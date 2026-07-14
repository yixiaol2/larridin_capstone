"""Signal Analysis — interactive scatter, IC, and per-signal detail (real data)."""

from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from scipy.stats import spearmanr

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.real_data import OUTCOMES, SIGNALS, load_table

st.set_page_config(page_title="Signal Analysis", layout="wide")
st.title("Signal Analysis")

df = load_table()

c1, c2 = st.columns(2)
sig = c1.selectbox("Signal", list(SIGNALS), format_func=SIGNALS.get)
out = c2.selectbox("Outcome", list(OUTCOMES), format_func=OUTCOMES.get)

sub = df[[sig, out, "sector_larridin", "name", "ticker"]].dropna()
ic, p = spearmanr(sub[sig], sub[out])

m1, m2, m3 = st.columns(3)
m1.metric("Spearman IC", f"{ic:+.3f}")
m2.metric("p-value", f"{p:.4f}")
m3.metric("Companies", len(sub))

fig = px.scatter(
    sub, x=sig, y=out, color="sector_larridin", hover_data=["ticker", "name"],
    trendline="ols", trendline_scope="overall", trendline_color_override="#C41230",
    labels={sig: SIGNALS[sig], out: OUTCOMES[out], "sector_larridin": "Sector"},
)
fig.update_layout(height=520, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("IC table — all signals × outcomes")
rows = []
for s, sname in SIGNALS.items():
    r = {"Signal": sname}
    for o, oname in OUTCOMES.items():
        d = df[[s, o]].dropna()
        icv, pv = spearmanr(d[s], d[o])
        star = "**" if pv < 0.01 else ("*" if pv < 0.05 else "")
        r[oname] = f"{icv:+.3f}{star} ({len(d)})"
    rows.append(r)
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("Spearman rank correlations; */** = p<0.05/0.01; sample size in parentheses. "
           "Unconditional associations — see Results for the controlled regressions.")
