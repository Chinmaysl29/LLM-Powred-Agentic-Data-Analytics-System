"""Add enterprise audit fields and indexes.

Revision ID: 003_phase16_enterprise_audit_fields
Revises: 002_phase16_audit_trail
"""

from alembic import op
import sqlalchemy as sa

revision = "003_phase16_enterprise_audit_fields"
down_revision = "002_phase16_audit_trail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_entries", sa.Column("event_id", sa.String(length=64), nullable=True))
    op.add_column("audit_entries", sa.Column("actor_type", sa.String(length=50), nullable=False, server_default="user"))
    op.add_column("audit_entries", sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("audit_entries", sa.Column("status", sa.String(length=32), nullable=False, server_default="success"))
    op.add_column("audit_entries", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_audit_entries_event_id", "audit_entries", ["event_id"], unique=True)
    op.create_index("ix_audit_entries_actor_type", "audit_entries", ["actor_type"])
    op.create_index("ix_audit_entries_status", "audit_entries", ["status"])


def downgrade() -> None:
    for index in ("ix_audit_entries_status", "ix_audit_entries_actor_type", "ix_audit_entries_event_id"):
        op.drop_index(index, table_name="audit_entries")
    for column in ("created_at", "status", "metadata", "actor_type", "event_id"):
        op.drop_column("audit_entries", column)
