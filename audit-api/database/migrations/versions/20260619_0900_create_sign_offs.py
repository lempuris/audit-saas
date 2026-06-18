"""create sign_offs

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-19 09:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sign_offs",
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
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resulting_status", sa.String(), nullable=False),
        sa.Column("signed_by", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
    )
    op.create_index(op.f("ix_sign_offs_engagement_id"), "sign_offs", ["engagement_id"])
    op.create_index(op.f("ix_sign_offs_target_id"), "sign_offs", ["target_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sign_offs_target_id"), table_name="sign_offs")
    op.drop_index(op.f("ix_sign_offs_engagement_id"), table_name="sign_offs")
    op.drop_table("sign_offs")
