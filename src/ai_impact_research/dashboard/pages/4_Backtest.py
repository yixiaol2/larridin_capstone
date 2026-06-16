from __future__ import annotations

import plotly.express as px
import streamlit as st

from ai_impact_research.dashboard.components import (
    configure_page,
    format_number,
    format_percent,
    load_data_from_sidebar,
    show_research_caveat,
    stop_if_panel_missing,
)
from ai_impact_research.dashboard.data_loader import available_signals

configure_page("Backtest")

st.title("Backtest")
show_research_caveat()
st.warning("Hypothetical research backtest only. This is not investment advice.")

data = load_data_from_sidebar()
stop_if_panel_missing(data)
panel = data.panel

signals = available_signals(panel)
if not signals:
    st.warning("Backtest exploration needs at least one AI signal in the panel.")
    st.stop()

signal = st.selectbox("Signal", signals, index=signals.index("composite_ai_score") if "composite_ai_score" in signals else 0)

metrics = data.backtest_metrics
metric_row = (
    metrics.loc[metrics["signal"] == signal].iloc[0]
    if not metrics.empty and "signal" in metrics.columns and signal in set(metrics["signal"])
    else metrics.iloc[0] if not metrics.empty else None
)
if metric_row is None:
    st.info("No saved backtest metrics are available. Run `python scripts/run_baseline_analysis.py`.")
else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sharpe ratio", format_number(metric_row.get("sharpe_ratio")))
    col2.metric("Max drawdown", format_percent(metric_row.get("max_drawdown")))
    col3.metric("Cumulative return", format_percent(metric_row.get("cumulative_return")))
    col4.metric("Rebalances", format_number(metric_row.get("number_of_rebalances")))

st.subheader("Quintile Returns")
quintiles = data.backtest_quintile_returns
if quintiles.empty:
    st.info("No quintile return table is available.")
else:
    st.dataframe(quintiles, use_container_width=True, hide_index=True)
    if {"quarter", "signal_quantile", "mean_return"}.issubset(quintiles.columns):
        st.plotly_chart(
            px.line(
                quintiles,
                x="quarter",
                y="mean_return",
                color="signal_quantile",
                markers=True,
                title="Equal-Weight Forward Returns by Quintile",
            ),
            use_container_width=True,
        )

st.subheader("Cumulative Long-Short Return")
long_short = data.backtest_long_short_returns
if long_short.empty:
    st.info("No long-short return series is available.")
else:
    y_col = "cumulative_return" if "cumulative_return" in long_short.columns else "cumulative_long_short"
    st.plotly_chart(
        px.line(long_short, x="quarter", y=y_col, markers=True, title="Q5 minus Q1 Cumulative Return"),
        use_container_width=True,
    )
    st.dataframe(long_short, use_container_width=True, hide_index=True)
