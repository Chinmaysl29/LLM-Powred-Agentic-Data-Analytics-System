"""Add canonical dataset artifact registry fields.

Revision ID: 004_phase17_canonical_dataset_storage
Revises: 003_phase16_enterprise_audit_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "004_phase17_canonical_dataset_storage"
down_revision = "003_phase16_enterprise_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, column in (
        ("original_path", sa.Text()), ("json_path", sa.Text()), ("canonical_path", sa.Text()),
        ("metadata_path", sa.Text()), ("profile_path", sa.Text()), ("quality_path", sa.Text()),
        ("canonical_format", sa.String(length=32)), ("content_hash", sa.String(length=64)),
        ("size_bytes", sa.Integer()), ("row_count", sa.Integer()), ("column_count", sa.Integer()),
    ):
        op.add_column("datasets", sa.Column(name, column, nullable=True))
    op.create_index("ix_datasets_content_hash", "datasets", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_datasets_content_hash", table_name="datasets")
    for name in ("column_count", "row_count", "size_bytes", "content_hash", "canonical_format", "quality_path", "profile_path", "metadata_path", "canonical_path", "json_path", "original_path"):
        op.drop_column("datasets", name)
