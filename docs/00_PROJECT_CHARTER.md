# Project Charter

## Problem

Test whether AI adoption signals are predictive of future corporate performance, and identify which signals matter most, for which company types, and over which horizons.

## MVP Scope

- Universe: start with S&P 500 or sponsor-provided current tracker coverage.
- Granularity: company-quarter panel.
- Core signals: AI Adoption, AI Fluency, AI Impact / Initiatives, AI Hiring.
- Outcomes: forward stock return, revenue growth, operating margin change, revenue per employee.
- Methods: EDA, IC, regression, quintile backtest, robustness checks.
- Product artifact: Streamlit dashboard plus ticker-level research report generator.

## Out of Scope for MVP

- Automated trading system.
- Investment recommendation engine.
- Full causal identification.
- Full 3,000+ company coverage before the first end-to-end pipeline is validated.

## Success Criteria

1. Reproducible company-quarter analytical panel.
2. Clear source lineage and feature timing.
3. One complete backtest and at least one regression or IC table.
4. Dashboard that can explain data coverage, signal distribution, and findings.
5. Written methodology with limitations and responsible-use caveats.
