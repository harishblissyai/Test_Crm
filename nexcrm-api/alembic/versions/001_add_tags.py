"""add tags to contacts and leads

Revision ID: 001_add_tags
Revises:
Create Date: 2026-03-24
"""
import sqlalchemy as sa
from alembic import op

revision = '001_add_tags'
down_revision = None
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    # Table may not exist yet on a brand-new DB
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _column_exists("contacts", "tags"):
        with op.batch_alter_table("contacts") as batch_op:
            batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))

    if not _column_exists("leads", "tags"):
        with op.batch_alter_table("leads") as batch_op:
            batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _column_exists("contacts", "tags"):
        with op.batch_alter_table("contacts") as batch_op:
            batch_op.drop_column("tags")

    if _column_exists("leads", "tags"):
        with op.batch_alter_table("leads") as batch_op:
            batch_op.drop_column("tags")
