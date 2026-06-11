"""create risks

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-12 11:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risks",
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
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("fs_area", sa.String(), nullable=True),
        sa.Column("assertions", JSONB(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("inherent_rating", sa.String(), nullable=False),
        sa.Column("control_rating", sa.String(), nullable=False),
        sa.Column("combined_rating", sa.String(), nullable=False),
        sa.Column("is_significant", sa.Boolean(), nullable=False),
        sa.Column("planned_response", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
    )
    op.create_index(op.f("ix_risks_engagement_id"), "risks", ["engagement_id"])
    op.create_index(op.f("ix_risks_fs_area"), "risks", ["fs_area"])


def downgrade() -> None:
    op.drop_index(op.f("ix_risks_fs_area"), table_name="risks")
    op.drop_index(op.f("ix_risks_engagement_id"), table_name="risks")
    op.drop_table("risks")
