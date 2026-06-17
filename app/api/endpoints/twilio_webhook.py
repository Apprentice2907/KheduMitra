from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
import logging
from app.worker.tasks import process_voice_query, process_sms_query

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/voice/incoming", tags=["Twilio"])
async def handle_incoming_call(request: Request):
    """
    Twilio incoming call webhook.
    Plays an IVR menu using <Gather>.
    If no digit is pressed, falls through to default Hindi recording.
    """
    try:
        logger.info("Received incoming call from Twilio")
        
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather action="/twilio/voice/menu" numDigits="1" timeout="5">
                <Say language="hi-IN" voice="Polly.Aditi">किसान हेल्पलाइन में आपका स्वागत है। हिंदी के लिए एक दबाएं। गुजराती माटे बे दबावो। मराठी साठी तीन दाबा. या फिर अपना सवाल सीधे पूछने के लिए बीप का इंतजार करें।</Say>
            </Gather>
            <!-- Fallback if no digit is pressed (assumes Hindi free speech) -->
            <Record action="/twilio/voice/recording?lang=hi" maxLength="15" playBeep="true" />
        </Response>
        """
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error handling incoming call: {e}")
        error_twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say language=\"hi-IN\" voice=\"Polly.Aditi\">क्षमा करें, एक तकनीकी समस्या है।</Say><Hangup/></Response>"
        return Response(content=error_twiml, media_type="application/xml")

@router.post("/voice/menu", tags=["Twilio"])
async def handle_ivr_menu(
    request: Request,
    Digits: str = Form(None)
):
    """
    Handles the digit pressed by the user in the IVR menu.
    """
    try:
        logger.info(f"User pressed digit: {Digits}")
        
        # Map digits to language code
        lang_map = {
            "1": "hi",
            "2": "gu",
            "3": "mr"
        }
        
        lang = lang_map.get(Digits, "hi") # Default to Hindi if invalid
        
        prompts = {
            "hi": "अपना सवाल बीप के बाद बोलें।",
            "gu": "બીપ પછી તમારો પ્રશ્ન બોલો.",
            "mr": "बीप नंतर तुमचा प्रश्न बोला."
        }
        
        voices = {
            "hi": "Polly.Aditi",
            "gu": "Polly.Kajal",
            "mr": "Polly.Kajal" # Twilio may not have native MR, using Kajal as fallback
        }
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say language="{lang}-IN" voice="{voices[lang]}">{prompts[lang]}</Say>
            <Record action="/twilio/voice/recording?lang={lang}" maxLength="15" playBeep="true" />
        </Response>
        """
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error handling menu: {e}")
        error_twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say language=\"hi-IN\" voice=\"Polly.Aditi\">क्षमा करें, एक तकनीकी समस्या है।</Say><Hangup/></Response>"
        return Response(content=error_twiml, media_type="application/xml")

@router.post("/voice/recording", tags=["Twilio"])
async def handle_recording(
    request: Request,
    lang: str = "hi",
    RecordingUrl: str = Form(None),
    CallSid: str = Form(None),
    From: str = Form(None)
):
    """
    Handles the finished audio recording.
    Dispatches Celery task to process the voice query.
    """
    try:
        # Don't log raw phone
        from app.core.telemetry import hash_phone
        hashed_from = hash_phone(From) if From else "unknown"
        logger.info(f"Received recording for CallSid: {CallSid} from {hashed_from} in language {lang}")
        
        if RecordingUrl:
            # Dispatch Celery background task
            process_voice_query.delay(CallSid, RecordingUrl, From, lang)
            
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say language="hi-IN" voice="Polly.Aditi">कृपया प्रतीक्षा करें, हम जानकारी खोज रहे हैं।</Say>
            <Pause length="15"/>
        </Response>
        """
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error handling recording: {e}")
        error_twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say language=\"hi-IN\" voice=\"Polly.Aditi\">क्षमा करें, एक तकनीकी समस्या है।</Say><Hangup/></Response>"
        return Response(content=error_twiml, media_type="application/xml")

@router.post("/sms/incoming", tags=["Twilio"])
async def handle_incoming_sms(
    request: Request,
    From: str = Form(None),
    Body: str = Form(None)
):
    """
    Webhook triggered by Twilio when an SMS comes in.
    """
    try:
        from app.core.telemetry import hash_phone
        hashed_from = hash_phone(From) if From else "unknown"
        logger.info(f"Received SMS from {hashed_from}: {Body}")
        
        # Process SMS via Celery task so we don't hold the connection
        if Body and From:
            process_sms_query.delay(From, Body)
            
        # Return empty TwiML, since we will reply asynchronously via REST API
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response></Response>
        """
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error handling SMS: {e}")
        error_twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>"
        return Response(content=error_twiml, media_type="application/xml")
