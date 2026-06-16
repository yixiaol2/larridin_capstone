"""Join universe + Larridin scores + forward returns into one analysis cross-section,
then run a SMOKE CHECK (coverage + rough Spearman IC).

This is a pipeline sanity check, NOT a research result: no controls, no
significance testing, no robustness. Real analysis lives in Week 2.

Dedup rule for tickers with two Larridin rows (e.g. "AMD" / "Advanced Micro
Devices"): keep the row with aiScores, then the higher page_version.

Output: data/processed/analysis_crosssection.parquet (+.csv)

Usage:
    python scripts/build_analysis_crosssection.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

SCORE_COLS = ["adoption_score", "proficiency_score", "impact_score", "maturity_index"]
RET_COLS = ["fwd_ret_1m", "fwd_ret_2m", "fwd_ret_3m", "fwd_ret_4m", "fwd_ret_latest"]


def main() -> int:
    uni = pd.read_parquet("data/processed/universe/universe.parquet")
    scores = pd.read_parquet("data/processed/larridin/scores_flat.parquet")
    rets = pd.read_parquet("data/processed/market/forward_returns.parquet")

    base = uni[uni["in_larridin"] & uni["ticker"].notna() & ~uni["share_class_dup"]]
    df = base.merge(
        scores.drop(columns=["name", "slug", "sector", "website", "created_at"]),
        on="company_id",
        how="left",
    ).merge(rets.drop(columns=["ticker_yf"]), on="ticker", how="left")

    # one row per ticker: prefer scored row, then higher page_version
    df = (
        df.sort_values(["maturity_index", "page_version"], ascending=False, na_position="last")
        .drop_duplicates("ticker")
        .sort_values("name")
        .reset_index(drop=True)
    )

    out = Path("data/processed")
    df.to_parquet(out / "analysis_crosssection.parquet", index=False)
    df.to_csv(out / "analysis_crosssection.csv", index=False)

    n = len(df)
    n_scored = int(df["maturity_index"].notna().sum())
    n_ret = int(df["fwd_ret_1m"].notna().sum())
    n_both = int((df["maturity_index"].notna() & df["fwd_ret_1m"].notna()).sum())
    print("=== SMOKE CHECK (not a research result) ===")
    print(f"rows (unique tickers, Larridin universe): {n}")
    print(f"  with aiScores: {n_scored} | with returns: {n_ret} | with both: {n_both}")

    print("\nrough Spearman IC (score vs forward return), n in parens:")
    header = "  " + " ".join(f"{r:>14s}" for r in RET_COLS)
    print(header)
    for sc in SCORE_COLS:
        cells = []
        for rc in RET_COLS:
            sub = df[[sc, rc]].dropna()
            ic, p = spearmanr(sub[sc], sub[rc])
            cells.append(f"{ic:+.3f}({len(sub)})")
        print(f"{sc:>18s}: " + " ".join(f"{c:>14s}" for c in cells))

    print("\nmaturity_index quintile mean fwd_ret_4m (rough sort):")
    sub = df[["maturity_index", "fwd_ret_4m"]].dropna()
    q = pd.qcut(sub["maturity_index"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    print(sub.groupby(q, observed=True)["fwd_ret_4m"].agg(["mean", "count"]).round(4).to_string())
    print(f"\noutput -> {out / 'analysis_crosssection.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
