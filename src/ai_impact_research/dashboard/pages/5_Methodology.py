"""Methodology — design, validation, and limitations (real data study)."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Methodology", layout="wide")
st.title("Methodology")

st.markdown(
    """
## Design

Cross-sectional study: AI-adoption signals measured January--March 2026 are related to
outcomes realized afterward (Q1-2026 fundamentals, reported April--May; forward returns
from the January 19 score date). Signals enter as cross-sectional percentile ranks.
Every regression controls for **sector** (12 fixed effects), **firm size** (log market
cap at the score date), and **growth momentum** (pre-signal revenue growth), with HC3
robust standard errors, 1%/99% winsorization, and Benjamini--Hochberg FDR control.

## Signals

| Signal | Source | Construction |
|---|---|---|
| Larridin scores | AI Transformation Tracker (Jan 2026) | Evidence-based LLM research pipeline, 3 pillars + maturity, 1–5 |
| Narrative concreteness | 10-K filings | LLM extraction with mandatory verbatim evidence; 1–5 anchored rubric |
| Investment intensity | 10-K filings | Same pipeline; building **or** buying AI both count |
| AI-hiring builder rate | 31k job postings (Jun + Jul 2026) | Per-posting LLM classification → company AI-builder share |

## Validation stack

- Posting classifier vs. **657 independently labeled postings**: ~90% agreement (core class)
- **87–90%** of LLM evidence quotes verify **verbatim** against source filings
- Hiring signal reproduces Larridin's independent POC ordering: Spearman **ρ = 0.83**
- Month-over-month test–retest reliability: **ρ = 0.54** (n = 226)
- Placebo signal through the same pipeline: null (p = 0.70)
- Permutation test: real concreteness coefficient exceeds **all 500** shuffled runs
- Leave-one-sector-out: significant in **all 12** re-estimations
- LLM re-scoring stability (30-company rerun): **93% exact**, 100% within ±1, concreteness rerun ρ = 0.94

## Limitations

Single score vintage (cross-sectional design, not time-series backtest); the outcome
quarter overlaps the score date by ~2 weeks (near-term association, not strict
prediction); disclosure-based signals cannot see silent adopters; conditional
associations, not causal estimates. Panel accumulation across quarterly vintages is
the designed remedy.
"""
)

st.caption(
    "Exploratory research produced in an academic–industry collaboration. "
    "Nothing herein constitutes investment advice."
)
