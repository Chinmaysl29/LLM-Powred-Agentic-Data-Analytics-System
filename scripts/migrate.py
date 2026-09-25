"""Safe command-line entry point for Alembic migrations.

Examples:
    python scripts/migrate.py current
    python scripts/migrate.py upgrade head
    python scripts/migrate.py revision --message "add audit trail"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run database migrations using application settings.")
    parser.add_argument("command", choices=("current", "upgrade", "downgrade", "revision", "history"))
    parser.add_argument("target", nargs="?", default="head")
    parser.add_argument("--message", "-m", default="schema change")
    parser.add_argument("--autogenerate", action="store_true")
    args = parser.parse_args()
    config = _config()

    if args.command == "current":
        command.current(config)
    elif args.command == "upgrade":
        command.upgrade(config, args.target)
    elif args.command == "downgrade":
        command.downgrade(config, args.target)
    elif args.command == "history":
        command.history(config)
    else:
        command.revision(config, message=args.message, autogenerate=args.autogenerate)


if __name__ == "__main__":
    main()
