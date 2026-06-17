from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
import logging
import json
import redis.asyncio as redis
from app.core.config import settings
from app.rag.pipeline import ask_rag
from app.worker.tasks import run_async

logger = logging.getLogger(__name__)
router = APIRouter()

ussd_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

def paginate_text(text: str, max_length: int = 160) -> list:
    """Split text into chunks suitable for USSD."""
    words = text.split(" ")
    chunks = []
    current_chunk = ""
    for word in words:
        if len(current_chunk) + len(word) + 1 <= max_length:
            current_chunk += (word + " ")
        else:
            chunks.append(current_chunk.strip())
            current_chunk = word + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

@router.post("/incoming", tags=["USSD"])
async def handle_ussd(
    sessionId: str = Form(None),
    phoneNumber: str = Form(None),
    networkCode: str = Form(None),
    serviceCode: str = Form(None),
    text: str = Form("")
):
    """
    Generic USSD endpoint (Africa's Talking style).
    text will be empty on first load, and will contain user input separated by * on subsequent loads.
    """
    logger.info(f"USSD Request from {phoneNumber}: {text}")
    
    # Split text by '*' to get the latest input
    inputs = text.split("*") if text else []
    latest_input = inputs[-1] if inputs else ""
    
    session_key = f"ussd:{sessionId}"
    
    if not text:
        # First screen
        response = "CON Welcome to Kisan Voice Bot.\nReply with your question or type 0 to exit."
        return PlainTextResponse(response)
        
    if latest_input == "0":
        # Exit
        await ussd_redis.delete(session_key)
        return PlainTextResponse("END Thank you for using Kisan Voice Bot.")
        
    # Check if we are paginating an existing response
    session_data = await ussd_redis.get(session_key)
    
    if session_data:
        data = json.loads(session_data)
        chunks = data.get("chunks", [])
        current_page = data.get("page", 0)
        
        if latest_input == "1":
            # Next page
            next_page = current_page + 1
            if next_page < len(chunks):
                data["page"] = next_page
                await ussd_redis.setex(session_key, 300, json.dumps(data))
                
                chunk_text = chunks[next_page]
                if next_page == len(chunks) - 1:
                    return PlainTextResponse(f"END {chunk_text}")
                else:
                    return PlainTextResponse(f"CON {chunk_text}\n\n1:Next 0:Exit")
            else:
                return PlainTextResponse("END No more pages.")
                
    # If not paginating, treat as a new query
    # Execute RAG pipeline
    # Note: For USSD, synchronous blocking might timeout if LLM takes > 10s. 
    # For a real production USSD, we might return "Processing, please wait" and push via SMS.
    # Here we await the async rag directly.
    try:
        rag_response = await ask_rag(latest_input, phone_number=phoneNumber)
    except Exception as e:
        logger.error(f"USSD RAG Error: {str(e)}")
        rag_response = "Sorry, I could not process your request at this time."
        
    chunks = paginate_text(rag_response, 160) # 160 to leave room for pagination menu (max 182)
    
    if len(chunks) > 1:
        # Save to Redis for pagination
        await ussd_redis.setex(session_key, 300, json.dumps({
            "chunks": chunks,
            "page": 0
        }))
        return PlainTextResponse(f"CON {chunks[0]}\n\n1:Next 0:Exit")
    else:
        return PlainTextResponse(f"END {chunks[0] if chunks else 'No response'}")
