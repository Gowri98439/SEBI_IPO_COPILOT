"""fix_audit_event_workspace_nullable

Revision ID: 0dc32cdbaea6
Revises: 267fccb50e98
Create Date: 2026-08-09 12:07:10.109061

SQLite does not support ALTER COLUMN, so we use batch_alter_table
which re-creates the table internally (safe for SQLite).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0dc32cdbaea6'
down_revision: Union[str, None] = '267fccb50e98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite-compatible column alteration via batch mode
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.alter_column(
            'workspace_id',
            existing_type=sa.VARCHAR(length=36),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.alter_column(
            'workspace_id',
            existing_type=sa.VARCHAR(length=36),
            nullable=False,
        )
