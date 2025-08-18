"""Fix deleted status constraint

Revision ID: 002
Revises: 001
Create Date: 2025-08-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 'deleted' status to conversations status constraint."""
    
    # SQLite doesn't support ALTER CONSTRAINT, so we need to recreate the table
    # First, create a new table with the correct constraint
    op.create_table('conversations_new',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('model_used', sa.String(100)),
        sa.Column('tags_json', sa.Text, default='[]'),
        sa.Column('category', sa.String(100)),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('is_favorite', sa.Boolean, default=False),
        sa.Column('metadata_json', sa.Text, default='{}'),
        sa.CheckConstraint("status IN ('active', 'archived', 'pinned', 'deleted')", name='check_status'),
        sa.CheckConstraint("priority BETWEEN -1 AND 1", name='check_priority'),
    )
    
    # Copy data from old table to new table
    op.execute("""
        INSERT INTO conversations_new (
            id, title, status, created_at, updated_at, message_count,
            model_used, tags_json, category, priority, is_favorite, metadata_json
        )
        SELECT 
            id, title, status, created_at, updated_at, message_count,
            model_used, tags_json, category, priority, is_favorite, metadata_json
        FROM conversations
    """)
    
    # Drop old table
    op.drop_table('conversations')
    
    # Rename new table
    op.rename_table('conversations_new', 'conversations')
    
    # Recreate indexes
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_conversations_created_at', 'conversations', ['created_at'])
    op.create_index('idx_conversations_updated_at', 'conversations', ['updated_at'])
    op.create_index('idx_conversations_title', 'conversations', ['title'])
    op.create_index('idx_conversations_category', 'conversations', ['category'])
    op.create_index('idx_conversations_is_favorite', 'conversations', ['is_favorite'])
    op.create_index('idx_conversations_status_updated', 'conversations', ['status', 'updated_at'])
    op.create_index('idx_conversations_category_status', 'conversations', ['category', 'status'])


def downgrade() -> None:
    """Remove 'deleted' status from conversations status constraint."""
    
    # Create a new table without 'deleted' in the constraint
    op.create_table('conversations_old',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('model_used', sa.String(100)),
        sa.Column('tags_json', sa.Text, default='[]'),
        sa.Column('category', sa.String(100)),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('is_favorite', sa.Boolean, default=False),
        sa.Column('metadata_json', sa.Text, default='{}'),
        sa.CheckConstraint("status IN ('active', 'archived', 'pinned')", name='check_status'),
        sa.CheckConstraint("priority BETWEEN -1 AND 1", name='check_priority'),
    )
    
    # Copy data excluding any 'deleted' status records
    op.execute("""
        INSERT INTO conversations_old (
            id, title, status, created_at, updated_at, message_count,
            model_used, tags_json, category, priority, is_favorite, metadata_json
        )
        SELECT 
            id, title, status, created_at, updated_at, message_count,
            model_used, tags_json, category, priority, is_favorite, metadata_json
        FROM conversations
        WHERE status != 'deleted'
    """)
    
    # Drop current table
    op.drop_table('conversations')
    
    # Rename old table back
    op.rename_table('conversations_old', 'conversations')
    
    # Recreate indexes
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_conversations_created_at', 'conversations', ['created_at'])
    op.create_index('idx_conversations_updated_at', 'conversations', ['updated_at'])
    op.create_index('idx_conversations_title', 'conversations', ['title'])
    op.create_index('idx_conversations_category', 'conversations', ['category'])
    op.create_index('idx_conversations_is_favorite', 'conversations', ['is_favorite'])
    op.create_index('idx_conversations_status_updated', 'conversations', ['status', 'updated_at'])
    op.create_index('idx_conversations_category_status', 'conversations', ['category', 'status'])