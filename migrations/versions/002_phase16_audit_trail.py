"""Add persistent Phase 16 audit trail.

Revision ID: 002_phase16_audit_trail
Revises: 001_phase2_dataset_pipeline
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_phase16_audit_trail"
down_revision = "001_phase2_dataset_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    for column in ("actor", "action", "resource_type", "resource_id", "occurred_at", "request_id"):
        op.create_index(f"ix_audit_entries_{column}", "audit_entries", [column])


def downgrade() -> None:
    op.drop_table("audit_entries")
