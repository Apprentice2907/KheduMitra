import os
import json
import asyncio
import sys
from dotenv import load_dotenv

# Ensure the app module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from langchain_core.documents import Document
from app.rag.embeddings import get_embeddings
from langchain_community.vectorstores import PGVector
from app.core.config import settings
from app.rag.vector_store import COLLECTION_NAME

async def build_knowledge_base():
    if not settings.POSTGRES_URL:
        print("ERROR: POSTGRES_URL is not set in .env. Please set it to your Supabase connection string.")
        return

    dataset_path = os.path.join(os.path.dirname(__file__), '../data/sample_dataset.json')
    if not os.path.exists(dataset_path):
        print(f"ERROR: Dataset not found at {dataset_path}")
        return

    print("Loading dataset...")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    docs = []
    for item in data:
        # We can structure the text to include the title for better semantic matching
        content = f"Title: {item['title']}\n\n{item['content']}"
        docs.append(Document(page_content=content, metadata=item["metadata"]))

    print(f"Loaded {len(docs)} documents. Initializing embeddings model...")
    embeddings = get_embeddings()

    print(f"Connecting to Supabase (pgvector) and inserting documents...")
    # This will automatically create the pgvector extension if missing (requires permissions)
    # and create the appropriate tables.
    try:
        PGVector.from_documents(
            embedding=embeddings,
            documents=docs,
            collection_name=COLLECTION_NAME,
            connection_string=settings.POSTGRES_URL,
            pre_delete_collection=True # Clean wipe for testing
        )
        print("Successfully built Knowledge Base in Supabase!")
    except Exception as e:
        print(f"Failed to insert documents: {str(e)}")

if __name__ == "__main__":
    asyncio.run(build_knowledge_base())
