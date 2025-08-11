"""
Database manager for conversation storage using SQLite.
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading

logger = logging.getLogger("ghostman.conversation_db")


class DatabaseManager:
    """Manages SQLite database for conversation storage."""
    
    SCHEMA_VERSION = 1
    
    # SQL Schema
    SCHEMA_SQL = """
    -- Conversations table
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        metadata_json TEXT DEFAULT '{}',
        
        -- Indexes for performance
        INDEX (status),
        INDEX (created_at),
        INDEX (updated_at),
        INDEX (title)
    );
    
    -- Messages table
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        token_count INTEGER,
        metadata_json TEXT DEFAULT '{}',
        
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        INDEX (conversation_id),
        INDEX (role),
        INDEX (timestamp)
    );
    
    -- Conversation summaries table
    CREATE TABLE IF NOT EXISTS conversation_summaries (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL UNIQUE,
        summary TEXT NOT NULL,
        key_topics_json TEXT DEFAULT '[]',
        generated_at TIMESTAMP NOT NULL,
        model_used TEXT,
        confidence_score REAL,
        
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        INDEX (conversation_id),
        INDEX (generated_at)
    );
    
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
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager."""
        from ...storage.settings_manager import settings
        
        if db_path is None:
            # Store in same directory as settings
            settings_dir = Path(settings.get_paths()['settings_dir'])
            db_path = settings_dir / "conversations.db"
        
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
            logger.error(f"Database vacuum failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Table counts
                cursor = conn.execute("SELECT COUNT(*) FROM conversations")
                stats['conversations'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                stats['messages'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM conversation_summaries")
                stats['summaries'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM tags")
                stats['tags'] = cursor.fetchone()[0]
                
                # Database file size
                stats['file_size_bytes'] = self.db_path.stat().st_size
                
                # Most used tags
                cursor = conn.execute("""
                    SELECT name, usage_count 
                    FROM tags 
                    ORDER BY usage_count DESC 
                    LIMIT 10
                """)
                stats['top_tags'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def close(self):
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            try:
                self._local.connection.close()
                delattr(self._local, 'connection')
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
        
        logger.info("Database connections closed")
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized