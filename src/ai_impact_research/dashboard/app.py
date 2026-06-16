from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[2]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.data_loader import available_signals, summarize_panel
from ai_impact_research.dashboard.components import (
    configure_page,
    load_data_from_sidebar,
    metric_row,
    show_missing_data_message,
    show_research_caveat,
)

configure_page("Overview")

st.title("AI Impact Research Dashboard")
show_research_caveat()

data = load_data_from_sidebar()
show_missing_data_message(data)

if data.panel.empty:
    st.stop()

panel = data.panel
summary = summarize_panel(panel)
metric_row(summary)

st.subheader("Sector Coverage")
coverage = summary["sector_coverage"]
if coverage.empty:
    st.warning("Sector coverage is unavailable because the panel has no sector column.")
else:
    left, right = st.columns([1, 2])
    left.dataframe(coverage, use_container_width=True, hide_index=True)
    right.plotly_chart(
        px.bar(coverage, x="sector", y="company_count", title="Companies by Sector"),
        use_container_width=True,
    )

st.subheader("Score Distributions")
signals = available_signals(panel)
if not signals:
    st.warning("No AI signal columns were found in the panel.")
else:
    selected_signal = st.selectbox("Signal", signals)
    st.plotly_chart(
        px.histogram(panel, x=selected_signal, nbins=5, title=f"Distribution of {selected_signal}"),
        use_container_width=True,
    )

st.subheader("Missingness Summary")
missingness = summary["missingness"]
if missingness:
    missing_df = (
        pd.DataFrame(
            [{"column": column, "missing_rows": count} for column, count in missingness.items()]
        )
        .sort_values("missing_rows", ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(missing_df, use_container_width=True, hide_index=True)
else:
    st.info("No expected dashboard columns were found for missingness reporting.")
