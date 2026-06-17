from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import KissanBotException, kissanbot_exception_handler, global_exception_handler
from app.api.router import api_router

import time
import httpx
import redis.asyncio as redis
from prometheus_client import make_asgi_app
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT
from app.db.connection import get_db_connection

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend for Kisan Voice Bot - AI Voice Helpline for Farmers",
)

# Mount static files for local testing UI
app.mount("/demo", StaticFiles(directory="public", html=True), name="public")

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path
    # Ignore /metrics to avoid self-polling noise
    if endpoint == "/metrics":
        return await call_next(request)
        
    start_time = time.time()
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            ERROR_COUNT.labels(method=method, endpoint=endpoint, status_code=response.status_code).inc()
        return response
    except Exception as e:
        ERROR_COUNT.labels(method=method, endpoint=endpoint, status_code=500).inc()
        raise e
    finally:
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

# Exception Handlers
app.add_exception_handler(KissanBotException, kissanbot_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Kisan Voice Bot FastAPI server")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Kisan Voice Bot FastAPI server")

@app.get("/health", tags=["Health"])
async def health_check():
    components = {
        "redis": "disconnected",
        "supabase": "disconnected",
        "groq": "disconnected",
        "sarvam": "disconnected"
    }
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        if await r.ping():
            components["redis"] = "connected"
    except Exception:
        pass
        
    # Check Supabase DB
    try:
        with get_db_connection() as conn:
            components["supabase"] = "connected"
    except Exception:
        pass
        
    # Check Groq API
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"} if settings.GROQ_API_KEY else {}
            res = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
            if res.status_code in [200, 401]:
                components["groq"] = "connected" if res.status_code == 200 else "unauthorized"
    except Exception:
        pass
        
    # Check Sarvam API
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Simple reachability check
            res = await client.get("https://api.sarvam.ai/")
            components["sarvam"] = "reachable"
    except Exception:
        pass
        
    status = "ok" if all(v in ["connected", "reachable", "unauthorized"] for v in components.values()) else "degraded"
    
    return {"status": status, "version": settings.VERSION, "components": components}
