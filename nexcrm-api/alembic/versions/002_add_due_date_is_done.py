"""add due_date and is_done to activities

Revision ID: 002
Revises: 001
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001_add_tags'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('activities') as batch_op:
        batch_op.add_column(sa.Column('due_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_done', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('activities') as batch_op:
        batch_op.drop_column('is_done')
        batch_op.drop_column('due_date')
