"""Overview — universe composition and signal coverage (real data)."""

from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.real_data import coverage, load_table

st.set_page_config(page_title="Overview", layout="wide")
st.title("Overview: Universe & Coverage")

df = load_table()

left, right = st.columns([1, 1])

with left:
    st.subheader("Coverage by variable")
    st.dataframe(coverage(df), hide_index=True, use_container_width=True)
    st.caption(
        "Missingness is documented and non-random: banks lack comparable revenue "
        "concepts, foreign filers lack 10-Ks, thin hiring samples (<5 postings) are excluded."
    )

with right:
    st.subheader("Companies by sector")
    sec = df["sector_larridin"].value_counts().reset_index()
    sec.columns = ["Sector", "Companies"]
    fig = px.bar(sec, x="Companies", y="Sector", orientation="h",
                 color_discrete_sequence=["#C41230"])
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Larridin maturity distribution")
    fig = px.histogram(df.dropna(subset=["maturity_index"]), x="maturity_index", nbins=20,
                       color_discrete_sequence=["#C41230"])
    fig.update_layout(height=320, xaxis_title="Maturity index (1–5)",
                      yaxis_title="Companies", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.subheader("Narrative concreteness distribution")
    fig = px.histogram(df.dropna(subset=["conc"]), x="conc", nbins=5,
                       color_discrete_sequence=["#C41230"])
    fig.update_layout(height=320, xaxis_title="Concreteness score (1–5)",
                      yaxis_title="Companies", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
