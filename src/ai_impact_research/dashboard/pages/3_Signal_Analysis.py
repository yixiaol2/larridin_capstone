from __future__ import annotations

import plotly.express as px
import streamlit as st

from ai_impact_research.dashboard.components import (
    configure_page,
    load_data_from_sidebar,
    show_research_caveat,
    stop_if_panel_missing,
)
from ai_impact_research.dashboard.data_loader import available_outcomes, available_signals

configure_page("Signal Analysis")

st.title("Signal Analysis")
show_research_caveat()

data = load_data_from_sidebar()
stop_if_panel_missing(data)
panel = data.panel

signals = available_signals(panel)
outcomes = available_outcomes(panel)
if not signals or not outcomes:
    st.warning("Signal analysis needs at least one AI signal and one outcome column in the panel.")
    st.stop()

col1, col2 = st.columns(2)
signal = col1.selectbox("Signal", signals)
outcome = col2.selectbox("Outcome", outcomes)

plot_df = panel.dropna(subset=[signal, outcome]).copy()
if plot_df.empty:
    st.warning("No rows have both the selected signal and outcome.")
else:
    st.plotly_chart(
        px.scatter(
            plot_df,
            x=signal,
            y=outcome,
            color="sector" if "sector" in plot_df.columns else None,
            hover_data=[col for col in ["ticker", "company_id", "score_quarter"] if col in plot_df.columns],
            trendline="ols" if len(plot_df) >= 3 else None,
            title=f"{signal} vs {outcome}",
        ),
        use_container_width=True,
    )

st.subheader("IC Summary")
ic_summary = data.ic_summary
filtered_summary = (
    ic_summary.loc[(ic_summary["signal"] == signal) & (ic_summary["outcome"] == outcome)]
    if not ic_summary.empty and {"signal", "outcome"}.issubset(ic_summary.columns)
    else ic_summary.iloc[0:0]
)
if filtered_summary.empty:
    st.info("No IC summary is available for this signal/outcome pair.")
else:
    st.dataframe(filtered_summary, use_container_width=True, hide_index=True)

st.subheader("IC by Quarter")
ic_by_quarter = data.ic_by_quarter
filtered_ic = (
    ic_by_quarter.loc[(ic_by_quarter["signal"] == signal) & (ic_by_quarter["outcome"] == outcome)]
    if not ic_by_quarter.empty and {"signal", "outcome", "quarter", "ic"}.issubset(ic_by_quarter.columns)
    else ic_by_quarter.iloc[0:0]
)
if filtered_ic.empty:
    st.info("No quarterly IC output is available for this signal/outcome pair.")
else:
    st.plotly_chart(
        px.line(filtered_ic, x="quarter", y="ic", markers=True, title="Spearman IC by Quarter"),
        use_container_width=True,
    )
    st.dataframe(filtered_ic, use_container_width=True, hide_index=True)

st.subheader("Regression Results")
regressions = data.regression_results
filtered_regressions = (
    regressions.loc[(regressions["signal"] == signal) & (regressions["outcome"] == outcome)]
    if not regressions.empty and {"signal", "outcome"}.issubset(regressions.columns)
    else regressions.iloc[0:0]
)
if filtered_regressions.empty:
    st.info("No regression results are available for this signal/outcome pair.")
else:
    st.dataframe(filtered_regressions, use_container_width=True, hide_index=True)
