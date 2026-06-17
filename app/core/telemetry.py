import hashlib
import logging
import json
from app.db.connection import get_db_connection

logger = logging.getLogger(__name__)

def hash_phone(phone: str) -> str:
    """Hashes a phone number for privacy using SHA-256."""
    if not phone:
        return "unknown"
    return hashlib.sha256(phone.encode('utf-8')).hexdigest()

def log_call_session(
    call_sid: str, 
    phone_number: str, 
    asr_route: str,
    query_text: str,
    response_text: str,
    cache_hit: bool,
    asr_latency_ms: int,
    llm_latency_ms: int,
    tts_latency_ms: int,
    total_latency_ms: int,
    estimated_cost_usd: float = 0.0
):
    """
    Logs comprehensive telemetry for a call session into PostgreSQL.
    """
    hashed_phone = hash_phone(phone_number)
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Ensure table exists (Phase 5 upgrade from call_logs)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS call_sessions (
                    call_sid VARCHAR(50) PRIMARY KEY,
                    hashed_phone VARCHAR(64) NOT NULL,
                    asr_route VARCHAR(20),
                    query_text TEXT,
                    response_text TEXT,
                    cache_hit BOOLEAN,
                    asr_latency_ms INTEGER,
                    llm_latency_ms INTEGER,
                    tts_latency_ms INTEGER,
                    total_latency_ms INTEGER,
                    estimated_cost_usd REAL DEFAULT 0.0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
                );
            """)
            
            # Auto-migrate table if estimated_cost_usd doesn't exist (robustness)
            try:
                cur.execute("ALTER TABLE call_sessions ADD COLUMN estimated_cost_usd REAL DEFAULT 0.0;")
            except Exception:
                conn.rollback() # Column likely exists
                pass
            
            query = """
                INSERT INTO call_sessions 
                (call_sid, hashed_phone, asr_route, query_text, response_text, cache_hit, asr_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms, estimated_cost_usd)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (call_sid) DO NOTHING;
            """
            cur.execute(query, (
                call_sid, hashed_phone, asr_route, query_text, response_text, cache_hit,
                asr_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms, estimated_cost_usd
            ))
            logger.info(f"Telemetry logged for session {call_sid} (Total Latency: {total_latency_ms}ms, Cost: ${estimated_cost_usd:.5f})")
    except Exception as e:
        logger.error(f"Failed to log telemetry for {call_sid}: {e}")

def log_ab_eval(query_text: str, rag_response: str, llm_response: str, length_diff: int, overlap_score: float):
    """
    Logs A/B testing evaluation data for RAG vs direct LLM to PostgreSQL.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eval_log (
                    id SERIAL PRIMARY KEY,
                    query_text TEXT,
                    rag_response TEXT,
                    llm_response TEXT,
                    length_diff INTEGER,
                    overlap_score REAL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
                );
            """)
            
            query = """
                INSERT INTO eval_log 
                (query_text, rag_response, llm_response, length_diff, overlap_score)
                VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(query, (query_text, rag_response, llm_response, length_diff, overlap_score))
            logger.info(f"A/B Evaluation logged (Overlap Score: {overlap_score:.2f})")
    except Exception as e:
        logger.error(f"Failed to log A/B eval: {e}")
