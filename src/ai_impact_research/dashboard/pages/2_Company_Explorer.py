from __future__ import annotations

import plotly.express as px
import streamlit as st

from ai_impact_research.dashboard.components import (
    configure_page,
    first_existing,
    format_number,
    load_data_from_sidebar,
    show_research_caveat,
    stop_if_panel_missing,
)
from ai_impact_research.dashboard.data_loader import SIGNAL_COLUMNS

configure_page("Company Explorer")

st.title("Company Explorer")
show_research_caveat()

data = load_data_from_sidebar()
stop_if_panel_missing(data)
panel = data.panel

ticker_col = first_existing(list(panel.columns), ["ticker", "company_id"])
if ticker_col is None:
    st.warning("The panel does not include ticker or company_id.")
    st.stop()

ticker = st.selectbox("Ticker", sorted(panel[ticker_col].dropna().unique()))
company_panel = panel.loc[panel[ticker_col] == ticker].copy()
quarter_col = first_existing(list(panel.columns), ["score_quarter", "quarter", "snapshot_date"])
if quarter_col:
    company_panel = company_panel.sort_values(quarter_col)

latest = company_panel.iloc[-1]
company_name = latest.get("company_name", ticker)
st.subheader(str(company_name))

score_cols = [col for col in SIGNAL_COLUMNS if col in company_panel.columns]
if score_cols:
    cols = st.columns(len(score_cols))
    for col, score_col in zip(cols, score_cols, strict=False):
        col.metric(score_col.replace("_", " "), format_number(latest.get(score_col)))
else:
    st.info("No AI score columns are available for this company.")

st.subheader("Score History")
if quarter_col and score_cols:
    long_scores = company_panel[[quarter_col, *score_cols]].melt(
        id_vars=quarter_col,
        value_vars=score_cols,
        var_name="signal",
        value_name="score",
    )
    st.plotly_chart(
        px.line(long_scores, x=quarter_col, y="score", color="signal", markers=True),
        use_container_width=True,
    )
else:
    st.info("Score history needs quarter and signal columns.")

st.subheader("Financial Outcome History")
outcome_cols = [
    col
    for col in [
        "fwd_return_1q",
        "fwd_return_2q",
        "future_revenue_growth_qoq",
        "future_operating_margin_delta_qoq",
        "future_revenue_per_employee_growth_qoq",
    ]
    if col in company_panel.columns
]
if quarter_col and outcome_cols:
    long_outcomes = company_panel[[quarter_col, *outcome_cols]].melt(
        id_vars=quarter_col,
        value_vars=outcome_cols,
        var_name="outcome",
        value_name="value",
    )
    st.plotly_chart(
        px.line(long_outcomes, x=quarter_col, y="value", color="outcome", markers=True),
        use_container_width=True,
    )
else:
    st.info("Financial outcome history is unavailable for this company.")

st.subheader("Sector Peer Rank")
rank_signal = st.selectbox("Rank signal", score_cols) if score_cols else None
if rank_signal and "sector" in panel.columns:
    sector = latest.get("sector")
    peers = panel.loc[panel["sector"] == sector].copy()
    if quarter_col:
        peers = peers.loc[peers[quarter_col] == latest.get(quarter_col)]
    peers = peers.dropna(subset=[rank_signal])
    if peers.empty:
        st.info("Peer rank is unavailable because peer signal data is missing.")
    else:
        peers["sector_rank"] = peers[rank_signal].rank(ascending=False, method="min")
        rank_row = peers.loc[peers[ticker_col] == ticker]
        if rank_row.empty:
            st.info("Selected company is missing from the peer rank universe.")
        else:
            rank = int(rank_row["sector_rank"].iloc[0])
            st.metric("Sector rank", f"{rank} of {len(peers)}")
            st.dataframe(
                peers[[ticker_col, "company_name", "sector", rank_signal, "sector_rank"]]
                .sort_values("sector_rank")
                .reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info("Sector peer rank needs sector and signal data.")

if company_panel[outcome_cols].isna().any().any() if outcome_cols else True:
    st.warning("Some company outcomes are missing. Interpret trends and peer ranks with care.")
