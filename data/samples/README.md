# Synthetic Sample Data

The CSV files in this folder are fully synthetic. They are designed for local smoke tests and demonstrations of the AI Impact Research workflow.

They do not contain private Larridin exports, vendor data, live market data, or real company fundamentals. Ticker-like symbols and company names are invented for reproducible testing.

## Files

- `companies.csv`: 12 synthetic companies across multiple sectors.
- `larridin_scores.csv`: Four quarters of synthetic AI adoption, fluency, impact, and hiring scores.
- `market_prices.csv`: Five quarter-end synthetic adjusted close observations for forward-return examples.
- `fundamentals.csv`: Four quarters of synthetic revenue, gross margin, operating margin, net income, employee count, fiscal period end, and availability timing.

## Timing

Each feature-bearing file includes dates that support point-in-time checks:

- Score records include `snapshot_date` and `available_at`.
- Market records include `price_date` and `available_at`.
- Fundamentals records include `fiscal_period_end` and `available_at`.

Use these files only for local tests and examples. Do not interpret generated analysis as evidence about real companies.
