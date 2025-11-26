"""Database connection and client management"""

from functools import lru_cache
from typing import Optional

from supabase import Client, create_client

from app.core.config import get_settings

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get Supabase client with connection pooling"""
    global _client
    
    if _client is None:
        settings = get_settings()
        _client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_anon_key
        )
    
    return _client


def health_check() -> bool:
    """Check database connection health"""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        result = client.table("prefix_metadata").select("count", count="exact").limit(0).execute()
        return True
    except Exception:
        return False
