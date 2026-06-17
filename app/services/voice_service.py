import httpx
import logging
from typing import Optional
from app.core.config import settings
from app.core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.headers = {
            "api-subscription-key": self.api_key
        }
        self.base_url = "https://api.sarvam.ai"

    async def transcribe_audio(self, audio_bytes: bytes, language_code: str = "hi-IN") -> str:
        """
        Transcribe audio using Sarvam AI ASR.
        """
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not set, using mock transcription.")
            return "कपास का भाव क्या है"

        url = f"{self.base_url}/speech-to-text"
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
                files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
                data = {'model': 'saaras:v3', 'language_code': language_code}
                
                response = await client.post(
                    url, 
                    headers={"api-subscription-key": self.api_key}, 
                    files=files, 
                    data=data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("transcript", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam ASR HTTP error: {e.response.text}")
            raise ExternalAPIException(f"ASR service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Sarvam ASR unexpected error: {str(e)}")
            raise ExternalAPIException("Failed to transcribe audio.")

    async def generate_speech(self, text: str, target_language_code: str = "hi-IN") -> bytes:
        """
        Generate TTS audio using Sarvam AI.
        """
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not set, returning dummy audio bytes.")
            return b"dummy_audio_bytes"

        url = f"{self.base_url}/text-to-speech"
        payload = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": "ritu",
            "pace": 1.0,
            "speech_sample_rate": 8000, # 8000Hz is standard for telephony (Twilio)
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                # Sarvam returns base64 encoded audio in audios[0]
                import base64
                audio_base64 = result.get("audios", [])[0]
                return base64.b64decode(audio_base64)
        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam TTS HTTP error: {e.response.text}")
            raise ExternalAPIException(f"TTS service error: {e.response.status_code}. Detail: {e.response.text}")
        except Exception as e:
            logger.error(f"Sarvam TTS unexpected error: {str(e)}")
            raise ExternalAPIException("Failed to generate speech.")

voice_service = VoiceService()
