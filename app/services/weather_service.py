import httpx
import logging
import redis.asyncio as redis
import json
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import ExternalAPIException
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_coordinates(self, city: str) -> Optional[Dict[str, float]]:
        """Resolve city name to lat/lon using Open-Meteo Geocoding API"""
        cache_key = f"geo:{city}".lower()
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        params = {"name": city, "count": 1, "language": "en", "format": "json"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.geocoding_url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    return None
                    
                coords = {
                    "latitude": results[0]["latitude"],
                    "longitude": results[0]["longitude"]
                }
                
                try:
                    await self.redis.setex(cache_key, 86400, json.dumps(coords)) # Cache for 24 hours
                except Exception:
                    pass
                    
                return coords
        except Exception as e:
            logger.error(f"Geocoding failed for {city}: {str(e)}")
            raise ExternalAPIException("Failed to resolve city coordinates.")

    def _interpret_weather_code(self, code: int) -> str:
        # WMO Weather interpretation codes
        if code == 0: return "Clear"
        if code in [1, 2, 3]: return "Partly Cloudy"
        if code in [45, 48]: return "Fog"
        if code in [51, 53, 55, 56, 57]: return "Drizzle"
        if code in [61, 63, 65, 66, 67]: return "Rain"
        if code in [71, 73, 75, 77]: return "Snow"
        if code in [80, 81, 82]: return "Rain Showers"
        if code in [95, 96, 99]: return "Thunderstorm"
        return "Unknown"

    async def get_forecast(self, city: str, days: int = 3) -> Dict[str, Any]:
        """Fetch weather forecast for the specified city and days."""
        cache_key = f"weather:forecast:{city}:{days}".lower()
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info(f"Weather cache hit for {city}")
                return json.loads(cached)
        except Exception:
            pass

        coords = await self.get_coordinates(city)
        if not coords:
            # Fallback mock or throw error
            return {
                "city": city,
                "forecast": [
                    {"date": datetime.now().strftime("%Y-%m-%d"), "max_temp": 38.5, "min_temp": 22.1, "condition": "Clear"}
                ]
            }

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
            "timezone": "auto",
            "forecast_days": min(max(days, 1), 16) # Max 16 days
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.weather_url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                
                daily = data.get("daily", {})
                times = daily.get("time", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                codes = daily.get("weather_code", [])

                forecast = []
                for i in range(len(times)):
                    forecast.append({
                        "date": times[i],
                        "max_temp": max_temps[i],
                        "min_temp": min_temps[i],
                        "condition": self._interpret_weather_code(codes[i])
                    })
                
                result = {
                    "city": city,
                    "forecast": forecast
                }
                
                # Cache for 2 hours (7200 seconds)
                try:
                    await self.redis.setex(cache_key, 7200, json.dumps(result))
                except Exception:
                    pass
                    
                return result
        except Exception as e:
            logger.error(f"Weather API failed: {str(e)}")
            raise ExternalAPIException("Failed to fetch weather forecast.")

    async def get_imd_forecast(self, district: str) -> Dict[str, Any]:
        """
        Fetch district-level IMD weather forecast via data.gov.in.
        Falls back to Open-Meteo if IMD data is unavailable or API key is missing.
        """
        if not settings.DATA_GOV_IN_API_KEY:
            logger.info("No data.gov.in API key, falling back to Open-Meteo for weather.")
            return await self.get_forecast(district, days=3)

        cache_key = f"kissan:cache:weather:imd:{district}".lower()
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info(f"IMD Weather cache hit for {district}")
                return json.loads(cached)
        except Exception:
            pass

        # Hypothetical data.gov.in IMD resource ID
        resource_id = "imd_district_forecast_resource_id"
        base_url = "https://api.data.gov.in/resource"
        
        params = {
            "api-key": settings.DATA_GOV_IN_API_KEY,
            "format": "json",
            "filters[district]": district.upper(),
            "limit": 3
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
                response = await client.get(f"{base_url}/{resource_id}", params=params)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("records", [])
                if not records:
                    logger.warning(f"No IMD data found for {district}, falling back to Open-Meteo.")
                    return await self.get_forecast(district, days=3)

                forecast = []
                for record in records:
                    forecast.append({
                        "date": record.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "max_temp": float(record.get("max_temp", 0)),
                        "min_temp": float(record.get("min_temp", 0)),
                        "condition": record.get("weather_desc", "Unknown")
                    })
                
                result = {
                    "city": district,
                    "forecast": forecast,
                    "source": "IMD"
                }
                
                try:
                    await self.redis.setex(cache_key, 7200, json.dumps(result))
                except Exception:
                    pass
                    
                return result
        except Exception as e:
            logger.error(f"IMD Weather API failed: {str(e)}. Falling back to Open-Meteo.")
            return await self.get_forecast(district, days=3)

weather_service = WeatherService()
