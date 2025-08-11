"""
Database management for conversations.

Provides SQLite database operations for conversation persistence with full-text search,
proper indexing, and thread-safe operations.
"""

import sqlite3
import threading
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ghostman.conversation_db")


class DatabaseManager:
    """Manages SQLite database for conversation storage."""
    
    SCHEMA_VERSION = 1
    SCHEMA_SQL = """
    -- Main conversations table
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('active', 'archived', 'pinned')),
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        message_count INTEGER DEFAULT 0,
        model_used TEXT,
        tags_json TEXT DEFAULT '[]',
        category TEXT,
        priority INTEGER DEFAULT 0,
        is_favorite BOOLEAN DEFAULT 0,
        metadata_json TEXT DEFAULT '{}'
    );
    
    -- Create indexes for conversations table
    CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
    CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
    CREATE INDEX IF NOT EXISTS idx_conversations_title ON conversations(title);
    CREATE INDEX IF NOT EXISTS idx_conversations_category ON conversations(category);
    CREATE INDEX IF NOT EXISTS idx_conversations_is_favorite ON conversations(is_favorite);
    
    -- Messages table
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
        content TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        token_count INTEGER,
        metadata_json TEXT DEFAULT '{}',
        
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    
    -- Create indexes for messages table
    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
    CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
    CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
    
    -- Conversation summaries table
    CREATE TABLE IF NOT EXISTS conversation_summaries (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL UNIQUE,
        summary TEXT NOT NULL,
        key_topics_json TEXT DEFAULT '[]',
        generated_at TIMESTAMP NOT NULL,
        model_used TEXT,
        confidence_score REAL,
        
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    
    -- Create indexes for conversation_summaries table
    CREATE INDEX IF NOT EXISTS idx_summaries_conversation_id ON conversation_summaries(conversation_id);
    CREATE INDEX IF NOT EXISTS idx_summaries_generated_at ON conversation_summaries(generated_at);
    
    -- Full-text search virtual table
    CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
        conversation_id UNINDEXED,
        title,
        content,
        tags,
        category
    );
    
    -- Tags table for normalization
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        usage_count INTEGER DEFAULT 0,
        created_at TIMESTAMP NOT NULL
    );
    
    -- Create index for tags table
    CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
    CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags(usage_count);
    
    -- Conversation-tags junction table
    CREATE TABLE IF NOT EXISTS conversation_tags (
        conversation_id TEXT NOT NULL,
        tag_id INTEGER NOT NULL,
        
        PRIMARY KEY (conversation_id, tag_id),
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );
    
    -- Schema version table
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP NOT NULL
    );
    
    -- Insert initial schema version
    INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager."""
        from ...storage.settings_manager import settings
        
        if db_path is None:
            # Store in db subdirectory of Ghostman data directory
            settings_paths = settings.get_paths()
            settings_dir = Path(settings_paths['settings_dir'])
            # Go up one level from configs to Ghostman root, then into db
            ghostman_root = settings_dir.parent
            db_dir = ghostman_root / "db"
            db_path = db_dir / "conversations.db"
        
        self.db_path = db_path
        self._local = threading.local()
        self._initialized = False
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Database path: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            # Row factory for easier access
            self._local.connection.row_factory = sqlite3.Row
            
        return self._local.connection
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
    
    def initialize(self) -> bool:
        """Initialize database schema."""
        try:
            with self.get_connection() as conn:
                # Execute schema
                conn.executescript(self.SCHEMA_SQL)
                
                # Check/update schema version
                current_version = self._get_schema_version(conn)
                if current_version < self.SCHEMA_VERSION:
                    self._migrate_schema(conn, current_version)
                
                self._initialized = True
                logger.info("✅ Database initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0
    
    def _migrate_schema(self, conn: sqlite3.Connection, from_version: int):
        """Migrate database schema."""
        logger.info(f"Migrating database from version {from_version} to {self.SCHEMA_VERSION}")
        
        # Add migration logic here for future schema changes
        # For now, just update version
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (self.SCHEMA_VERSION,)
        )
        
        logger.info("✅ Database migration completed")
    
    def vacuum(self):
        """Optimize database by running VACUUM."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("Database optimized")
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
    
    def close_all_connections(self):
        """Close all thread-local connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
        logger.debug("Database connections closed")
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized