from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from ai_impact_research.dashboard.data_loader import (
    DashboardData,
    load_dashboard_data,
    setup_instructions,
)


def configure_page(title: str) -> None:
    st.set_page_config(page_title=f"AI Impact Research | {title}", layout="wide")


def show_research_caveat() -> None:
    st.caption(
        "Research use only. Hypothetical backtests are not investment advice. "
        "Associations are not causal claims and require timing/data-quality review."
    )


def load_data_from_sidebar() -> DashboardData:
    st.sidebar.header("Data inputs")
    panel_path = st.sidebar.text_input("Analytic panel", "data/processed/analytic_panel.csv")
    analysis_dir = st.sidebar.text_input("Analysis outputs", "data/processed/analysis")
    st.sidebar.caption("Override paths for local experiments. No database or live API is required.")
    return _cached_load_dashboard_data(panel_path, analysis_dir)


@st.cache_data(show_spinner=False)
def _cached_load_dashboard_data(panel_path: str, analysis_dir: str) -> DashboardData:
    return load_dashboard_data(panel_path=panel_path, analysis_dir=analysis_dir)


def show_missing_data_message(data: DashboardData) -> None:
    if not data.missing_files:
        return
    st.info(setup_instructions())
    with st.expander("Missing dashboard inputs", expanded=False):
        st.write(", ".join(data.missing_files))
        st.write(f"Panel path: `{data.panel_path}`")
        st.write(f"Analysis directory: `{data.analysis_dir}`")


def stop_if_panel_missing(data: DashboardData) -> None:
    if data.panel.empty:
        show_missing_data_message(data)
        st.stop()


def metric_row(metrics: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Companies", metrics.get("company_count", 0))
    col2.metric("Quarters", metrics.get("quarter_count", 0))
    col3.metric("Sectors", metrics.get("sector_count", 0))
    col4.metric("Panel rows", metrics.get("row_count", 0))


def format_percent(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "n/a"
    return f"{numeric:.2%}"


def format_number(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "n/a"
    return f"{numeric:,.3f}"


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def read_markdown(path: str | Path) -> str:
    doc_path = Path(path)
    if not doc_path.exists():
        return ""
    return doc_path.read_text(encoding="utf-8")
