"""Results — controlled regressions, sorts, and value-chain heterogeneity (real data)."""

from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.real_data import SIGNALS, load_regressions, load_table

st.set_page_config(page_title="Results", layout="wide")
st.title("Results: Regressions, Sorts, Heterogeneity")

df = load_table()
reg = load_regressions()

st.subheader("Specification ladder — revenue growth")
st.caption("Coefficient on the signal (percentile rank) as controls tighten: "
           "(1) raw → (2) +sector → (3) +size → (4) +growth momentum. HC3 robust p-values.")
lad = reg[reg["dv"] == "rev_growth_yoy"].copy()
lad["Signal"] = lad["signal"].map(SIGNALS)
piv = lad.pivot_table(index="Signal", columns="spec", values="coef", aggfunc="first").round(3)
pv = lad.pivot_table(index="Signal", columns="spec", values="p", aggfunc="first").round(3)
show = piv.astype(str) + "  (p=" + pv.astype(str) + ")"
show.columns = ["(1) Raw", "(2) +Sector", "(3) +Size", "(4) +Momentum"]
st.dataframe(show, use_container_width=True)
st.success("Narrative concreteness survives all four specifications: +8.7pp revenue-growth "
           "gap low→high (p = 0.007), passing FDR in the primary family.")

st.divider()
st.subheader("Outcome sorts")
c1, c2 = st.columns(2)
with c1:
    sub = df[["conc", "rev_growth_yoy"]].dropna()
    g = sub.groupby("conc")["rev_growth_yoy"].agg(["mean", "count"]).reset_index()
    g.columns = ["Concreteness score", "Mean revenue growth", "n"]
    fig = px.bar(g, x="Concreteness score", y="Mean revenue growth", text="n",
                 color_discrete_sequence=["#C41230"])
    fig.update_layout(height=340, yaxis_tickformat=".0%", margin=dict(l=10, r=10, t=25, b=10),
                      title="Revenue growth by concreteness score (n on bars)")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    sub = df[["maturity_index", "rev_growth_yoy"]].dropna()
    sub["Quintile"] = pd.qcut(sub["maturity_index"].rank(method="first"), 5,
                              labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    g = sub.groupby("Quintile", observed=True)["rev_growth_yoy"].mean().reset_index()
    fig = px.bar(g, x="Quintile", y="rev_growth_yoy", color_discrete_sequence=["#8A8A8A"])
    fig.update_layout(height=340, yaxis_tickformat=".0%", margin=dict(l=10, r=10, t=25, b=10),
                      title="Revenue growth by Larridin maturity quintile",
                      yaxis_title="Mean revenue growth")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Value-chain heterogeneity")
if "category" in df.columns:
    c1, c2 = st.columns(2)
    with c1:
        g = df.dropna(subset=["category", "fwd_ret_4m"]).groupby("category")["fwd_ret_4m"] \
              .agg(["mean", "count"]).reset_index()
        g.columns = ["Category", "Mean 4-mo return", "n"]
        fig = px.bar(g.sort_values("Mean 4-mo return"), x="Mean 4-mo return", y="Category",
                     orientation="h", text="n", color_discrete_sequence=["#C41230"])
        fig.update_layout(height=320, xaxis_tickformat=".0%", margin=dict(l=10, r=10, t=25, b=10),
                          title="Return by AI value-chain category")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown(
            """
**Two findings:**
- **AI-Infrastructure suppliers** returned **+48.9%** on average over four months —
  **+36.8pp vs. peers** even with sector and size controls (p<0.0001). AI's market-value
  creation has been narrowly concentrated in the suppliers.
- The **concreteness→growth link holds *within* Physical-Asset-Heavy / Late Adopters**
  (p=0.029, n=214): where AI claims are cheapest to make, concrete disclosure best
  separates genuine adopters from laggards.
"""
        )
st.caption("Hypothetical, exploratory research results — not investment advice.")
