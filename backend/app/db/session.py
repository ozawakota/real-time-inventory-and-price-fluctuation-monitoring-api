"""
Database session management
"""
from app.core.database import get_db

# Re-export get_db for convenience
__all__ = ["get_db"]