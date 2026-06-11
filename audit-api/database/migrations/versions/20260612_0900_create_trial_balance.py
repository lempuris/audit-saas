"""create trial_balances and trial_balance_lines

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-12 09:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trial_balances",
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
        sa.Column("source_filename", sa.String(), nullable=False),
        sa.Column("imported_by", sa.String(), nullable=False),
    )
    op.create_index(op.f("ix_trial_balances_engagement_id"), "trial_balances", ["engagement_id"])

    op.create_table(
        "trial_balance_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "trial_balance_id",
            UUID(as_uuid=True),
            sa.ForeignKey("trial_balances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("account_code", sa.String(), nullable=False),
        sa.Column("account_name", sa.String(), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("prior_year_balance", sa.Numeric(18, 2), nullable=True),
        sa.Column("fs_area", sa.String(), nullable=True),
        sa.UniqueConstraint("trial_balance_id", "account_code"),
    )
    op.create_index(
        op.f("ix_trial_balance_lines_trial_balance_id"),
        "trial_balance_lines",
        ["trial_balance_id"],
    )
    op.create_index(op.f("ix_trial_balance_lines_fs_area"), "trial_balance_lines", ["fs_area"])


def downgrade() -> None:
    op.drop_index(op.f("ix_trial_balance_lines_fs_area"), table_name="trial_balance_lines")
    op.drop_index(op.f("ix_trial_balance_lines_trial_balance_id"), table_name="trial_balance_lines")
    op.drop_table("trial_balance_lines")
    op.drop_index(op.f("ix_trial_balances_engagement_id"), table_name="trial_balances")
    op.drop_table("trial_balances")
