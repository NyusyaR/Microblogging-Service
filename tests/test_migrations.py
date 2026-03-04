import subprocess


def test_alembic_upgrade():
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_migrations_roundtrip():
    assert subprocess.run(["alembic", "upgrade", "head"]).returncode == 0
    assert subprocess.run(["alembic", "downgrade", "base"]).returncode == 0
    assert subprocess.run(["alembic", "upgrade", "head"]).returncode == 0
