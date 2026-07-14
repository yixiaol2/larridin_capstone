"""AI Adoption Signals dashboard — home page (real data).

Run:  streamlit run src/ai_impact_research/dashboard/app.py
"""

from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[2]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ai_impact_research.dashboard.real_data import load_table

st.set_page_config(page_title="AI Adoption Signals", page_icon="📊", layout="wide")

st.title("Do AI Adoption Signals Predict Company Performance?")
st.caption("CMU Capstone × Larridin — interactive research dashboard (July 2026)")

df = load_table()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Companies in universe", "564")
c2.metric("With Larridin AI scores", int(df["maturity_index"].notna().sum()))
c3.metric("Job postings classified", "30,861")
c4.metric("10-K filings scored", int(df["conc"].notna().sum()))

st.divider()

st.subheader("Headline finding")
st.markdown(
    """
> **Narrative concreteness — whether a company's 10-K reports named, deployed AI use cases
> with quantified results — predicts revenue growth through sector, size, and momentum
> controls (+8.7pp low-to-high, p = 0.007).** Composite adoption scores capture the same
> phenomenon unconditionally; the evidence-anchored concreteness dimension is what
> survives every control. Public signals show no excess-return predictability, consistent
> with markets having priced them.
"""
)

st.info(
    "Pages (sidebar): **Overview** (coverage) · **Company Explorer** (per-ticker signals) · "
    "**Signal Analysis** (interactive scatter + IC) · **Results** (regressions, sorts, "
    "value-chain heterogeneity) · **Methodology**."
)

st.caption(
    "Exploratory research; not investment advice. All signals derive from public data; "
    "every LLM-extracted score cites verbatim source evidence."
)
