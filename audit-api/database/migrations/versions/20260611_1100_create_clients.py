"""create clients

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-11 11:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("risk_rating", sa.String(), nullable=True),
        sa.Column("contacts", JSONB(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
    )
    op.create_index(op.f("ix_clients_name"), "clients", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_clients_name"), table_name="clients")
    op.drop_table("clients")
