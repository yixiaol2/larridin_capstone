"""The headline test: does AI-signal -> revenue growth survive size, sector,
and momentum controls?

Builds the v3 analysis table (signals + outcomes + controls), then runs the
coefficient-survival ladder for each signal:
  spec 1: DV ~ signal
  spec 2: + sector fixed effects
  spec 3: + log market cap (size)
  spec 4: + prior revenue growth (momentum)   <- full spec
OLS with HC3 robust standard errors. Signals are cross-sectional percentile
ranks (0-1), so a coefficient reads as the DV difference between the
lowest- and highest-ranked company. DV and momentum winsorized at 1%/99%,
inf treated as missing.

Also runs the full spec on secondary DVs (margin change, 4m return) and
applies Benjamini-Hochberg FDR across the signal x DV matrix.

Output: data/processed/analysis/controls_regressions.csv (+ printed report)

Usage:
    python scripts/run_controls_analysis.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

SIGNALS = ["maturity_index", "adoption_score", "proficiency_score", "impact_score", "conc", "inv", "builder_rate"]
PRIMARY_DV = "rev_growth_yoy"
SECONDARY_DVS = ["op_margin_delta_yoy", "fwd_ret_4m"]


def winsorize(s: pd.Series, lo=0.01, hi=0.99) -> pd.Series:
    s = s.replace([np.inf, -np.inf], np.nan)
    lo_v, hi_v = s.quantile([lo, hi])
    return s.clip(lo_v, hi_v)


def build_table() -> pd.DataFrame:
    cx = pd.read_parquet("data/processed/analysis_crosssection.parquet")[
        ["ticker", "sector_larridin", "maturity_index", "adoption_score",
         "proficiency_score", "impact_score", "fwd_ret_4m"]
    ]
    fund = pd.read_parquet("data/processed/fundamentals/q1_outcomes.parquet")[
        ["ticker", "rev_growth_yoy", "op_margin_delta_yoy"]
    ]
    ctrl = pd.read_parquet("data/processed/fundamentals/controls.parquet")
    fil = pd.read_parquet("data/processed/filings/filings_signals.parquet")[["ticker", "conc", "inv"]]
    hire = pd.read_parquet("data/processed/hiring/2026-06/company_hiring_signal.parquet")[
        ["ticker", "builder_rate", "n_matched"]
    ]
    df = cx.merge(fund, on="ticker", how="left").merge(ctrl, on="ticker", how="left")
    df = df.merge(fil, on="ticker", how="left").merge(hire, on="ticker", how="left")
    df.loc[df["n_matched"] < 5, "builder_rate"] = np.nan

    for c in ["rev_growth_yoy", "op_margin_delta_yoy", "prior_rev_growth_yoy"]:
        df[c] = winsorize(df[c])
    df["log_mktcap"] = np.log(df["mktcap_t0"].replace(0, np.nan))
    for s in SIGNALS:
        df[f"{s}_rk"] = df[s].rank(pct=True)
    return df


def run_ladder(df: pd.DataFrame, signal: str, dv: str) -> list[dict]:
    rk = f"{signal}_rk"
    specs = {
        "1_univariate": f"{dv} ~ {rk}",
        "2_sector": f"{dv} ~ {rk} + C(sector_larridin)",
        "3_size": f"{dv} ~ {rk} + C(sector_larridin) + log_mktcap",
        "4_full": f"{dv} ~ {rk} + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy",
    }
    out = []
    for name, formula in specs.items():
        cols = [dv, rk, "sector_larridin", "log_mktcap", "prior_rev_growth_yoy"]
        sub = df[cols].dropna()
        if len(sub) < 50:
            continue
        m = smf.ols(formula, data=sub).fit(cov_type="HC3")
        out.append(
            {
                "signal": signal, "dv": dv, "spec": name, "n": int(m.nobs),
                "coef": m.params.get(rk), "se": m.bse.get(rk),
                "t": m.tvalues.get(rk), "p": m.pvalues.get(rk),
                "r2": m.rsquared,
            }
        )
    return out


def main() -> int:
    df = build_table()
    print(f"analysis table: {len(df)} companies")
    print("coverage:", {c: int(df[c].notna().sum())
                        for c in ["rev_growth_yoy", "prior_rev_growth_yoy", "log_mktcap",
                                  "maturity_index", "conc", "builder_rate"]})
    df.to_parquet("data/processed/analysis_table_v3.parquet", index=False)

    rows = []
    for sig in SIGNALS:
        rows += run_ladder(df, sig, PRIMARY_DV)
    for dv in SECONDARY_DVS:
        for sig in SIGNALS:
            ladder = run_ladder(df, sig, dv)
            rows += [r for r in ladder if r["spec"] == "4_full"]
    res = pd.DataFrame(rows)

    # BH-FDR across the full-spec signal x DV matrix
    full = res[res["spec"] == "4_full"].copy().sort_values("p").reset_index(drop=True)
    m_tests = len(full)
    full["bh_crit"] = [(i + 1) / m_tests * 0.05 for i in range(m_tests)]
    cutoff_idx = full[full["p"] <= full["bh_crit"]].index.max()
    full["fdr_significant"] = full.index <= cutoff_idx if pd.notna(cutoff_idx) else False
    res = res.merge(full[["signal", "dv", "fdr_significant"]], on=["signal", "dv"], how="left")

    out = Path("data/processed/analysis")
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "controls_regressions.csv", index=False)

    print("\n=== SURVIVAL LADDER: revenue growth (coef = low->high rank effect) ===")
    piv = res[res["dv"] == PRIMARY_DV].pivot_table(
        index="signal", columns="spec", values=["coef", "p"], aggfunc="first"
    ).round(4)
    print(piv.to_string())

    print("\n=== FULL-SPEC results across all DVs (FDR-corrected) ===")
    show = res[res["spec"] == "4_full"][["signal", "dv", "n", "coef", "t", "p", "fdr_significant"]]
    print(show.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
