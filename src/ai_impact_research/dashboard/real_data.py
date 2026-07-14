"""Data access layer for the real-data dashboard.

Loads the processed real datasets (analysis table, regression results, hiring
snapshots) with Streamlit caching. Kept separate from the legacy
``data_loader`` module, which serves the original synthetic-sample pages and
their tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path("data/processed")

SIGNALS = {
    "maturity_index": "Larridin maturity index",
    "adoption_score": "Larridin adoption",
    "conc": "Narrative concreteness (ours)",
    "inv": "Investment intensity (ours)",
    "builder_rate": "AI-hiring builder rate (ours)",
}
OUTCOMES = {
    "rev_growth_yoy": "Revenue growth YoY (Q1-2026)",
    "op_margin_delta_yoy": "Operating-margin change YoY",
    "fwd_ret_4m": "Forward return (4 months)",
}


@st.cache_data(show_spinner=False)
def load_table() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "analysis_table_v4.parquet")
    cx = pd.read_parquet(ROOT / "analysis_crosssection.parquet")[
        ["ticker", "name", "gics_sector", "cik"]
    ]
    return df.merge(cx, on="ticker", how="left")


@st.cache_data(show_spinner=False)
def load_regressions() -> pd.DataFrame:
    return pd.read_csv(ROOT / "analysis" / "controls_regressions.csv")


@st.cache_data(show_spinner=False)
def load_hiring(snapshot: str) -> pd.DataFrame:
    return pd.read_parquet(ROOT / f"hiring/{snapshot}/company_hiring_signal.parquet")


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, label in {**SIGNALS, **OUTCOMES}.items():
        if col in df.columns:
            rows.append({"Variable": label, "Companies": int(df[col].notna().sum())})
    return pd.DataFrame(rows)
