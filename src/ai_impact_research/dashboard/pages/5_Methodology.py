from __future__ import annotations

import streamlit as st

from ai_impact_research.dashboard.components import (
    configure_page,
    read_markdown,
    show_research_caveat,
)

configure_page("Methodology")

st.title("Methodology")
show_research_caveat()

st.header("Data Sources")
st.markdown(
    """
The dashboard reads local processed files from `data/processed` by default. It does not use live APIs,
databases, credentials, or private data during the MVP workflow.

Primary dashboard inputs:

- `data/processed/analytic_panel.csv`
- `data/processed/analysis/ic_summary.csv`
- `data/processed/analysis/ic_by_quarter.csv`
- `data/processed/analysis/regression_results.csv`
- `data/processed/analysis/backtest_metrics.csv`
- `data/processed/analysis/backtest_quintile_returns.csv`
- `data/processed/analysis/backtest_long_short_returns.csv`
"""
)

st.header("Feature Timing")
st.markdown(
    """
Every model feature should have an observation date or `available_at` timestamp. Larridin scores use
`snapshot_date` and `score_available_at`; fundamentals use `available_at`; market outcomes begin after
the prediction date. Rows with ambiguous timing should be flagged and excluded in strict analysis mode.
"""
)

st.header("Look-Ahead Bias Controls")
st.markdown(
    """
- Features may only use data available on or before `prediction_date`.
- Forward return windows begin after `prediction_date`.
- Fundamentals must not be used before their `available_at` timestamp.
- Backtests are cross-sectional research exercises and should be audited before interpretation.
"""
)

st.header("Limitations")
st.markdown(
    """
- Synthetic sample data is for reproducibility checks only and does not represent real company results.
- Small samples can make IC, regression, and quintile statistics unstable.
- Associations shown in charts are not causal evidence.
- Hypothetical backtests are not investment advice.
- Disclosure-heavy companies may appear more AI mature than quieter adopters.
"""
)

st.header("Responsible AI Caveats")
st.markdown(
    """
LLM-derived fields must preserve source evidence, prompt version, model name, source document ID, schema
version, confidence, and extraction timestamp. Unsupported dimensions should remain null rather than being
filled with invented scores.
"""
)

with st.expander("Project documentation excerpts", expanded=False):
    for path in [
        "docs/03_DATA_SOURCES.md",
        "docs/05_BACKTESTING_METHODOLOGY.md",
        "docs/08_LLM_SIGNAL_RUBRIC.md",
        "docs/07_RESPONSIBLE_AI_AND_RISKS.md",
    ]:
        text = read_markdown(path)
        if text:
            st.subheader(path)
            st.markdown(text)
