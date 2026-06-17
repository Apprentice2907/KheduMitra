from fastapi import APIRouter
from app.api.endpoints import health, twilio_webhook, data_api, whatsapp_webhook, test_voice, ussd_handler

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(twilio_webhook.router, prefix="/twilio")
api_router.include_router(whatsapp_webhook.router, prefix="/whatsapp")
api_router.include_router(ussd_handler.router, prefix="/ussd")
api_router.include_router(data_api.router)
api_router.include_router(test_voice.router, prefix="/test")
