from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd
import pytest

from ai_impact_research.ingestion.larridin import (
    LarridinAPIClient,
    load_larridin_scores_csv,
    normalize_larridin_scores,
)


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["msft"],
            "company_id": ["C001"],
            "company_name": ["Microsoft Corporation"],
            "snapshot_date": ["2025-03-31"],
            "available_at": ["2025-04-02"],
            "ai_adoption_score": [5],
            "ai_fluency_score": [5],
            "ai_impact_score": [5],
            "ai_hiring_score": [4],
            "source_name": ["synthetic_larridin_sample"],
            "source_reference": ["synthetic://larridin/msft/2025q1"],
            "unused_raw_field": ["preserve-me"],
        }
    )


def test_valid_csv_passes_and_preserves_metadata(tmp_path) -> None:
    input_path = tmp_path / "scores.csv"
    _valid_df().to_csv(input_path, index=False)

    out = load_larridin_scores_csv(input_path)
    metadata = json.loads(out.loc[0, "metadata_json"])

    assert out.loc[0, "ticker"] == "MSFT"
    assert out.loc[0, "score_quarter"] == "2025Q1"
    assert out.loc[0, "source_url"] == "synthetic://larridin/msft/2025q1"
    assert metadata["unused_raw_field"] == "preserve-me"


def test_metadata_json_is_empty_object_when_no_extra_columns() -> None:
    df = _valid_df().drop(columns=["unused_raw_field", "source_reference"])

    out = normalize_larridin_scores(df)

    assert out.loc[0, "metadata_json"] == "{}"


def test_missing_required_column_fails() -> None:
    df = _valid_df().drop(columns=["snapshot_date"])

    with pytest.raises(ValueError, match="missing required columns"):
        normalize_larridin_scores(df)


def test_score_outside_range_fails() -> None:
    df = _valid_df()
    df.loc[0, "ai_hiring_score"] = 6

    with pytest.raises(ValueError, match="Invalid 1-5 score values"):
        normalize_larridin_scores(df)


def test_non_integer_score_fails() -> None:
    df = _valid_df()
    df["ai_adoption_score"] = [3.5]

    with pytest.raises(ValueError, match="whole numbers"):
        normalize_larridin_scores(df)


def test_missing_available_at_without_override_fails() -> None:
    df = _valid_df().drop(columns=["available_at"])

    with pytest.raises(ValueError, match="available_at"):
        normalize_larridin_scores(df)


def test_missing_available_at_with_override_passes() -> None:
    df = _valid_df().drop(columns=["available_at"])

    out = normalize_larridin_scores(df, available_at_override="2025-04-05")

    assert out.loc[0, "available_at"] == pd.Timestamp("2025-04-05")
    assert bool(out.loc[0, "available_at_assumption"]) is True


def test_ticker_normalization_works() -> None:
    df = _valid_df()
    df.loc[0, "ticker"] = " msft "

    out = normalize_larridin_scores(df)

    assert out.loc[0, "ticker"] == "MSFT"


def test_cli_writes_normalized_csv_and_prints_summary(tmp_path) -> None:
    input_path = tmp_path / "scores.csv"
    output_path = tmp_path / "larridin_scores_normalized.csv"
    _valid_df().to_csv(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_larridin.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    out = pd.read_csv(output_path)

    assert "rows: 1" in result.stdout
    assert "tickers: 1" in result.stdout
    assert out.loc[0, "ticker"] == "MSFT"


def test_api_client_stub_does_not_call_network() -> None:
    with pytest.raises(NotImplementedError, match="TODO"):
        LarridinAPIClient().fetch_scores()
