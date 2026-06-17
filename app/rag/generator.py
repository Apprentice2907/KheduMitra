import logging
from langchain_groq import ChatGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_llm():
    """
    Initializes the Groq LLM using model from settings.
    """
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set. LLM will not be available.")
        return None
        
    model_name = settings.GROQ_MODEL
    
    try:
        llm = ChatGroq(
            temperature=0.1, 
            groq_api_key=settings.GROQ_API_KEY, 
            model_name=model_name
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Groq model {model_name}: {str(e)}")
        return None
