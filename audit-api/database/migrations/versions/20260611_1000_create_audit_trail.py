"""create audit_trail

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11 10:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_trail",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor_clerk_user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("before", JSONB(), nullable=True),
        sa.Column("after", JSONB(), nullable=True),
    )
    op.create_index(
        op.f("ix_audit_trail_actor_clerk_user_id"), "audit_trail", ["actor_clerk_user_id"]
    )
    op.create_index(op.f("ix_audit_trail_entity_type"), "audit_trail", ["entity_type"])
    op.create_index(op.f("ix_audit_trail_entity_id"), "audit_trail", ["entity_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_trail_entity_id"), table_name="audit_trail")
    op.drop_index(op.f("ix_audit_trail_entity_type"), table_name="audit_trail")
    op.drop_index(op.f("ix_audit_trail_actor_clerk_user_id"), table_name="audit_trail")
    op.drop_table("audit_trail")
