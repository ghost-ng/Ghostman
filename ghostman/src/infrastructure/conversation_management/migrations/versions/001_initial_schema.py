"""Initial conversation management schema

Revision ID: 001
Revises: 
Create Date: 2025-08-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import TEXT

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial conversation management tables."""
    
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('model_used', sa.String(100)),
        sa.Column('tags_json', TEXT, default='[]'),
        sa.Column('category', sa.String(100)),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('is_favorite', sa.Boolean, default=False),
        sa.Column('metadata_json', TEXT, default='{}'),
        sa.CheckConstraint("status IN ('active', 'archived', 'pinned', 'deleted')", name='check_status'),
        sa.CheckConstraint("priority BETWEEN -1 AND 1", name='check_priority'),
    )
    
    # Create indexes for conversations
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_conversations_created_at', 'conversations', ['created_at'])
    op.create_index('idx_conversations_updated_at', 'conversations', ['updated_at'])
    op.create_index('idx_conversations_title', 'conversations', ['title'])
    op.create_index('idx_conversations_category', 'conversations', ['category'])
    op.create_index('idx_conversations_is_favorite', 'conversations', ['is_favorite'])
    op.create_index('idx_conversations_status_updated', 'conversations', ['status', 'updated_at'])
    op.create_index('idx_conversations_category_status', 'conversations', ['category', 'status'])
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', TEXT, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('token_count', sa.Integer),
        sa.Column('metadata_json', TEXT, default='{}'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('system', 'user', 'assistant')", name='check_role'),
    )
    
    # Create indexes for messages
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_messages_role', 'messages', ['role'])
    op.create_index('idx_messages_timestamp', 'messages', ['timestamp'])
    op.create_index('idx_messages_conversation_timestamp', 'messages', ['conversation_id', 'timestamp'])
    op.create_index('idx_messages_role_timestamp', 'messages', ['role', 'timestamp'])
    
    # Create tags table
    op.create_table('tags',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # Create indexes for tags
    op.create_index('idx_tags_name', 'tags', ['name'])
    op.create_index('idx_tags_usage_count', 'tags', ['usage_count'])
    op.create_index('idx_tags_usage_name', 'tags', ['usage_count', 'name'])
    
    # Create conversation_tags association table
    op.create_table('conversation_tags',
        sa.Column('conversation_id', sa.String(36), primary_key=True),
        sa.Column('tag_id', sa.Integer, primary_key=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    )
    
    # Create conversation_summaries table
    op.create_table('conversation_summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), nullable=False, unique=True),
        sa.Column('summary', TEXT, nullable=False),
        sa.Column('key_topics_json', TEXT, default='[]'),
        sa.Column('generated_at', sa.DateTime, nullable=False),
        sa.Column('model_used', sa.String(100)),
        sa.Column('confidence_score', sa.Float),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for summaries
    op.create_index('idx_summaries_conversation_id', 'conversation_summaries', ['conversation_id'])
    op.create_index('idx_summaries_generated_at', 'conversation_summaries', ['generated_at'])
    
    # Create full-text search table
    op.create_table('conversations_fts',
        sa.Column('conversation_id', sa.String(36), primary_key=True),
        sa.Column('title', TEXT),
        sa.Column('content', TEXT),
        sa.Column('tags', TEXT),
        sa.Column('category', TEXT),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    )
    
    # Create schema_version table for tracking
    op.create_table('schema_version',
        sa.Column('version', sa.Integer, primary_key=True),
        sa.Column('applied_at', sa.DateTime, nullable=False),
    )
    
    # Insert initial schema version
    op.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, datetime('now'))")


def downgrade() -> None:
    """Drop all conversation management tables."""
    
    op.drop_table('schema_version')
    op.drop_table('conversations_fts')
    op.drop_table('conversation_summaries')
    op.drop_table('conversation_tags')
    op.drop_table('tags')
    op.drop_table('messages')
    op.drop_table('conversations')