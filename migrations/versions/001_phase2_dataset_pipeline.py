"""Phase 2 dataset foundation, validation, metadata, profiling, quality, versioning, and recommendations

Revision ID: 001_phase2_dataset_pipeline
Revises: 
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_phase2_dataset_pipeline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. datasets
    op.create_table(
        'datasets',
        sa.Column('dataset_id', sa.String(length=36), primary_key=True),
        sa.Column('dataset_name', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_active_version_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 2. dataset_metadata
    op.create_table(
        'dataset_metadata',
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('datasets.dataset_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('column_count', sa.Integer(), nullable=False),
        sa.Column('column_names', sa.JSON(), nullable=False),
        sa.Column('column_types', sa.JSON(), nullable=False),
        sa.Column('columns_metadata', sa.JSON(), nullable=False),
        sa.Column('classifications', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 3. dataset_profiles
    op.create_table(
        'dataset_profiles',
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('datasets.dataset_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('duplicate_rows', sa.Integer(), nullable=False),
        sa.Column('duplicate_percentage', sa.Float(), nullable=False),
        sa.Column('missing_data_profile', sa.JSON(), nullable=False),
        sa.Column('cardinality_profile', sa.JSON(), nullable=False),
        sa.Column('numeric_columns_profile', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 4. dataset_quality
    op.create_table(
        'dataset_quality',
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('datasets.dataset_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('completeness_score', sa.Float(), nullable=False),
        sa.Column('uniqueness_score', sa.Float(), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=False),
        sa.Column('validity_score', sa.Float(), nullable=False),
        sa.Column('integrity_score', sa.Float(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('quality_classification', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index(
        'ix_dataset_quality_dataset_id_created_at',
        'dataset_quality',
        ['dataset_id', 'created_at'],
    )

    # 5. dataset_versions
    op.create_table(
        'dataset_versions',
        sa.Column('version_id', sa.String(length=36), primary_key=True),
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('datasets.dataset_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('parent_version_id', sa.String(length=36), sa.ForeignKey('dataset_versions.version_id', ondelete='RESTRICT'), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('transformation_metadata', sa.JSON(), nullable=True),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('metadata_snapshot', sa.JSON(), nullable=False),
        sa.Column('quality_snapshot', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('version_number >= 1', name='chk_version_number_positive'),
    )
    op.create_index(
        'uq_dataset_version_number',
        'dataset_versions',
        ['dataset_id', 'version_number'],
        unique=True,
    )
    op.create_index(
        'ix_dataset_versions_history',
        'dataset_versions',
        ['dataset_id', 'created_at'],
    )
    op.create_index(
        'ix_dataset_versions_parent',
        'dataset_versions',
        ['parent_version_id'],
    )

    # 6. cleaning_recommendations
    op.create_table(
        'cleaning_recommendations',
        sa.Column('recommendation_id', sa.String(length=36), primary_key=True),
        sa.Column('dataset_id', sa.String(length=36), sa.ForeignKey('datasets.dataset_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_id', sa.String(length=36), sa.ForeignKey('dataset_versions.version_id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('recommendation_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('priority_score', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('column_name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('suggested_action', sa.Text(), nullable=False),
        sa.Column('estimated_quality_gain', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('algorithm_metadata', sa.JSON(), nullable=True),
        sa.Column('prerequisites', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.CheckConstraint('priority_score >= 0 AND priority_score <= 100', name='chk_priority_score_range'),
    )
    op.create_index(
        'ix_recommendations_dataset_version',
        'cleaning_recommendations',
        ['dataset_id', 'version_id'],
    )
    op.create_index(
        'ix_recommendations_active',
        'cleaning_recommendations',
        ['dataset_id', 'status'],
    )
    op.create_index(
        'ix_recommendations_priority',
        'cleaning_recommendations',
        [sa.text('priority_score DESC')],
    )


def downgrade() -> None:
    op.drop_table('cleaning_recommendations')
    op.drop_table('dataset_versions')
    op.drop_table('dataset_quality')
    op.drop_table('dataset_profiles')
    op.drop_table('dataset_metadata')
    op.drop_table('datasets')
