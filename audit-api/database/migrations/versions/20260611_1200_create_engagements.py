"""create engagements and engagement_team_members

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-11 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("engagement_type", sa.String(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_index(op.f("ix_engagements_client_id"), "engagements", ["client_id"])
    op.create_index(op.f("ix_engagements_status"), "engagements", ["status"])

    op.create_table(
        "engagement_team_members",
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
        ),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("role_on_engagement", sa.String(), nullable=True),
        sa.Column("independence_confirmed", sa.Boolean(), nullable=False),
        sa.Column("independence_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("engagement_id", "clerk_user_id"),
    )
    op.create_index(
        op.f("ix_engagement_team_members_engagement_id"),
        "engagement_team_members",
        ["engagement_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_engagement_team_members_engagement_id"), table_name="engagement_team_members"
    )
    op.drop_table("engagement_team_members")
    op.drop_index(op.f("ix_engagements_status"), table_name="engagements")
    op.drop_index(op.f("ix_engagements_client_id"), table_name="engagements")
    op.drop_table("engagements")
