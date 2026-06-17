import httpx
import logging
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)

class AgmarknetService:
    def __init__(self):
        self.api_key = settings.AGMARKNET_API_KEY
        self.resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
        self.base_url = "https://api.data.gov.in/resource"
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_mandi_price(self, state: str, district: str, commodity: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest mandi price for a specific commodity in a given district/state.
        Uses Redis to cache results for 12 hours since Agmarknet data updates daily.
        """
        cache_key = f"mandi:{state}:{district}:{commodity}".lower()
        
        # Check cache first
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Redis cache error: {str(e)}")

        if not self.api_key:
            logger.warning("AGMARKNET_API_KEY not set. Returning mock data.")
            mock_data = {
                "commodity": commodity,
                "mandi": district,
                "min_price": 5000.0,
                "max_price": 7200.0,
                "modal_price": 6800.0,
                "date": "2024-03-24"
            }
            return mock_data

        url = f"{self.base_url}/{self.resource_id}"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[state]": state,
            "filters[district]": district,
            "filters[commodity]": commodity,
            "limit": 1
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("records", [])
                if not records:
                    return None
                    
                record = records[0]
                result = {
                    "commodity": record.get("commodity"),
                    "mandi": record.get("market"),
                    "min_price": float(record.get("min_price", 0)),
                    "max_price": float(record.get("max_price", 0)),
                    "modal_price": float(record.get("modal_price", 0)),
                    "date": record.get("arrival_date")
                }

                # Cache for 2 hours (7200 seconds) as per Phase 5 spec
                try:
                    await self.redis.setex(cache_key, 7200, json.dumps(result))
                except Exception as e:
                    logger.error(f"Redis cache set error: {str(e)}")

                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Agmarknet API HTTP error: {e.response.text}")
            raise ExternalAPIException(f"Agmarknet service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Agmarknet API unexpected error: {str(e)}")
            raise ExternalAPIException("Failed to fetch mandi price.")

agmarknet_service = AgmarknetService()
