import logging
import asyncio
from app.core.celery_app import celery_app
from app.core.config import settings
from twilio.rest import Client
from app.services.weather_service import weather_service
from app.models.subscriptions import get_all_districts, get_farmers_by_district

logger = logging.getLogger(__name__)

def run_async(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)

@celery_app.task(name="app.worker.cron_tasks.check_weather_and_alert")
def check_weather_and_alert():
    """
    Cron job to check weather for all subscribed districts.
    If rain or frost is detected, send Twilio SMS to subscribed farmers.
    """
    logger.info("Starting scheduled weather alert check...")
    
    districts = get_all_districts()
    logger.info(f"Found farmers in {len(districts)} districts.")
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials missing. Skipping SMS dispatches.")
        return
        
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    for district in districts:
        logger.info(f"Checking weather for {district}...")
        
        # Get 1 day forecast
        forecast = run_async(weather_service.get_forecast(district, 1))
        
        if not forecast or not forecast.get("forecast"):
            continue
            
        today = forecast["forecast"][0]
        
        # Simple alert criteria (Rain > 5mm or Temp < 5C for frost)
        rain_mm = today.get("rain_sum", 0)
        min_temp = today.get("min_temp", 25)
        
        alert_msg_hi = None
        
        if rain_mm > 5:
            alert_msg_hi = f"अलर्ट: {district} में आज भारी बारिश ({rain_mm}mm) की संभावना है। अपनी फसल ढक लें। - किसान हेल्पलाइन"
        elif min_temp < 5:
            alert_msg_hi = f"अलर्ट: {district} में आज पाला पड़ने (तापमान {min_temp}°C) की संभावना है। खेतों में हल्की सिंचाई करें। - किसान हेल्पलाइन"
            
        if alert_msg_hi:
            farmers = get_farmers_by_district(district)
            logger.info(f"Condition met in {district}. Alerting {len(farmers)} farmers.")
            
            for farmer in farmers:
                phone = farmer['phone_number']
                lang = farmer['language']
                
                # In a real app, translate alert_msg_hi to 'gu' or 'mr' based on lang
                # For Phase 4, we send the Hindi message
                msg = alert_msg_hi
                
                try:
                    message = twilio_client.messages.create(
                        body=msg,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=phone
                    )
                    logger.debug(f"Alert sent to {phone}, SID: {message.sid}")
                except Exception as e:
                    logger.error(f"Failed to send alert to {phone}: {e}")

from app.core.monitor import get_health_metrics

@celery_app.task(name="app.worker.cron_tasks.monitor_health_metrics")
def monitor_health_metrics():
    """
    Cron job running every 5 minutes to check Redis health metrics.
    Dispatches alerts if thresholds are breached.
    """
    logger.info("Checking health metrics for alerts...")
    metrics = get_health_metrics()
    
    total = metrics["total"]
    breaches = metrics["breaches"]
    fallbacks = metrics["fallbacks"]
    
    alerts = []
    
    # Threshold 1: Latency > 8s for more than 10% of calls (min 10 calls to avoid noise)
    if total > 10 and (breaches / total) > 0.10:
        alerts.append(f"LATENCY BREACH: {breaches}/{total} calls exceeded 8s latency in the last hour.")
        
    # Threshold 2: >20 Whisper fallbacks in the last hour
    if fallbacks >= 20:
        alerts.append(f"ASR DEGRADATION: Whisper fallback used {fallbacks} times in the last hour.")
        
    if alerts:
        alert_msg = " | ".join(alerts)
        logger.critical(f"HEALTH MONITOR ALERT: {alert_msg}")
        
        # In production, send this via Twilio SMS to Admin or Slack Webhook
        # For now, we log as critical
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                admin_phone = "+919876543210"  # Replace with actual admin number from settings
                twilio_client.messages.create(
                    body=f"KisanBot Critical Alert: {alert_msg}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=admin_phone
                )
            except Exception as e:
                logger.error(f"Failed to send SMS alert to Admin: {e}")
