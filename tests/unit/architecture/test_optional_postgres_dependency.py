from __future__ import annotations

from pathlib import Path
import tomllib


def test_psycopg_is_only_in_postgres_extra() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert not any(item.startswith("psycopg") for item in data["project"]["dependencies"])
    postgres = data["project"]["optional-dependencies"]["postgres"]
    assert postgres == ["psycopg[binary]>=3.2,<4"]
