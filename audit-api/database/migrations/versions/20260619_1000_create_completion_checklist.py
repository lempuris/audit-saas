"""create completion_checklist_items

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-19 10:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completion_checklist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "engagement_id", UUID(as_uuid=True), sa.ForeignKey("engagements.id"), nullable=False
        ),
        sa.Column("item_key", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("isa_reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("engagement_id", "item_key"),
    )
    op.create_index(
        op.f("ix_completion_checklist_items_engagement_id"),
        "completion_checklist_items",
        ["engagement_id"],
    )
    op.create_index(
        op.f("ix_completion_checklist_items_status"),
        "completion_checklist_items",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_completion_checklist_items_status"), table_name="completion_checklist_items"
    )
    op.drop_index(
        op.f("ix_completion_checklist_items_engagement_id"),
        table_name="completion_checklist_items",
    )
    op.drop_table("completion_checklist_items")
