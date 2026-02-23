"""
Migration management utilities for Specter conversation database.

Provides utilities to run Alembic migrations programmatically and manage
database schema versioning.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import text

logger = logging.getLogger("specter.migrations")


class MigrationManager:
    """Manages database migrations using Alembic."""
    
    def __init__(self, db_manager=None):
        """Initialize migration manager."""
        self.db_manager = db_manager
        
        # Set up Alembic config
        self.migrations_dir = Path(__file__).parent
        self.alembic_cfg_path = self.migrations_dir.parent / "alembic.ini"
        
        if not self.alembic_cfg_path.exists():
            raise FileNotFoundError(f"Alembic config not found: {self.alembic_cfg_path}")
        
        self.alembic_cfg = Config(str(self.alembic_cfg_path))
        self.alembic_cfg.set_main_option("script_location", str(self.migrations_dir))
        
        # Set the database URL if db_manager is provided
        if self.db_manager and hasattr(self.db_manager, 'db_path'):
            db_url = f"sqlite:///{self.db_manager.db_path}"
            self.alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    def run_migrations(self, target_revision: Optional[str] = "head") -> bool:
        """Run database migrations to target revision."""
        try:
            logger.info(f"Running migrations to revision: {target_revision}")
            command.upgrade(self.alembic_cfg, target_revision)
            logger.info("✓ Database migrations completed successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Migration failed: {e}")
            return False
    
    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """Create a new migration file."""
        try:
            logger.info(f"Creating migration: {message}")
            command.revision(
                self.alembic_cfg, 
                message=message, 
                autogenerate=autogenerate
            )
            logger.info("✓ Migration file created successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create migration: {e}")
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            if not self.db_manager:
                return None
                
            with self.db_manager.get_session() as session:
                result = session.execute(text("SELECT version_num FROM alembic_version")).first()
                return result[0] if result else None
        except Exception as e:
            logger.debug(f"Could not get current revision: {e}")
            return None
    
    def get_head_revision(self) -> Optional[str]:
        """Get the latest available revision."""
        try:
            from alembic.script import ScriptDirectory
            script = ScriptDirectory.from_config(self.alembic_cfg)
            return script.get_current_head()
        except Exception as e:
            logger.error(f"Could not get head revision: {e}")
            return None
    
    def is_database_up_to_date(self) -> bool:
        """Check if database is up to date with latest migrations."""
        try:
            current = self.get_current_revision()
            head = self.get_head_revision()
            return current == head and current is not None
        except Exception as e:
            logger.error(f"Could not check migration status: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize database with latest schema."""
        try:
            # Run migrations to create/update schema
            if not self.run_migrations():
                return False
            
            # Verify database is working
            if self.db_manager:
                with self.db_manager.get_session() as session:
                    # Test query
                    session.execute(text("SELECT 1"))
                
            logger.info("✓ Database initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset database by dropping all tables and re-running migrations."""
        try:
            logger.warning("Resetting database - all data will be lost!")
            
            if self.db_manager:
                # Drop all tables
                from ..models.database_models import Base
                Base.metadata.drop_all(self.db_manager.get_engine())
                
                # Recreate with migrations
                return self.initialize_database()
            
            return False
            
        except Exception as e:
            logger.error(f"✗ Database reset failed: {e}")
            return False
    
    def get_migration_history(self) -> list:
        """Get migration history."""
        try:
            from alembic.script import ScriptDirectory
            script = ScriptDirectory.from_config(self.alembic_cfg)
            
            history = []
            for revision in script.walk_revisions():
                history.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'description': revision.doc,
                    'is_current': revision.revision == self.get_current_revision()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Could not get migration history: {e}")
            return []


def run_migrations_from_cli():
    """CLI entry point for running migrations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Specter database migrations')
    parser.add_argument('--target', default='head', help='Target revision (default: head)')
    parser.add_argument('--reset', action='store_true', help='Reset database')
    parser.add_argument('--create', help='Create new migration with message')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        from ..repositories.database import DatabaseManager
        db_manager = DatabaseManager()
        migration_manager = MigrationManager(db_manager)
        
        if args.reset:
            success = migration_manager.reset_database()
        elif args.create:
            success = migration_manager.create_migration(args.create)
        elif args.status:
            current = migration_manager.get_current_revision()
            head = migration_manager.get_head_revision()
            up_to_date = migration_manager.is_database_up_to_date()
            
            print(f"Current revision: {current or 'None'}")
            print(f"Head revision: {head or 'None'}")
            print(f"Up to date: {'Yes' if up_to_date else 'No'}")
            
            print("\nMigration history:")
            for migration in migration_manager.get_migration_history():
                marker = "* " if migration['is_current'] else "  "
                print(f"{marker}{migration['revision']}: {migration['description']}")
            
            success = True
        else:
            success = migration_manager.run_migrations(args.target)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Migration command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations_from_cli()