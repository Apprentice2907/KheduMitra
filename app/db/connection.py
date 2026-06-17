import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger(__name__)

def _prepare_postgres_url(url: str) -> str:
    if not url:
        return ""
    try:
        # Check if using pooler URL format
        if "pooler.supabase.com" not in url:
            logger.warning("POSTGRES_URL domain does not appear to be a Supabase pooler URL (should contain pooler.supabase.com).")
            
        # Parse and encode any '@' in the password
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "/" in rest:
                auth_host, path = rest.split("/", 1)
                if "@" in auth_host:
                    auth, host_port = auth_host.rsplit("@", 1)
                    if ":" in auth:
                        user, pwd = auth.split(":", 1)
                        # Encode any remaining unencoded '@' in password
                        pwd = pwd.replace("@", "%40")
                        encoded_auth = f"{user}:{pwd}"
                        return f"{scheme}://{encoded_auth}@{host_port}/{path}"
    except Exception as e:
        logger.warning(f"Failed to parse or format POSTGRES_URL: {e}")
    return url

@contextmanager
def get_db_connection():
    """
    Context manager for getting a psycopg2 database connection.
    Uses POSTGRES_URL from settings.
    Yields a connection that automatically closes when done.
    """
    conn = None
    try:
        if not settings.POSTGRES_URL:
            raise ValueError("POSTGRES_URL is not set in environment.")
            
        final_url = _prepare_postgres_url(settings.POSTGRES_URL)
        conn = psycopg2.connect(final_url)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database connection error: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()

def get_cursor(conn):
    """
    Returns a dictionary cursor so rows can be accessed by column name.
    """
    return conn.cursor(cursor_factory=RealDictCursor)
