from __future__ import annotations

import logging

from ai_impact_research.config import load_settings
from ai_impact_research.logging import configure_logging, get_logger


def _clear_config_env(monkeypatch) -> None:
    for name in [
        "PROJECT_ENV",
        "AI_IMPACT_CONFIG",
        "AI_IMPACT_SAMPLES_DIR",
        "AI_IMPACT_PROCESSED_DIR",
        "AI_IMPACT_REPORTS_DIR",
        "AI_IMPACT_DEFAULT_SIGNAL",
        "AI_IMPACT_DEFAULT_RETURN_COLUMN",
        "AI_IMPACT_LOG_LEVEL",
        "DATABASE_URL",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_load_settings_reads_yaml_defaults(tmp_path, monkeypatch) -> None:
    _clear_config_env(monkeypatch)
    config_path = tmp_path / "base.yaml"
    config_path.write_text(
        """
project:
  name: ai-impact-research
  default_universe: sample
  timezone: UTC
paths:
  samples_dir: data/samples
  processed_dir: data/processed
  reports_dir: reports
analysis:
  score_columns:
    - ai_adoption_score
    - ai_fluency_score
  outcome_columns:
    - fwd_return_1q
  default_signal: ai_adoption_score
  default_return_column: fwd_return_1q
llm:
  default_score_scale_min: 1
  default_score_scale_max: 5
  require_evidence: true
  max_quote_words: 35
""",
        encoding="utf-8",
    )

    settings = load_settings(project_root=tmp_path, config_path=config_path, env_file=None)

    assert settings.project_name == "ai-impact-research"
    assert settings.environment == "dev"
    assert settings.samples_dir == tmp_path / "data" / "samples"
    assert settings.processed_dir == tmp_path / "data" / "processed"
    assert settings.analysis.default_signal == "ai_adoption_score"
    assert settings.llm.require_evidence is True


def test_load_settings_applies_dotenv_overrides(tmp_path, monkeypatch) -> None:
    _clear_config_env(monkeypatch)
    config_path = tmp_path / "base.yaml"
    config_path.write_text(
        """
project:
  name: ai-impact-research
  default_universe: sample
  timezone: UTC
paths:
  samples_dir: data/samples
  processed_dir: data/processed
  reports_dir: reports
analysis:
  score_columns:
    - ai_adoption_score
  outcome_columns:
    - fwd_return_1q
  default_signal: ai_adoption_score
  default_return_column: fwd_return_1q
llm:
  default_score_scale_min: 1
  default_score_scale_max: 5
  require_evidence: true
  max_quote_words: 35
""",
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PROJECT_ENV=test",
                "DATABASE_URL=sqlite:///local.db",
                "AI_IMPACT_PROCESSED_DIR=custom/processed",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(project_root=tmp_path, config_path=config_path, env_file=env_file)

    assert settings.environment == "test"
    assert settings.database_url == "sqlite:///local.db"
    assert settings.processed_dir == tmp_path / "custom" / "processed"


def test_logging_helper_configures_named_logger() -> None:
    configure_logging("DEBUG")
    logger = get_logger("ai_impact_research.tests")

    assert logger.name == "ai_impact_research.tests"
    assert logging.getLogger().level == logging.DEBUG
