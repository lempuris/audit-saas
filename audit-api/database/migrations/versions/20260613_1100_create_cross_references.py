"""create cross_references

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-13 11:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cross_references",
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
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.UniqueConstraint("source_type", "source_id", "target_type", "target_id"),
    )
    op.create_index(
        op.f("ix_cross_references_engagement_id"), "cross_references", ["engagement_id"]
    )
    op.create_index(op.f("ix_cross_references_source_id"), "cross_references", ["source_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_cross_references_source_id"), table_name="cross_references")
    op.drop_index(op.f("ix_cross_references_engagement_id"), table_name="cross_references")
    op.drop_table("cross_references")
