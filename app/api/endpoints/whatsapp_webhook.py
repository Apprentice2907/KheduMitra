from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
import logging
from app.core.config import settings
from app.worker.tasks import process_sms_query # For now, we can reuse SMS logic for text, or add WhatsApp specific
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/webhook", tags=["WhatsApp"])
async def verify_whatsapp_webhook(request: Request):
    """
    Meta (WhatsApp) webhook verification endpoint.
    Meta sends a GET request with hub.mode, hub.challenge, and hub.verify_token.
    """
    query_params = request.query_params
    hub_mode = query_params.get("hub.mode")
    hub_challenge = query_params.get("hub.challenge")
    hub_verify_token = query_params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning("WhatsApp webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook", tags=["WhatsApp"])
async def handle_whatsapp_message(request: Request):
    """
    Handles incoming messages from WhatsApp users.
    """
    try:
        body = await request.json()
        logger.info(f"Incoming WhatsApp webhook: {body}")
        
        # WhatsApp webhooks have a deeply nested structure
        if "object" in body and body["object"] == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    for msg in messages:
                        from_number = msg.get("from")
                        msg_type = msg.get("type")
                        
                        if msg_type == "text":
                            text_body = msg.get("text", {}).get("body", "")
                            logger.info(f"WhatsApp Text from {from_number}: {text_body}")
                            
                            # We can reuse the SMS task, or create a specific WhatsApp task 
                            # because WhatsApp replies use a different API than Twilio SMS.
                            # For now, let's log. A full implementation would need a task that calls the Meta Graph API.
                            pass
                            
                        elif msg_type == "audio":
                            audio_id = msg.get("audio", {}).get("id")
                            logger.info(f"WhatsApp Audio received from {from_number}, Audio ID: {audio_id}")
                            # Would dispatch a celery task to download media from Meta Graph API,
                            # run through Sarvam -> RAG -> TTS -> Upload back to Meta -> Send
                            pass
                            
            return Response(content="EVENT_RECEIVED", status_code=200)
        else:
            raise HTTPException(status_code=404, detail="Not a WhatsApp API event")
            
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {str(e)}")
        return Response(content="ERROR", status_code=500)
