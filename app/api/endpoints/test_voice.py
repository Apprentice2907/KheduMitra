from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import Response
import logging
from app.services.voice_service import voice_service
from app.rag.pipeline import ask_rag

logger = logging.getLogger(__name__)
router = APIRouter()

from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    phone_number: str

@router.post("/ask", tags=["Testing"])
async def handle_test_ask(req: AskRequest):
    """Test endpoint for text-based RAG query bypassing Twilio"""
    from app.core.telemetry import hash_phone
    from app.services.memory_service import memory_service
    hashed = hash_phone(req.phone_number)
    
    # 1. Update Memory Async
    memory_service.extract_and_update_memory_async(req.phone_number, req.question)
    
    # 2. Get RAG response
    response_text = await ask_rag(f"({req.phone_number}) {req.question}")
    
    return {"response": response_text, "intent": "detected_internally"}

@router.post("/voice-chat", tags=["Testing"])
async def handle_test_voice(
    audio: UploadFile = File(...),
    lang: str = Form("hi")
):
    """
    Test endpoint to simulate the full voice pipeline:
    1. Transcribe uploaded audio
    2. Pass to RAG
    3. Generate TTS audio and return it
    """
    logger.info(f"Received test voice request for language: {lang}")
    
    try:
        # Read the uploaded audio bytes
        audio_bytes = await audio.read()
        # Convert browser audio (likely webm/ogg) to standard 16kHz WAV using ffmpeg
        import subprocess
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_in:
            temp_in.write(audio_bytes)
            temp_in_path = temp_in.name
            
        temp_out_path = temp_in_path + ".wav"
        
        try:
            # -ac 1 (mono), -ar 16000 (16kHz) for best ASR compatibility
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_in_path, 
                "-ac", "1", "-ar", "16000", "-f", "wav", temp_out_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            with open(temp_out_path, "rb") as f:
                wav_bytes = f.read()
        finally:
            if os.path.exists(temp_in_path):
                os.remove(temp_in_path)
            if os.path.exists(temp_out_path):
                os.remove(temp_out_path)

        # Map 'hi' -> 'hi-IN'
        sarvam_lang = f"{lang}-IN"

        # 1. Transcribe
        logger.info(f"Transcribing audio in {sarvam_lang}...")
        transcription = await voice_service.transcribe_audio(wav_bytes, language_code=sarvam_lang)
        logger.info(f"Transcription: {transcription}")
        
        # 2. RAG
        if transcription.strip() == "":
            response_text = "क्षमा करें, मैं आपकी आवाज़ नहीं सुन सका।"
        else:
            logger.info("Querying RAG...")
            # ask_rag is likely an async function
            response_text = await ask_rag(f"({lang}) {transcription}")
        
        logger.info(f"RAG Response: {response_text}")
        
        # 3. TTS
        logger.info("Generating TTS...")
        tts_bytes = await voice_service.generate_speech(response_text, target_language_code=sarvam_lang)
        
        return Response(content=tts_bytes, media_type="audio/wav")
        
    except Exception as e:
        logger.error(f"Error in test voice pipeline: {str(e)}", exc_info=True)
        return Response(content=f"Error: {str(e)}", status_code=500, media_type="text/plain")
