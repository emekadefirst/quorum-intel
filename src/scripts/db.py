"""Thin wrappers around aerich commands, exposed as uv scripts.

Extra CLI args are forwarded, so you can do:
    uv run db-migrate --name add_trades_table
    uv run db-upgrade --in-transaction false
"""

import subprocess
import sys


def _run(cmd: str) -> None:
    extra = sys.argv[1:]
    subprocess.run([sys.executable, "-m", "aerich", cmd, *extra], check=True)


def init() -> None:
    """aerich init -t src.core.database.TORTOISE_ORM [extra args]"""
    extra = sys.argv[1:] or ["-t", "src.core.database.TORTOISE_ORM"]
    subprocess.run([sys.executable, "-m", "aerich", "init", *extra], check=True)


def init_db() -> None:
    """aerich init-db [extra args]"""
    _run("init-db")


def migrate() -> None:
    """aerich migrate [--name <name>]"""
    _run("migrate")


def upgrade() -> None:
    """aerich upgrade [extra args]"""
    _run("upgrade")


def downgrade() -> None:
    """aerich downgrade [extra args]"""
    _run("downgrade")


def history() -> None:
    """aerich history"""
    _run("history")


def heads() -> None:
    """aerich heads"""
    _run("heads")
