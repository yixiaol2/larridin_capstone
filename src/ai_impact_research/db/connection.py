from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_impact_research.config import load_settings


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    schema_path: Path


def require_database_url(database_url: str | None) -> str:
    if not database_url:
        raise ValueError("DATABASE_URL is not set. Copy .env.example to .env and configure it.")
    return database_url


def load_database_config(database_url: str | None = None, schema_path: str | Path | None = None) -> DatabaseConfig:
    settings = load_settings()
    selected_url = require_database_url(database_url or settings.database_url)
    selected_schema_path = Path(schema_path) if schema_path is not None else settings.project_root / "infra" / "db_schema.sql"
    return DatabaseConfig(url=selected_url, schema_path=selected_schema_path)


def read_schema_sql(schema_path: str | Path | None = None) -> str:
    settings = load_settings()
    selected_schema_path = Path(schema_path) if schema_path is not None else settings.project_root / "infra" / "db_schema.sql"
    if not selected_schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {selected_schema_path}")
    return selected_schema_path.read_text(encoding="utf-8")
