from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


@dataclass(frozen=True)
class AnalysisConfig:
    score_columns: list[str]
    outcome_columns: list[str]
    default_signal: str
    default_return_column: str


@dataclass(frozen=True)
class LLMConfig:
    default_score_scale_min: int
    default_score_scale_max: int
    require_evidence: bool
    max_quote_words: int


@dataclass(frozen=True)
class Settings:
    project_root: Path
    config_path: Path
    environment: str
    project_name: str
    default_universe: str
    timezone: str
    samples_dir: Path
    processed_dir: Path
    reports_dir: Path
    analysis: AnalysisConfig
    llm: LLMConfig
    database_url: str | None
    larridin_api_base_url: str | None
    larridin_api_key: str | None
    sec_user_agent: str | None
    object_storage_bucket: str | None
    log_level: str


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return data


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section must be a mapping: {name}")
    return value


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def load_settings(
    project_root: str | Path | None = None,
    config_path: str | Path | None = None,
    env_file: str | Path | None = ".env",
) -> Settings:
    root = Path(project_root).resolve() if project_root is not None else _find_project_root()
    dotenv_path = _resolve_path(root, env_file) if env_file is not None else None
    if dotenv_path is not None and dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)

    selected_config = Path(os.getenv("AI_IMPACT_CONFIG", config_path or root / "configs" / "base.yaml"))
    if not selected_config.is_absolute():
        selected_config = root / selected_config
    config = _load_yaml(selected_config)
    project = _section(config, "project")
    paths = _section(config, "paths")
    analysis = _section(config, "analysis")
    llm = _section(config, "llm")
    logging_config = _section(config, "logging")

    samples_dir = os.getenv("AI_IMPACT_SAMPLES_DIR", paths.get("samples_dir", "data/samples"))
    processed_dir = os.getenv("AI_IMPACT_PROCESSED_DIR", paths.get("processed_dir", "data/processed"))
    reports_dir = os.getenv("AI_IMPACT_REPORTS_DIR", paths.get("reports_dir", "reports"))

    return Settings(
        project_root=root,
        config_path=selected_config,
        environment=os.getenv("PROJECT_ENV", "dev"),
        project_name=str(project.get("name", "ai-impact-research")),
        default_universe=str(project.get("default_universe", "sample")),
        timezone=str(project.get("timezone", "UTC")),
        samples_dir=_resolve_path(root, samples_dir),
        processed_dir=_resolve_path(root, processed_dir),
        reports_dir=_resolve_path(root, reports_dir),
        analysis=AnalysisConfig(
            score_columns=list(analysis.get("score_columns", [])),
            outcome_columns=list(analysis.get("outcome_columns", [])),
            default_signal=os.getenv(
                "AI_IMPACT_DEFAULT_SIGNAL", str(analysis.get("default_signal", "ai_adoption_score"))
            ),
            default_return_column=os.getenv(
                "AI_IMPACT_DEFAULT_RETURN_COLUMN",
                str(analysis.get("default_return_column", "fwd_return_1q")),
            ),
        ),
        llm=LLMConfig(
            default_score_scale_min=int(llm.get("default_score_scale_min", 1)),
            default_score_scale_max=int(llm.get("default_score_scale_max", 5)),
            require_evidence=bool(llm.get("require_evidence", True)),
            max_quote_words=int(llm.get("max_quote_words", 35)),
        ),
        database_url=_optional_env("DATABASE_URL"),
        larridin_api_base_url=_optional_env("LARRIDIN_API_BASE_URL"),
        larridin_api_key=_optional_env("LARRIDIN_API_KEY"),
        sec_user_agent=_optional_env("SEC_USER_AGENT"),
        object_storage_bucket=_optional_env("OBJECT_STORAGE_BUCKET"),
        log_level=os.getenv("AI_IMPACT_LOG_LEVEL", str(logging_config.get("level", "INFO"))),
    )
