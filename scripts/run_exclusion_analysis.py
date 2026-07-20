"""Ameya's exclusion robustness test: does the headline survive dropping the
handful of mega-cap AI-semiconductor names he flagged?

Client ask (2026-07-14 review): the H1-2026 revenue-growth spike is concentrated
in a few semis (NVDA, AVGO, MU, AMD, INTC). Remove those companies entirely from
the pool -- not as a control, but dropped -- and re-run the specification ladder
on the remaining ~497 firms. If the concreteness->growth result holds without
them, it is a broad-based finding rather than a few-stock artifact.

This script mirrors run_controls_analysis.py EXACTLY (same winsorization, same
cross-sectional percentile ranks, same 4-step ladder, same HC3 SEs) and reuses
its helpers by import, so the only difference from the baseline is the row drop.
Because ranks and winsor bounds are cross-sectional, excluded firms are dropped
BEFORE ranking/winsorizing, so both are recomputed on the reduced sample.

Outputs:
  data/processed/analysis/exclusion_regressions.csv   (full vs excluded, every signal x DV x spec)
  data/processed/analysis/exclusion_valuechain.csv     (AI-Infra return premium, full vs excluded)
Usage:
  python scripts/run_exclusion_analysis.py                       # drops the default 5
  python scripts/run_exclusion_analysis.py --exclude NVDA,AVGO   # custom list
"""

# ruff: noqa: UP031, E741

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# ---- reuse the canonical helpers so logic can never drift ------------------
_spec = importlib.util.spec_from_file_location(
    "rca", str(Path(__file__).with_name("run_controls_analysis.py"))
)
rca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rca)

SIGNALS = rca.SIGNALS
PRIMARY_DV = rca.PRIMARY_DV
SECONDARY_DVS = rca.SECONDARY_DVS
winsorize = rca.winsorize

DEFAULT_EXCLUDE = ["NVDA", "AVGO", "MU", "AMD", "INTC"]  # Ameya's named semis


def build_table(exclude: set[str] | None = None) -> pd.DataFrame:
    """Identical to rca.build_table(), but drops `exclude` tickers before the
    winsorize + rank steps so both are recomputed on the surviving sample."""
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

    if exclude:
        df = df[~df["ticker"].isin(exclude)].copy()

    for c in ["rev_growth_yoy", "op_margin_delta_yoy", "prior_rev_growth_yoy"]:
        df[c] = winsorize(df[c])
    df["log_mktcap"] = np.log(df["mktcap_t0"].replace(0, np.nan))
    for s in SIGNALS:
        df[f"{s}_rk"] = df[s].rank(pct=True)
    return df


def run_all(df: pd.DataFrame, tag: str) -> pd.DataFrame:
    rows = []
    for sig in SIGNALS:
        rows += rca.run_ladder(df, sig, PRIMARY_DV)
    for dv in SECONDARY_DVS:
        for sig in SIGNALS:
            rows += [r for r in rca.run_ladder(df, sig, dv) if r["spec"] == "4_full"]
    res = pd.DataFrame(rows)
    res.insert(0, "sample", tag)
    return res


def diagnostic(exclude: list[str]) -> None:
    """Show where the excluded firms sit on the signal and the outcome (full sample)."""
    df = build_table(exclude=None)
    df["conc_growth_rk"] = df["rev_growth_yoy"].rank(pct=True)
    sub = df[df["ticker"].isin(exclude)][
        ["ticker", "sector_larridin", "conc", "conc_rk", "rev_growth_yoy", "conc_growth_rk", "fwd_ret_4m"]
    ].copy()
    sub = sub.set_index("ticker").reindex(exclude)
    print("\n=== STEP 0 DIAGNOSTIC: where do the excluded firms sit? (full sample) ===")
    print("(conc_rk / growth_rk are percentile ranks in 0-1; 1.0 = highest)")
    with pd.option_context("display.float_format", lambda v: f"{v:.3f}"):
        print(sub.rename(columns={"conc_rk": "conc_pctile", "conc_growth_rk": "growth_pctile"}).to_string())
    present = [t for t in exclude if t in set(df["ticker"])]
    print(f"\nof {len(exclude)} named tickers, {len(present)} are in the analysis universe: {present}")


def value_chain(exclude: list[str]) -> pd.DataFrame:
    """AI-Infra 4-month return premium vs peers, full sample vs after exclusion."""
    v4 = pd.read_parquet("data/processed/analysis_table_v4.parquet")
    out = []
    for tag, ex in [("full", set()), ("ex_semis", set(exclude))]:
        d = v4[~v4["ticker"].isin(ex)].copy()
        d = d[d["fwd_ret_4m"].notna()]
        d["is_infra"] = (d["category"] == "AI-Infra").astype(int)
        means = d.groupby("category")["fwd_ret_4m"].mean()
        m = smf.ols("fwd_ret_4m ~ is_infra + C(sector_larridin) + log_mktcap",
                    data=d.dropna(subset=["fwd_ret_4m", "log_mktcap"])).fit(cov_type="HC3")
        out.append({
            "sample": tag,
            "n_infra": int((d["category"] == "AI-Infra").sum()),
            "infra_mean_ret": means.get("AI-Infra", np.nan),
            "other_mean_ret": d.loc[d["category"] != "AI-Infra", "fwd_ret_4m"].mean(),
            "infra_premium_ctrl": m.params.get("is_infra"),
            "premium_p": m.pvalues.get("is_infra"),
        })
    return pd.DataFrame(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDE),
                    help="comma-separated tickers to drop")
    args = ap.parse_args()
    exclude = [t.strip().upper() for t in args.exclude.split(",") if t.strip()]

    print(f"Exclusion robustness test -- dropping: {exclude}")
    diagnostic(exclude)

    full = run_all(build_table(exclude=None), "full")
    excl = run_all(build_table(exclude=set(exclude)), "ex_semis")
    res = pd.concat([full, excl], ignore_index=True)

    out = Path("data/processed/analysis")
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "exclusion_regressions.csv", index=False)

    # headline side-by-side: revenue growth ladder, full vs excluded
    print("\n=== HEADLINE: revenue-growth ladder, FULL vs EX-SEMIS (coef / p) ===")
    rev = res[res["dv"] == PRIMARY_DV].copy()
    for sig in SIGNALS:
        block = rev[rev["signal"] == sig]
        f4 = block[(block["sample"] == "full") & (block["spec"] == "4_full")]
        e4 = block[(block["sample"] == "ex_semis") & (block["spec"] == "4_full")]
        if f4.empty or e4.empty:
            continue
        fc, fp, fn = f4.iloc[0][["coef", "p", "n"]]
        ec, ep, en = e4.iloc[0][["coef", "p", "n"]]
        if fp < 0.05 and ep < 0.05:
            flag = "   [SURVIVES]"
        elif fp < 0.05 and ep >= 0.05:
            flag = "   [LOST significance]"
        else:
            flag = "   [n.s. either way]"
        print(f"  {sig:18s} full: coef={fc:+.4f} p={fp:.4f} (n={int(fn)})   "
              f"ex-semis: coef={ec:+.4f} p={ep:.4f} (n={int(en)}){flag}")

    print("\n=== full ladder (all 4 specs) for the headline signal 'conc' ===")
    conc = rev[rev["signal"] == "conc"].pivot_table(
        index="spec", columns="sample", values=["coef", "p"], aggfunc="first").round(4)
    print(conc.to_string())

    print("\n=== SECONDARY DVs (full spec), FULL vs EX-SEMIS ===")
    for dv in SECONDARY_DVS:
        print(f"  -- {dv} --")
        block = res[(res["dv"] == dv) & (res["spec"] == "4_full")]
        for sig in SIGNALS:
            f = block[(block["sample"] == "full") & (block["signal"] == sig)]
            e = block[(block["sample"] == "ex_semis") & (block["signal"] == sig)]
            if f.empty or e.empty:
                continue
            print(f"    {sig:18s} full p={f.iloc[0]['p']:.3f}  ex p={e.iloc[0]['p']:.3f}  "
                  f"(coef {f.iloc[0]['coef']:+.4f} -> {e.iloc[0]['coef']:+.4f})")

    vc = value_chain(exclude)
    vc.to_csv(out / "exclusion_valuechain.csv", index=False)
    print("\n=== VALUE CHAIN: AI-Infra 4-month return premium, FULL vs EX-SEMIS ===")
    with pd.option_context("display.float_format", lambda v: f"{v:.4f}"):
        print(vc.to_string(index=False))

    print("\nWrote data/processed/analysis/exclusion_regressions.csv "
          "and exclusion_valuechain.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
