import logging
from langchain_community.vectorstores import PGVector
from app.rag.embeddings import get_embeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "kisan_knowledge_base"

def get_vector_store():
    """
    Initializes and returns the Supabase pgvector store.
    """
    if not settings.POSTGRES_URL:
        logger.warning("POSTGRES_URL is not set. Vector store will not be available.")
        return None
        
    try:
        embeddings = get_embeddings()
        
        vector_store = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=settings.POSTGRES_URL,
            embedding_function=embeddings,
        )
        return vector_store
    except Exception as e:
        logger.error(f"Failed to connect to Supabase pgvector: {str(e)}")
        return None
