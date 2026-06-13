"""create tick_marks, tick_mark_applications

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-13 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tick_marks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("meaning", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("symbol"),
    )

    op.create_table(
        "tick_mark_applications",
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
        sa.Column(
            "tick_mark_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tick_marks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("applied_by", sa.String(), nullable=False),
        sa.UniqueConstraint("tick_mark_id", "target_type", "target_id"),
    )
    op.create_index(
        op.f("ix_tick_mark_applications_engagement_id"),
        "tick_mark_applications",
        ["engagement_id"],
    )
    op.create_index(
        op.f("ix_tick_mark_applications_target_id"), "tick_mark_applications", ["target_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tick_mark_applications_target_id"), table_name="tick_mark_applications")
    op.drop_index(
        op.f("ix_tick_mark_applications_engagement_id"), table_name="tick_mark_applications"
    )
    op.drop_table("tick_mark_applications")
    op.drop_table("tick_marks")
