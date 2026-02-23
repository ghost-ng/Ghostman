"""
SQLAlchemy database management for conversations.

Provides SQLAlchemy ORM database operations with proper session management,
connection pooling, and migration support using Alembic.
"""

import logging
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..models.database_models import Base

logger = logging.getLogger("specter.conversation_db")


class DatabaseManager:
    """
    Manages SQLAlchemy database for conversation storage.

    Singleton pattern ensures only one instance exists to prevent
    multiple mapper configurations that can cause recursion issues.
    """

    _instance: Optional['DatabaseManager'] = None
    _lock = None  # Will be initialized to threading.Lock() on first use

    def __new__(cls, db_path: Optional[Path] = None):
        """Singleton pattern - returns same instance for all calls."""
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()

        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._singleton_initialized = False
            return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLAlchemy database manager."""
        # Skip re-initialization for singleton
        if self._singleton_initialized:
            return

        from ...storage.settings_manager import settings

        if db_path is None:
            # Store in db subdirectory of Specter data directory
            settings_paths = settings.get_paths()
            settings_dir = Path(settings_paths['settings_dir'])
            # Go up one level from configs to Specter root, then into db
            specter_root = settings_dir.parent
            db_dir = specter_root / "db"
            db_path = db_dir / "conversations.db"

        self.db_path = db_path
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._initialized = False

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._singleton_initialized = True
        logger.info(f"Database path: {self.db_path}")
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with proper SQLite configuration."""
        # SQLite URL - convert Windows backslashes to forward slashes
        database_url = f"sqlite:///{str(self.db_path).replace(chr(92), '/')}"
        
        engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30.0,
            },
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        
        # Configure SQLite for better performance and data integrity
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Optimize for speed vs safety (adjust as needed)
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
        
        return engine
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def initialize(self, run_migrations: bool = False) -> bool:
        """Initialize SQLAlchemy database with optional migrations."""
        try:
            # Create engine and session factory
            self._engine = self._create_engine()
            self._session_factory = sessionmaker(bind=self._engine)
            
            if run_migrations:
                # Run database migrations using Alembic
                try:
                    from ..migrations.migration_manager import MigrationManager
                    migration_manager = MigrationManager(self)
                    
                    if not migration_manager.is_database_up_to_date():
                        logger.info("Database needs migration, running migrations...")
                        if not migration_manager.run_migrations():
                            logger.error("Migration failed, falling back to direct table creation")
                            Base.metadata.create_all(self._engine)
                    else:
                        logger.info("Database is up to date")

                except ImportError:
                    logger.warning("Alembic not available, creating tables directly")
                    Base.metadata.create_all(self._engine)
                except Exception as e:
                    logger.warning(f"Migration failed ({e}), falling back to direct table creation")
                    Base.metadata.create_all(self._engine)
            else:
                # Create tables directly without migrations
                Base.metadata.create_all(self._engine)
            
            # Mark as initialized before testing connection
            self._initialized = True
            
            # Test connection
            try:
                with self.get_session() as session:
                    # Simple query to test the connection using SQLAlchemy
                    from sqlalchemy import text
                    session.execute(text("SELECT 1"))
            except Exception as e:
                self._initialized = False
                raise
            logger.info("✓ SQLAlchemy database initialized successfully")
            return True
                
        except Exception as e:
            logger.error(f"✗ SQLAlchemy database initialization failed: {e}")
            return False
    
    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        if not self._engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    def create_session(self) -> Session:
        """Create a new database session."""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()
    
    def vacuum(self):
        """Optimize database by running VACUUM."""
        try:
            with self._engine.connect() as conn:
                conn.execute("VACUUM")
            logger.info("Database optimized")
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
    
    def close_all_connections(self):
        """Close database engine and all connections."""
        if self._engine:
            self._engine.dispose()
            logger.debug("Database engine disposed")
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized