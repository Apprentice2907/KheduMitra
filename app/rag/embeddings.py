import logging
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Using a multilingual model that works well for Hindi, Gujarati, Marathi, and English
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def get_embeddings():
    """
    Returns the HuggingFace embeddings model.
    Downloads the model on first run.
    """
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={'device': 'cpu'},  # Can use 'cuda' if GPU is available
            encode_kwargs={'normalize_embeddings': True}
        )
        return embeddings
    except Exception as e:
        logger.error(f"Failed to initialize embeddings model: {str(e)}")
        raise e
