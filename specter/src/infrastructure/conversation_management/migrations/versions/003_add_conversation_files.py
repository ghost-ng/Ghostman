"""Add conversation_files table for RAG file associations

Revision ID: 003
Revises: 002
Create Date: 2025-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import TEXT

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create conversation_files table for file associations."""
    
    # Create conversation_files table
    op.create_table('conversation_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('file_id', sa.String(500), nullable=False),  # File identifier used in RAG pipeline
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000)),  # Original file path
        sa.Column('file_size', sa.Integer, default=0),
        sa.Column('file_type', sa.String(100)),
        sa.Column('upload_timestamp', sa.DateTime, nullable=False),
        sa.Column('processing_status', sa.String(20), default='queued'),  # queued, processing, completed, failed
        sa.Column('chunk_count', sa.Integer, default=0),  # Number of chunks created in RAG
        sa.Column('is_enabled', sa.Boolean, default=True),  # Whether file is enabled for context
        sa.Column('metadata_json', TEXT, default='{}'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.CheckConstraint("processing_status IN ('queued', 'processing', 'completed', 'failed')", name='check_processing_status'),
    )
    
    # Create indexes for conversation_files
    op.create_index('idx_conversation_files_conversation_id', 'conversation_files', ['conversation_id'])
    op.create_index('idx_conversation_files_file_id', 'conversation_files', ['file_id'])
    op.create_index('idx_conversation_files_processing_status', 'conversation_files', ['processing_status'])
    op.create_index('idx_conversation_files_is_enabled', 'conversation_files', ['is_enabled'])
    op.create_index('idx_conversation_files_upload_timestamp', 'conversation_files', ['upload_timestamp'])
    op.create_index('idx_conversation_files_conv_status', 'conversation_files', ['conversation_id', 'processing_status'])
    op.create_index('idx_conversation_files_conv_enabled', 'conversation_files', ['conversation_id', 'is_enabled'])
    
    # Update schema version
    op.execute("UPDATE schema_version SET version = 3, applied_at = datetime('now')")


def downgrade() -> None:
    """Drop conversation_files table."""
    
    # Drop indexes first
    op.drop_index('idx_conversation_files_conv_enabled', 'conversation_files')
    op.drop_index('idx_conversation_files_conv_status', 'conversation_files')
    op.drop_index('idx_conversation_files_upload_timestamp', 'conversation_files')
    op.drop_index('idx_conversation_files_is_enabled', 'conversation_files')
    op.drop_index('idx_conversation_files_processing_status', 'conversation_files')
    op.drop_index('idx_conversation_files_file_id', 'conversation_files')
    op.drop_index('idx_conversation_files_conversation_id', 'conversation_files')
    
    # Drop table
    op.drop_table('conversation_files')
    
    # Revert schema version
    op.execute("UPDATE schema_version SET version = 2, applied_at = datetime('now')")