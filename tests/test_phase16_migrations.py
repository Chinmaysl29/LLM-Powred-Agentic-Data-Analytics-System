"""Phase 16.1 migration configuration and SQL generation validation."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app.models.base import Base
import backend.app.models  # noqa: F401 - registers all application models


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def migration_config() -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"), output_buffer=StringIO())
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


def test_migration_history_has_a_single_valid_head():
    scripts = ScriptDirectory.from_config(migration_config())
    heads = scripts.get_heads()
    assert heads == ["002_phase16_audit_trail"]


def test_upgrade_and_downgrade_generate_schema_sql_without_a_live_database():
    upgrade_config = migration_config()
    command.upgrade(upgrade_config, "head", sql=True)
    upgrade_sql = upgrade_config.output_buffer.getvalue().lower()
    assert "create table datasets" in upgrade_sql
    assert "create table audit_entries" in upgrade_sql
    assert "alembic_version" in upgrade_sql

    downgrade_config = migration_config()
    command.downgrade(downgrade_config, "002_phase16_audit_trail:base", sql=True)
    downgrade_sql = downgrade_config.output_buffer.getvalue().lower()
    assert "drop table cleaning_recommendations" in downgrade_sql
    assert "drop table audit_entries" in downgrade_sql
    assert "delete from alembic_version" in downgrade_sql


def test_model_metadata_is_available_to_alembic_autogenerate():
    assert "users" in Base.metadata.tables
    assert "datasets" in Base.metadata.tables
    assert "forecast_runs" in Base.metadata.tables
