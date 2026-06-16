# Backtesting Methodology

> ⚠️ **Original scaffold design — not current reality.** This assumes a multi-quarter panel with IC / backtests. Larridin's scores are a single January-2026 snapshot, so the current study is **cross-sectional** (signals → subsequent outcomes), not a multi-period backtest. See [`HANDOFF.md`](../HANDOFF.md).

## Main hypotheses

- H1: Higher AI adoption scores are positively associated with future excess returns.
- H2: AI hiring scores lead future revenue per employee growth.
- H3: AI impact scores are more strongly associated with margin expansion than raw AI mention intensity.

## Feature timing

Only use features that are available at or before the prediction date. Every record should carry `available_at`.

The analytical panel uses these timing conventions:

- Panel grain is one row per `company_id` per `score_quarter`.
- `prediction_date` defaults to the Larridin score `available_at` date unless an explicit prediction date is supplied for a research experiment.
- `score_available_at` must be at or before `prediction_date`.
- Market outcomes start from the first price date after `prediction_date`; the one-quarter outcome ends at the next available price date.
- `prior_return_1q` uses only prices at or before `prediction_date`.
- Financial controls use only fundamentals with `available_at <= prediction_date`.
- Future fundamental outcomes use fiscal periods ending after `prediction_date`.
- Strict mode excludes rows with timing violations.
- Permissive mode preserves rows and sets `timing_warning` / `timing_violation` for audit.

## Core metrics

- Spearman information coefficient (IC)
- Mean IC and IC hit rate
- Regression coefficient, p-value, and confidence interval
- Quintile portfolio return
- Q5-Q1 long-short return
- Sharpe ratio, if sufficient time-series observations exist

## Basic regression

```text
future_outcome_i,t+1 = beta_0
  + beta_1 * ai_signal_i,t
  + beta_2 * log_market_cap_i,t
  + beta_3 * prior_return_i,t
  + sector fixed effects
  + quarter fixed effects
  + error_i,t
```

## Quintile portfolio construction

For each rebalance period:

- Use the analytical panel after strict timing filtering.
- Rank companies by the selected AI signal within the period.
- Form quintiles only when there are enough names for meaningful buckets.
- Compute equal-weight average forward returns by quintile.
- Report Q5-Q1 long-short return when both edge quintiles are populated.
- Use `fwd_excess_return_1q` only as a benchmark-relative diagnostic unless a sponsor-approved benchmark field is available.

Rows with missing signal, missing outcome, or `timing_violation = true` should be excluded from strict IC, regression, and backtest runs.

## Baseline quantitative analysis

Phase 9 implements three transparent baseline tests:

- Cross-sectional Spearman IC by quarter for each AI signal/outcome pair.
- Pooled OLS regressions with optional controls plus sector and quarter fixed effects.
- Equal-weight quintile backtests with Q5-Q1 long-short returns.

Default signals:

- `ai_adoption_score`
- `ai_fluency_score`
- `ai_impact_score`
- `ai_hiring_score`
- `composite_ai_score`

Default outcomes:

- `fwd_return_1q`
- `fwd_return_2q`
- `future_revenue_growth_qoq`
- `future_operating_margin_delta_qoq`
- `future_revenue_per_employee_growth_qoq`

Regression controls are included only when available:

- `prior_return_1q`
- `revenue_growth_qoq`
- `operating_margin_t`
- `log_market_cap`

These baselines are intended for signal discovery and reproducibility checks. They do not establish causality and must not be presented as investment advice.

## Robustness diagnostics

Phase 14 adds descriptive robustness checks that should be reviewed before interpreting signal relationships:

- Sector-neutral IC computes within-sector IC values and compares their average with raw cross-sectional IC.
- Size bucket analysis compares signal distributions and IC across small / mid / large buckets when `market_cap` or `log_market_cap` is available.
- Missingness diagnostics report missingness by sector, quarter, signal, and outcome, and flag highly concentrated gaps.
- Lag sensitivity compares available 1Q, 2Q, and 4Q horizons where those outcome columns exist.
- Disclosure bias proxy checks the relationship between disclosure-volume fields and AI scores when source document counts or filing lengths are available.
- LLM extraction reliability reports schema/evidence/confidence diagnostics when extraction JSONL outputs exist.

These checks are guardrails, not proof. Sector-neutral IC can become unstable when sector groups are small, size buckets require defensible market-cap fields, and disclosure-bias proxies are placeholders until real source-document volume fields are available.

## Caveats

- Correlation is not causation.
- Short history may make Sharpe ratios unstable.
- Disclosure intensity may bias AI scores toward large-cap or technology companies.
- Hypothetical backtests are not investment advice.
- Robustness checks do not solve fairness or eliminate omitted-variable bias.
