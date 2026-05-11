"""Add equipment context columns to users table."""
from alembic import op
import sqlalchemy as sa

revision = "001_equipment_context"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("default_equipment", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("equipment_context_note", sa.String(), nullable=True))
    op.add_column("users", sa.Column("equipment_context_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "equipment_context_expires_at")
    op.drop_column("users", "equipment_context_note")
    op.drop_column("users", "default_equipment")
