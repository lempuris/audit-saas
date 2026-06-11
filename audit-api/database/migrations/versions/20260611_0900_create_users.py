"""create users

Revision ID: 0001
Revises:
Create Date: 2026-06-11 09:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index(op.f("ix_users_clerk_user_id"), "users", ["clerk_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_clerk_user_id"), table_name="users")
    op.drop_table("users")
