"""create review_notes

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-13 14:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_notes",
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
            "working_paper_id",
            UUID(as_uuid=True),
            sa.ForeignKey("working_papers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("raised_by", sa.String(), nullable=False),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("response", sa.String(), nullable=True),
        sa.Column("responded_by", sa.String(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleared_by", sa.String(), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_review_notes_engagement_id"), "review_notes", ["engagement_id"])
    op.create_index(op.f("ix_review_notes_working_paper_id"), "review_notes", ["working_paper_id"])
    op.create_index(op.f("ix_review_notes_assigned_to"), "review_notes", ["assigned_to"])
    op.create_index(op.f("ix_review_notes_status"), "review_notes", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_review_notes_status"), table_name="review_notes")
    op.drop_index(op.f("ix_review_notes_assigned_to"), table_name="review_notes")
    op.drop_index(op.f("ix_review_notes_working_paper_id"), table_name="review_notes")
    op.drop_index(op.f("ix_review_notes_engagement_id"), table_name="review_notes")
    op.drop_table("review_notes")
