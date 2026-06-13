"""create working_papers, working_paper_versions

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-13 09:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "working_papers",
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
        sa.Column("fs_area", sa.String(), nullable=False),
        sa.Column("index_ref", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("conclusion", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "procedure_id",
            UUID(as_uuid=True),
            sa.ForeignKey("engagement_procedures.id"),
            nullable=True,
        ),
        sa.Column("prepared_by", sa.String(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.UniqueConstraint("engagement_id", "index_ref"),
    )
    op.create_index(op.f("ix_working_papers_engagement_id"), "working_papers", ["engagement_id"])
    op.create_index(op.f("ix_working_papers_fs_area"), "working_papers", ["fs_area"])
    op.create_index(op.f("ix_working_papers_status"), "working_papers", ["status"])

    op.create_table(
        "working_paper_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "working_paper_id",
            UUID(as_uuid=True),
            sa.ForeignKey("working_papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("index_ref", sa.String(), nullable=False),
        sa.Column("fs_area", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("conclusion", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("edited_by", sa.String(), nullable=False),
        sa.UniqueConstraint("working_paper_id", "version_no"),
    )
    op.create_index(
        op.f("ix_working_paper_versions_working_paper_id"),
        "working_paper_versions",
        ["working_paper_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_working_paper_versions_working_paper_id"), table_name="working_paper_versions"
    )
    op.drop_table("working_paper_versions")
    op.drop_index(op.f("ix_working_papers_status"), table_name="working_papers")
    op.drop_index(op.f("ix_working_papers_fs_area"), table_name="working_papers")
    op.drop_index(op.f("ix_working_papers_engagement_id"), table_name="working_papers")
    op.drop_table("working_papers")
