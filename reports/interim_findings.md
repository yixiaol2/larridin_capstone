# Interim Findings

> ⚠️ **SYNTHETIC SMOKE-TEST OUTPUT — NOT RESEARCH FINDINGS.** Every number and row count below comes from running the baseline/robustness pipeline on the synthetic sample data in `data/samples/`, only to confirm the code runs end-to-end. These are not real results and must not be cited or interpreted as findings. Real findings will only come from validated real data.

Phase 9 adds reproducible baseline quantitative analysis for the synthetic/sample analytical panel.

Generated tables are written by `scripts/run_baseline_analysis.py` to:

- `data/processed/analysis/`
- `reports/tables/`

Baseline methods:

- Cross-sectional Spearman IC by quarter.
- Pooled OLS regression with available controls plus sector and quarter fixed effects.
- Equal-weight quintile backtest and Q5-Q1 long-short summary.

Interpretation guardrails:

- These outputs are associational research diagnostics.
- They do not establish causality.
- They are not investment advice.
- Synthetic sample results must not be represented as real sponsor findings.

Open review items:

- Confirm sponsor-approved benchmark or sector return field for excess return analysis.
- Confirm minimum sample thresholds for regression and quintile construction on real data.
- Decide whether robust or clustered standard errors should replace baseline OLS standard errors.

## Phase 14 Robustness and Responsible AI Diagnostics
Phase 14 adds robustness diagnostics for sector neutrality, size buckets, missingness, lag sensitivity, disclosure bias proxies, and LLM extraction reliability.
These diagnostics are descriptive checks only. They do not establish causality, solve fairness, or validate investment use.
Diagnostic row counts:
- disclosure_bias_proxy: 1
- lag_sensitivity: 3
- llm_extraction_reliability: 6
- missingness_diagnostics: 130
- sector_neutral_ic: 8
- size_bucket_analysis: 3
