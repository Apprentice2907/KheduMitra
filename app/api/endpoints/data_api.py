from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
from app.services.agmarknet_service import agmarknet_service
from app.services.weather_service import weather_service
from app.services.voice_service import voice_service
from app.models.schemas import MandiPriceResponse, WeatherForecastResponse, ASRResponse

router = APIRouter()

@router.get("/mandi/price", response_model=MandiPriceResponse, tags=["Data API"])
async def get_mandi_price(state: str, district: str, commodity: str):
    data = await agmarknet_service.get_mandi_price(state, district, commodity)
    if not data:
        raise HTTPException(status_code=404, detail="Price data not found")
    return MandiPriceResponse(**data)

@router.get("/weather/forecast", response_model=WeatherForecastResponse, tags=["Data API"])
async def get_weather_forecast(city: str, days: int = 3):
    data = await weather_service.get_forecast(city, days)
    return WeatherForecastResponse(**data)

@router.post("/voice/asr", response_model=ASRResponse, tags=["Voice API"])
async def test_asr(file: UploadFile = File(...)):
    """Test ASR by uploading a WAV file"""
    audio_bytes = await file.read()
    transcription = await voice_service.transcribe_audio(audio_bytes)
    return ASRResponse(transcription=transcription, language="hi", confidence=0.95)

@router.get("/stats", tags=["Data API"])
async def get_stats():
    """Impact metrics endpoint for dashboard."""
    from app.core.config import settings
    import redis.asyncio as redis
    from app.db.connection import get_db_connection
    import json
    
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    try:
        total_calls = await r.get("stats:total_calls") or "0"
        lang_hi = await r.get("stats:lang:hi") or "0"
        lang_mr = await r.get("stats:lang:mr") or "0"
        lang_gu = await r.get("stats:lang:gu") or "0"
        lang_sms = await r.get("stats:lang:sms") or "0"
        cache_hits = await r.get("stats:cache_hits") or "0"
        total_latency_ms = await r.get("stats:total_latency_ms") or "0"
        
        total_calls_int = int(total_calls)
        avg_latency = int(total_latency_ms) / total_calls_int if total_calls_int > 0 else 0
        hit_rate = (int(cache_hits) / total_calls_int) * 100 if total_calls_int > 0 else 0
        
        # Get district coverage map data from DB (cached)
        district_coverage_key = "khedumitra:cache:district_coverage"
        district_coverage = await r.get(district_coverage_key)
        
        if not district_coverage:
            # Query db for district coverage (assuming memory table or log table)
            # Since we don't extract district to call_sessions yet, we can mock it based on Redis memory scans, 
            # or just return a dummy structure for now as a placeholder until Phase 5.
            # To be safe, we'll return a placeholder mapping.
            coverage_data = {"pune": 150, "nashik": 85, "surat": 45}
            await r.setex(district_coverage_key, 3600, json.dumps(coverage_data))
            district_coverage = coverage_data
        else:
            district_coverage = json.loads(district_coverage)

        return {
            "total_calls_handled": total_calls_int,
            "language_breakdown": {
                "hi": int(lang_hi),
                "mr": int(lang_mr),
                "gu": int(lang_gu),
                "sms": int(lang_sms)
            },
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "average_latency_ms": int(avg_latency),
            "district_coverage": district_coverage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
