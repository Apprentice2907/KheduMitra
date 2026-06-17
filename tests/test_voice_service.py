import pytest
from app.services.voice_service import voice_service

@pytest.mark.asyncio
async def test_voice_service_initialization():
    assert voice_service.base_url == "https://api.sarvam.ai"
    # Basic sanity check
    assert voice_service.api_key is not None or voice_service.api_key == ""
