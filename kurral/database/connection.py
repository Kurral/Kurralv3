"""
Database connection and session management for PostgreSQL/Supabase
"""

import warnings
from typing import Optional, Generator
from contextlib import contextmanager

try:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    declarative_base = None

# Base will be imported from models after models is defined
# We'll import it conditionally to avoid circular imports


class DatabaseConnection:
    """Manages database connection and sessions"""
    
    def __init__(self, database_url: str):
        """
        Initialize database connection
        
        Args:
            database_url: PostgreSQL connection string
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "SQLAlchemy is required for PostgreSQL support. "
                "Install it with: pip install sqlalchemy psycopg2-binary"
            )
        
        self.database_url = database_url
        
        # Create engine with connection pooling
        # Use NullPool for simple use cases (no connection pooling)
        # For production, consider using connection pooling
        try:
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,  # Verify connections before using
                poolclass=NullPool,  # Simple connection management
                echo=False,  # Set to True for SQL debugging
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create database engine: {e}")
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self._tables_created = False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db_conn.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self) -> None:
        """Create database tables if they don't exist"""
        if not self._tables_created:
            try:
                # Import Base from models (avoid circular import)
                from kurral.database.models import Base
                if Base:
                    Base.metadata.create_all(bind=self.engine)
                    self._tables_created = True
            except Exception as e:
                warnings.warn(f"Failed to create database tables: {e}")
                raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            warnings.warn(f"Database connection test failed: {e}")
            return False


# Global connection instance (lazy initialization)
_db_connection: Optional[DatabaseConnection] = None


def get_db_connection(database_url: Optional[str] = None) -> Optional[DatabaseConnection]:
    """
    Get or create database connection
    
    Args:
        database_url: Optional database URL (if not provided, returns None)
        
    Returns:
        DatabaseConnection instance or None if database_url is not provided
    """
    global _db_connection
    
    if not database_url:
        return None
    
    if not SQLALCHEMY_AVAILABLE:
        return None
    
    # Create new connection if URL changed or doesn't exist
    if _db_connection is None or _db_connection.database_url != database_url:
        _db_connection = DatabaseConnection(database_url)
        # Create tables on first connection
        try:
            _db_connection.create_tables()
        except Exception as e:
            warnings.warn(f"Failed to create database tables: {e}")
    
    return _db_connection


def get_db_session(database_url: Optional[str] = None) -> Optional[Generator[Session, None, None]]:
    """
    Get database session generator
    
    Args:
        database_url: Optional database URL
        
    Returns:
        Session generator or None if database_url is not provided
    """
    db_conn = get_db_connection(database_url)
    if db_conn is None:
        return None
    return db_conn.get_session()


def create_tables(database_url: Optional[str] = None) -> None:
    """
    Create database tables
    
    Args:
        database_url: Optional database URL
    """
    db_conn = get_db_connection(database_url)
    if db_conn:
        try:
            db_conn.create_tables()
        except Exception as e:
            warnings.warn(f"Failed to create database tables: {e}")

