import logging
import json
import os
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

def get_hybrid_retriever():
    """
    Returns the Supabase semantic search retriever.
    """
    vs = get_vector_store()
    if not vs:
        return None
        
    return vs.as_retriever(search_kwargs={"k": 3})

