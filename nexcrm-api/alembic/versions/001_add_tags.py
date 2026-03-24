"""add tags to contacts and leads

Revision ID: 001_add_tags
Revises:
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '001_add_tags'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tags column to contacts — SQLite supports JSON stored as TEXT
    with op.batch_alter_table('contacts') as batch_op:
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))

    with op.batch_alter_table('leads') as batch_op:
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('contacts') as batch_op:
        batch_op.drop_column('tags')

    with op.batch_alter_table('leads') as batch_op:
        batch_op.drop_column('tags')
