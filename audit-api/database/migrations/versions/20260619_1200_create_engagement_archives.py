"""create engagement_archives

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-19 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_archives",
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
        sa.Column("archived_by", sa.String(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_years", sa.Integer(), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_engagement_archives_engagement_id"), "engagement_archives", ["engagement_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_engagement_archives_engagement_id"), table_name="engagement_archives")
    op.drop_table("engagement_archives")
