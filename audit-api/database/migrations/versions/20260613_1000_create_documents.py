"""create documents

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-13 10:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
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
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("s3_version_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("uploaded_by", sa.String(), nullable=False),
        sa.UniqueConstraint("s3_key"),
    )
    op.create_index(op.f("ix_documents_engagement_id"), "documents", ["engagement_id"])
    op.create_index(op.f("ix_documents_working_paper_id"), "documents", ["working_paper_id"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_working_paper_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_engagement_id"), table_name="documents")
    op.drop_table("documents")
