"""create materiality_assessments

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-12 10:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "materiality_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "engagement_id",
            UUID(as_uuid=True),
            sa.ForeignKey("engagements.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("benchmark", sa.String(), nullable=False),
        sa.Column("benchmark_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("overall_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("overall_materiality", sa.Numeric(18, 2), nullable=False),
        sa.Column("performance_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("performance_materiality", sa.Numeric(18, 2), nullable=False),
        sa.Column("clearly_trivial_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("clearly_trivial_threshold", sa.Numeric(18, 2), nullable=False),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_materiality_assessments_engagement_id"),
        "materiality_assessments",
        ["engagement_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_materiality_assessments_engagement_id"), table_name="materiality_assessments"
    )
    op.drop_table("materiality_assessments")
