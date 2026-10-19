import subprocess
import sys


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "aerich", *args], check=True)


def init() -> None:
    """Initialize aerich: aerich init -t src.core.database.TORTOISE_ORM"""
    _run(["init", "-t", "src.core.database.TORTOISE_ORM"])


def init_db() -> None:
    """Create initial database schema: aerich init-db"""
    _run(["init-db"])


def migrate() -> None:
    """Create migration from model changes: aerich migrate"""
    _run(["migrate"])


def upgrade() -> None:
    """Apply migrations: aerich upgrade"""
    _run(["upgrade"])


def downgrade() -> None:
    """Rollback last migration: aerich downgrade"""
    _run(["downgrade"])


def history() -> None:
    """Show migration history: aerich history"""
    _run(["history"])


def heads() -> None:
    """Show migration heads: aerich heads"""
    _run(["heads"])
