"""Company Explorer — all signals and outcomes for one ticker (real data)."""

from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.real_data import SIGNALS, load_table

st.set_page_config(page_title="Company Explorer", layout="wide")
st.title("Company Explorer")

df = load_table()
options = df.dropna(subset=["maturity_index"]).sort_values("ticker")
label = {t: f"{t} — {n}" for t, n in zip(options["ticker"], options["name"])}  # noqa: B905 — py3.8 compat
ticker = st.selectbox("Company", options["ticker"], format_func=lambda t: label.get(t, t))

row = df[df["ticker"] == ticker].iloc[0]
sector = row["sector_larridin"]
peers = df[df["sector_larridin"] == sector]

st.subheader(f"{row['name']}  ({ticker})")
st.caption(f"Sector: {sector}  ·  AI value-chain category: {row.get('category', '—')}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Larridin maturity", f"{row['maturity_index']:.1f}" if pd.notna(row["maturity_index"]) else "—")
c2.metric("Concreteness (10-K)", f"{row['conc']:.0f}" if pd.notna(row["conc"]) else "—")
c3.metric("Investment intensity", f"{row['inv']:.0f}" if pd.notna(row["inv"]) else "—")
c4.metric("AI-hiring builder rate", f"{row['builder_rate']:.0%}" if pd.notna(row["builder_rate"]) else "—")

c1, c2, c3 = st.columns(3)
c1.metric("Revenue growth YoY (Q1-26)",
          f"{row['rev_growth_yoy']:+.1%}" if pd.notna(row["rev_growth_yoy"]) else "—")
c2.metric("Margin change YoY",
          f"{row['op_margin_delta_yoy']:+.1%}" if pd.notna(row["op_margin_delta_yoy"]) else "—")
c3.metric("4-month return", f"{row['fwd_ret_4m']:+.1%}" if pd.notna(row["fwd_ret_4m"]) else "—")

st.divider()
st.subheader(f"Rank within {sector} peers (n={len(peers)})")

rank_rows = []
for col, name in SIGNALS.items():
    if pd.notna(row.get(col)):
        pct = (peers[col] < row[col]).mean()
        rank_rows.append({"Signal": name, "Value": round(float(row[col]), 2),
                          "Sector percentile": f"{pct:.0%}"})
st.dataframe(pd.DataFrame(rank_rows), hide_index=True, use_container_width=True)

st.caption("Missing values indicate the company is outside that signal's coverage (see Overview).")
