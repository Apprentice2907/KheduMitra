import json
import logging
import asyncio
from app.core.config import settings
from app.core.telemetry import hash_phone
import redis.asyncio as redis
from app.rag.generator import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 7 * 24 * 60 * 60 # 7 days
        self.extraction_prompt = PromptTemplate(
            template="""Extract the crop type and district mentioned by the farmer. 
If not mentioned, return null for that field.
Output must be ONLY valid JSON matching this schema: {{"crop": "wheat", "district": "pune"}}

Query: {query}
""",
            input_variables=["query"]
        )

    async def get_farmer_memory(self, phone: str) -> dict:
        if not phone:
            return {}
        try:
            hashed = hash_phone(phone)
            data = await self.redis.get(f"khedumitra:{hashed}:memory")
            return json.loads(data) if data else {}
        except Exception as e:
            logger.error(f"Error reading memory for {phone}: {str(e)}")
            return {}

    async def _update_memory_task(self, phone: str, query: str):
        """Background task to extract and update memory."""
        llm = get_llm()
        if not llm or not phone:
            return

        try:
            chain = self.extraction_prompt | llm | JsonOutputParser()
            result = await chain.ainvoke({"query": query})
            
            crop = result.get("crop")
            district = result.get("district")
            
            if not crop and not district:
                return # Nothing to update
                
            hashed = hash_phone(phone)
            key = f"khedumitra:{hashed}:memory"
            
            # Get existing to merge
            existing = await self.get_farmer_memory(phone)
            if crop: existing["crop"] = crop
            if district: existing["district"] = district
            
            await self.redis.setex(key, self.ttl, json.dumps(existing))
            logger.info(f"Updated memory for {hashed}: {existing}")
            
        except Exception as e:
            # Fail silently as requested
            logger.debug(f"Memory extraction failed silently: {str(e)}")

    def extract_and_update_memory_async(self, phone: str, query: str):
        """Fire and forget memory extraction."""
        # Use asyncio.create_task to run in the background
        try:
            asyncio.create_task(self._update_memory_task(phone, query))
        except Exception as e:
            logger.debug(f"Failed to launch memory task: {e}")

memory_service = MemoryService()
