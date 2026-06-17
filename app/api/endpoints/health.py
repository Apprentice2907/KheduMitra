from fastapi import APIRouter
import redis.asyncio as redis
from app.core.config import settings
from app.core.celery_app import celery_app
from app.models.schemas import HealthResponse, ReadinessResponse
from app.core.logging import logger

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(status="ok", version=settings.VERSION)

@router.get("/health/readiness", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check():
    """Deep readiness check of external dependencies (Redis, Celery)"""
    redis_status = "disconnected"
    celery_status = "unknown"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        if await r.ping():
            redis_status = "connected"
    except Exception as e:
        logger.error(f"Readiness check failed for Redis: {str(e)}")
        
    # Check Celery
    try:
        # Pinging celery workers
        i = celery_app.control.inspect()
        active = i.active()
        if active is not None:
            celery_status = "running"
        else:
            celery_status = "no_workers_found"
    except Exception as e:
        logger.error(f"Readiness check failed for Celery: {str(e)}")
        celery_status = "error"
        
    status = "ready" if redis_status == "connected" and celery_status == "running" else "degraded"
    
    return ReadinessResponse(
        status=status,
        redis=redis_status,
        celery=celery_status
    )
