"""create engagement_reports

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-19 11:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_reports",
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
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("opinion_type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("letterhead", sa.String(), nullable=False),
        sa.Column("sections", JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.UniqueConstraint("engagement_id", "report_type"),
    )
    op.create_index(
        op.f("ix_engagement_reports_engagement_id"), "engagement_reports", ["engagement_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_engagement_reports_engagement_id"), table_name="engagement_reports")
    op.drop_table("engagement_reports")
