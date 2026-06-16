from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_impact_research.dashboard.components import (
    configure_page,
    load_data_from_sidebar,
    metric_row,
    show_missing_data_message,
    show_research_caveat,
)
from ai_impact_research.dashboard.data_loader import available_signals, summarize_panel

configure_page("Overview")

st.title("Overview")
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
    st.warning("Sector coverage is unavailable.")
else:
    col1, col2 = st.columns([1, 2])
    col1.dataframe(coverage, use_container_width=True, hide_index=True)
    col2.plotly_chart(
        px.bar(coverage, x="sector", y="company_count", title="Company Coverage by Sector"),
        use_container_width=True,
    )

st.subheader("Score Distributions")
signals = available_signals(panel)
if signals:
    signal = st.selectbox("Signal", signals)
    st.plotly_chart(
        px.histogram(panel, x=signal, color="sector" if "sector" in panel.columns else None, nbins=5),
        use_container_width=True,
    )
else:
    st.info("No AI score columns were found.")

st.subheader("Missingness Summary")
missingness = pd.DataFrame(
    [{"column": col, "missing_rows": count} for col, count in summary["missingness"].items()]
)
if missingness.empty:
    st.info("No expected dashboard columns were found for missingness reporting.")
else:
    st.dataframe(
        missingness.sort_values("missing_rows", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
