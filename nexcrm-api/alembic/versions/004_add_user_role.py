"""add role to users

Revision ID: 004
Revises: 003
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'  # 003_add_notifications
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(), nullable=False, server_default='member'))

    # Promote the first user (id=1) to admin
    op.execute("UPDATE users SET role = 'admin' WHERE id = (SELECT MIN(id) FROM users)")


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('role')
