"""add_collection_tag_to_conversation_files

Revision ID: 79afc519981f
Revises: 004
Create Date: 2025-11-07 19:38:12.109929

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79afc519981f'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add collection_tag column to conversation_files table
    op.add_column('conversation_files', sa.Column('collection_tag', sa.String(length=100), nullable=True))
    # Add index for efficient lookups
    op.create_index('idx_conversation_files_collection_tag', 'conversation_files', ['collection_tag'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_conversation_files_collection_tag', table_name='conversation_files')
    # Remove column
    op.drop_column('conversation_files', 'collection_tag')