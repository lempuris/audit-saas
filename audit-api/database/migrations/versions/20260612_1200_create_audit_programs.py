"""create procedure_templates, engagement_procedures, risk_procedure_links

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-12 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procedure_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("fs_area", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("isa_reference", sa.String(), nullable=True),
        sa.Column("assertions", JSONB(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("fs_area", "title"),
    )
    op.create_index(op.f("ix_procedure_templates_fs_area"), "procedure_templates", ["fs_area"])

    op.create_table(
        "engagement_procedures",
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
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("procedure_templates.id"),
            nullable=True,
        ),
        sa.Column("fs_area", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("isa_reference", sa.String(), nullable=True),
        sa.Column("assertions", JSONB(), nullable=False),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
    )
    op.create_index(
        op.f("ix_engagement_procedures_engagement_id"), "engagement_procedures", ["engagement_id"]
    )
    op.create_index(op.f("ix_engagement_procedures_fs_area"), "engagement_procedures", ["fs_area"])
    op.create_index(
        op.f("ix_engagement_procedures_assigned_to"), "engagement_procedures", ["assigned_to"]
    )
    op.create_index(op.f("ix_engagement_procedures_status"), "engagement_procedures", ["status"])

    op.create_table(
        "risk_procedure_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "risk_id",
            UUID(as_uuid=True),
            sa.ForeignKey("risks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "procedure_id",
            UUID(as_uuid=True),
            sa.ForeignKey("engagement_procedures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("risk_id", "procedure_id"),
    )
    op.create_index(op.f("ix_risk_procedure_links_risk_id"), "risk_procedure_links", ["risk_id"])
    op.create_index(
        op.f("ix_risk_procedure_links_procedure_id"), "risk_procedure_links", ["procedure_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_procedure_links_procedure_id"), table_name="risk_procedure_links")
    op.drop_index(op.f("ix_risk_procedure_links_risk_id"), table_name="risk_procedure_links")
    op.drop_table("risk_procedure_links")
    op.drop_index(op.f("ix_engagement_procedures_status"), table_name="engagement_procedures")
    op.drop_index(op.f("ix_engagement_procedures_assigned_to"), table_name="engagement_procedures")
    op.drop_index(op.f("ix_engagement_procedures_fs_area"), table_name="engagement_procedures")
    op.drop_index(
        op.f("ix_engagement_procedures_engagement_id"), table_name="engagement_procedures"
    )
    op.drop_table("engagement_procedures")
    op.drop_index(op.f("ix_procedure_templates_fs_area"), table_name="procedure_templates")
    op.drop_table("procedure_templates")
