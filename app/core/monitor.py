import redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Basic sync redis client for metrics
# In production, you might reuse an async pool, but simple counters are fast enough
redis_client = None
if settings.REDIS_URL:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis for monitoring: {e}")

def record_latency(total_latency_ms: int):
    """Increments a 1-hour expiring key if latency > 8000ms."""
    if not redis_client:
        return
        
    try:
        if total_latency_ms > 8000:
            key = "alerts:latency_breach_1hr"
            redis_client.incr(key)
            # Set TTL to 1 hour (3600s) if not already set
            if redis_client.ttl(key) == -1:
                redis_client.expire(key, 3600)
                
        # Also track total calls for percentage calculation
        total_key = "alerts:total_calls_1hr"
        redis_client.incr(total_key)
        if redis_client.ttl(total_key) == -1:
            redis_client.expire(total_key, 3600)
            
    except Exception as e:
        logger.error(f"Redis latency metric tracking failed: {e}")

def record_asr_route(route: str):
    """Increments fallback counter if Whisper is used."""
    if not redis_client:
        return
        
    try:
        if "whisper" in route.lower():
            key = "alerts:whisper_fallback_1hr"
            redis_client.incr(key)
            if redis_client.ttl(key) == -1:
                redis_client.expire(key, 3600)
    except Exception as e:
        logger.error(f"Redis ASR metric tracking failed: {e}")

def get_health_metrics():
    """Returns current counts for health monitoring tasks."""
    if not redis_client:
        return {"total": 0, "breaches": 0, "fallbacks": 0}
        
    try:
        total = int(redis_client.get("alerts:total_calls_1hr") or 0)
        breaches = int(redis_client.get("alerts:latency_breach_1hr") or 0)
        fallbacks = int(redis_client.get("alerts:whisper_fallback_1hr") or 0)
        return {
            "total": total,
            "breaches": breaches,
            "fallbacks": fallbacks
        }
    except Exception as e:
        logger.error(f"Failed to fetch health metrics: {e}")
        return {"total": 0, "breaches": 0, "fallbacks": 0}
