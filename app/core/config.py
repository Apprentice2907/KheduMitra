from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kisan Voice Bot"
    VERSION: str = "1.0.0"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # External APIs
    SARVAM_API_KEY: str = ""
    AGMARKNET_API_KEY: str = ""
    DATA_GOV_IN_API_KEY: str = ""
    
    # Cost Tracking Constants
    GROQ_COST_PER_1K_TOKENS: float = 0.0007 # Example: Llama-3-70b
    SARVAM_COST_PER_SECOND: float = 0.0000 # Assuming free tier or very low cost
    
    # AI & RAG configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    POSTGRES_URL: str = "" # For pgvector direct connection
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # WhatsApp Meta API
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "kisan_voice_bot_secret"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
