"""Add collections tables for file collection management

Revision ID: 004
Revises: 003
Create Date: 2025-11-05 00:00:00.000000

This migration adds support for file collections:
- collections: Reusable file collections with metadata
- collection_files: Files within each collection
- collection_tags: Tags for organizing collections
- conversation_collections: Many-to-many relationship between conversations and collections

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import TEXT

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collections tables for file collection management."""

    # Create collections table
    op.create_table('collections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('description', TEXT),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('chunk_size', sa.Integer, default=1000),
        sa.Column('chunk_overlap', sa.Integer, default=200),
        sa.Column('is_template', sa.Boolean, default=False),
        sa.Column('max_size_mb', sa.Integer, default=500),
    )

    # Create indexes for collections
    op.create_index('idx_collections_name', 'collections', ['name'])
    op.create_index('idx_collections_created_at', 'collections', ['created_at'])
    op.create_index('idx_collections_is_template', 'collections', ['is_template'])

    # Create collection_files table
    op.create_table('collection_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('collection_id', sa.String(36), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('file_type', sa.String(100)),
        sa.Column('added_at', sa.DateTime, nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),  # SHA256 hash
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
    )

    # Create indexes for collection_files
    op.create_index('idx_collection_files_collection_id', 'collection_files', ['collection_id'])
    op.create_index('idx_collection_files_checksum', 'collection_files', ['checksum'])

    # Create collection_tags table
    op.create_table('collection_tags',
        sa.Column('collection_id', sa.String(36), nullable=False),
        sa.Column('tag', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('collection_id', 'tag'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
    )

    # Create index for collection_tags
    op.create_index('idx_collection_tags_collection_id', 'collection_tags', ['collection_id'])

    # Create conversation_collections table (many-to-many)
    op.create_table('conversation_collections',
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('collection_id', sa.String(36), nullable=False),
        sa.Column('attached_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('conversation_id', 'collection_id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
    )

    # Create indexes for conversation_collections
    op.create_index('idx_conversation_collections_conversation', 'conversation_collections', ['conversation_id'])
    op.create_index('idx_conversation_collections_collection', 'conversation_collections', ['collection_id'])

    # Update schema version
    op.execute("UPDATE schema_version SET version = 4, applied_at = datetime('now')")


def downgrade() -> None:
    """Drop collections tables."""

    # Drop conversation_collections table and indexes
    op.drop_index('idx_conversation_collections_collection', 'conversation_collections')
    op.drop_index('idx_conversation_collections_conversation', 'conversation_collections')
    op.drop_table('conversation_collections')

    # Drop collection_tags table and indexes
    op.drop_index('idx_collection_tags_collection_id', 'collection_tags')
    op.drop_table('collection_tags')

    # Drop collection_files table and indexes
    op.drop_index('idx_collection_files_checksum', 'collection_files')
    op.drop_index('idx_collection_files_collection_id', 'collection_files')
    op.drop_table('collection_files')

    # Drop collections table and indexes
    op.drop_index('idx_collections_is_template', 'collections')
    op.drop_index('idx_collections_created_at', 'collections')
    op.drop_index('idx_collections_name', 'collections')
    op.drop_table('collections')

    # Revert schema version
    op.execute("UPDATE schema_version SET version = 3, applied_at = datetime('now')")
