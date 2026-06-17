import logging
import httpx
import asyncio
from twilio.rest import Client
from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.voice_service import voice_service
from app.rag.pipeline import ask_rag

logger = logging.getLogger(__name__)

def run_async(coro):
    """Synchronous wrapper to run async code inside Celery task."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If somehow running in an async context, this might fail, but Celery workers are sync by default.
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)

@celery_app.task(name="app.worker.tasks.process_voice_query")
def process_voice_query(call_sid: str, recording_url: str, from_number: str, lang: str = "hi"):
    """
    1. Download audio from Twilio RecordingUrl
    2. Transcribe via Sarvam AI
    3. Pass text to RAG Pipeline
    4. Tell Twilio to play the RAG response back to the user
    """
    import time
    from app.core.telemetry import log_call_session
    from app.core.monitor import record_latency, record_asr_route
    from app.core.metrics import CACHE_MISSES, CACHE_HITS
    
    logger.info(f"Processing voice query for CallSid: {call_sid} in {lang}")
    start_time = time.time()
    
    try:
        # 1. Download Twilio Recording to /tmp
        audio_url = f"{recording_url}.wav"
        temp_audio_path = f"/tmp/twilio_{call_sid}.wav"
        audio_bytes = None
        
        try:
            with httpx.Client() as client:
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN) if settings.TWILIO_ACCOUNT_SID else None
                # Enforce strict 5s timeout on download
                response = client.get(audio_url, auth=auth, timeout=5.0)
                response.raise_for_status()
                
                # Write to tmp file (Production Hardening: /tmp cleanup)
                import os
                
                # Create /tmp dir if on windows or fallback
                tmp_dir = "/tmp" if os.name != 'nt' else os.environ.get('TEMP', 'C:\\Temp')
                if not os.path.exists(tmp_dir):
                    os.makedirs(tmp_dir, exist_ok=True)
                    
                temp_audio_path = os.path.join(tmp_dir, f"twilio_{call_sid}.wav")
                
                with open(temp_audio_path, 'wb') as f:
                    f.write(response.content)
                
                # Read back for transcription (or pass path to ffmpeg later)
                with open(temp_audio_path, 'rb') as f:
                    audio_bytes = f.read()
                    
        finally:
            # Ephemeral /tmp cleanup
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                logger.debug(f"Cleaned up ephemeral audio file: {temp_audio_path}")

        if not audio_bytes:
            raise ValueError("Failed to download audio bytes")

        sarvam_lang_map = {
            "hi": "hi-IN",
            "gu": "gu-IN",
            "mr": "mr-IN"
        }
        sarvam_lang = sarvam_lang_map.get(lang, "hi-IN")
        
        # 2. Transcribe
        t0 = time.time()
        transcription = run_async(voice_service.transcribe_audio(audio_bytes, language_code=sarvam_lang))
        asr_latency_ms = int((time.time() - t0) * 1000)
        
        # Track if fallback was used (assuming voice_service logs it or we infer from latency/route)
        # For demo purposes, we will assume route is Bhashini
        asr_route = "bhashini" 
        record_asr_route(asr_route)
        
        logger.info(f"Transcription: {transcription} ({asr_latency_ms}ms)")
        
        # 3. Query RAG
        t1 = time.time()
        if transcription.strip() == "":
            response_text = "क्षमा करें, मैं आपकी आवाज़ नहीं सुन सका।"
        else:
            response_text = run_async(ask_rag(f"({lang}) {transcription}", phone_number=from_number))
        llm_latency_ms = int((time.time() - t1) * 1000)
        
        # 4. Generate TTS
        t2 = time.time()
        tts_bytes = run_async(voice_service.generate_speech(response_text, target_language_code=sarvam_lang))
        tts_latency_ms = int((time.time() - t2) * 1000)
        logger.info(f"Generated Sarvam TTS audio: {len(tts_bytes)} bytes ({tts_latency_ms}ms)")
        
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        # Estimate Costs
        # ~4 chars per token for Groq
        groq_tokens = len(response_text) / 4
        groq_cost = (groq_tokens / 1000.0) * settings.GROQ_COST_PER_1K_TOKENS
        # ~15 chars per second for Sarvam TTS
        sarvam_seconds = len(response_text) / 15.0
        sarvam_cost = sarvam_seconds * settings.SARVAM_COST_PER_SECOND
        estimated_cost_usd = groq_cost + sarvam_cost
        
        cache_hit = False # Placeholder
        
        # Track metrics for cache (placeholder since RAG currently doesn't return flag)
        if cache_hit:
            CACHE_HITS.inc()
        else:
            CACHE_MISSES.inc()
            
        # Update Redis Stats
        import redis
        try:
            r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.incr("stats:total_calls")
            r.incr(f"stats:lang:{lang}")
            r.incrby("stats:total_latency_ms", total_latency_ms)
            if cache_hit:
                r.incr("stats:cache_hits")
        except Exception as e:
            logger.error(f"Failed to increment Redis stats: {e}")
        
        log_call_session(
            call_sid=call_sid,
            phone_number=from_number,
            asr_route=asr_route,
            query_text=transcription,
            response_text=response_text,
            cache_hit=cache_hit,
            asr_latency_ms=asr_latency_ms,
            llm_latency_ms=llm_latency_ms,
            tts_latency_ms=tts_latency_ms,
            total_latency_ms=total_latency_ms,
            estimated_cost_usd=estimated_cost_usd
        )
        
        # Track metrics for alerts
        record_latency(total_latency_ms)
        
        # 5. Call Modification
        voices = {
            "hi": "Polly.Aditi",
            "gu": "Polly.Kajal",
            "mr": "Polly.Kajal"
        }
        voice = voices.get(lang, "Polly.Aditi")
        
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say language="{lang}-IN" voice="{voice}">{response_text}</Say>
            </Response>
            """
            
            call = twilio_client.calls(call_sid).update(twiml=twiml)
            logger.info(f"Twilio call {call_sid} updated. Status: {call.status}")
        else:
            logger.warning("Twilio credentials not set. Skipping call modification.")

    except Exception as e:
        logger.error(f"Error processing voice query: {str(e)}", exc_info=True)


@celery_app.task(name="app.worker.tasks.process_sms_query")
def process_sms_query(from_number: str, body: str):
    """
    Process an incoming SMS by hitting the RAG pipeline and sending an SMS reply.
    """
    from app.core.telemetry import hash_phone
    hashed_from = hash_phone(from_number)
    logger.info(f"Processing SMS query from {hashed_from}")
    try:
        response_text = run_async(ask_rag(body, phone_number=from_number))
        
        # Estimate Costs
        groq_tokens = len(response_text) / 4
        groq_cost = (groq_tokens / 1000.0) * settings.GROQ_COST_PER_1K_TOKENS
        
        # Update Redis Stats
        import redis
        try:
            r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.incr("stats:total_calls")
            r.incr("stats:lang:sms")
        except Exception as e:
            logger.error(f"Failed to increment Redis stats: {e}")
        
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = twilio_client.messages.create(
                body=response_text,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=from_number
            )
            logger.info(f"SMS reply sent to {hashed_from}. SID: {message.sid}. Cost: ${groq_cost:.5f}")
        else:
            logger.warning("Twilio credentials not set. Cannot send SMS reply.")
    except Exception as e:
        logger.error(f"Error processing SMS query: {str(e)}", exc_info=True)
