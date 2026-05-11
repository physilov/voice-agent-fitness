"""add onboarding_complete to users

Revision ID: 002
Revises: 001
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "002_onboarding"
down_revision = "001_equipment_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_complete", sa.Boolean(), nullable=True, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_complete")
