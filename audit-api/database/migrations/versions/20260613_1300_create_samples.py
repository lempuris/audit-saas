"""create samples

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-13 13:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "samples",
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
            sa.ForeignKey("working_papers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fs_area", sa.String(), nullable=True),
        sa.Column("population_description", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("population_size", sa.Integer(), nullable=True),
        sa.Column("population_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("tolerable_misstatement", sa.Numeric(18, 2), nullable=False),
        sa.Column("expected_misstatement", sa.Numeric(18, 2), nullable=False),
        sa.Column("confidence_level", sa.Integer(), nullable=False),
        sa.Column("reliability_factor", sa.Numeric(5, 2), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("selection_basis", JSONB(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
    )
    op.create_index(op.f("ix_samples_engagement_id"), "samples", ["engagement_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_samples_engagement_id"), table_name="samples")
    op.drop_table("samples")
