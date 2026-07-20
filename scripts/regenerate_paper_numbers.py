"""Regenerate EVERY data-derived number in the paper, for the full sample AND
for the analysis base that excludes the five largest AI-semiconductor firms
(NVDA, AVGO, MU, AMD, INTC), from one reproducible harness.

Motivation: the paper's ladder is reproducible (run_controls_analysis.py), but
the IC table, sorts, complete-case, heterogeneity, value-chain, placebo, and
permutation numbers were computed ad-hoc with no saved script. To make the
exclusion-based version trustworthy we recompute all of them here from the
source tables, print a validation column against the paper's currently stated
full-sample numbers, and emit both bases so the paper's main (ex-5) and
appendix (full) numbers come from identical code.

Outputs:
  data/processed/analysis/paper_numbers_full.json
  data/processed/analysis/paper_numbers_ex5.json
Usage:
  python scripts/regenerate_paper_numbers.py
"""

# ruff: noqa: UP031, E741

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import spearmanr

_spec = importlib.util.spec_from_file_location(
    "rca", str(Path(__file__).with_name("run_controls_analysis.py"))
)
rca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rca)
winsorize = rca.winsorize
run_ladder = rca.run_ladder
SIGNALS = rca.SIGNALS

EXCLUDE = ["NVDA", "AVGO", "MU", "AMD", "INTC"]
SIGNAL_LABEL = {
    "conc": "concreteness", "inv": "investment_intensity",
    "adoption_score": "adoption", "maturity_index": "maturity",
    "impact_score": "impact", "proficiency_score": "proficiency",
    "builder_rate": "builder_rate",
}


def build_base(exclude=None) -> pd.DataFrame:
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
    cat = pd.read_parquet("data/processed/analysis_table_v4.parquet")[["ticker", "category"]]
    name = pd.read_parquet("data/processed/universe/universe.parquet")[["ticker", "name"]].drop_duplicates("ticker")

    df = cx.merge(fund, on="ticker", how="left").merge(ctrl, on="ticker", how="left")
    df = df.merge(fil, on="ticker", how="left").merge(hire, on="ticker", how="left")
    df = df.merge(cat, on="ticker", how="left").merge(name, on="ticker", how="left")
    df.loc[df["n_matched"] < 5, "builder_rate"] = np.nan

    if exclude:
        df = df[~df["ticker"].isin(exclude)].copy()

    for c in ["rev_growth_yoy", "op_margin_delta_yoy", "prior_rev_growth_yoy"]:
        df[c] = winsorize(df[c])
    df["log_mktcap"] = np.log(df["mktcap_t0"].replace(0, np.nan))
    for s in SIGNALS:
        df[f"{s}_rk"] = df[s].rank(pct=True)
    df["namelen"] = df["name"].fillna("").str.len()
    df["namelen_rk"] = df["namelen"].rank(pct=True)
    return df


def ladder(df) -> dict:
    out = {}
    for s in SIGNALS:
        rows = run_ladder(df, s, "rev_growth_yoy")
        out[s] = {r["spec"]: {"coef": r["coef"], "p": r["p"], "n": r["n"]} for r in rows}
        # secondary DVs, full spec only
        for dv in ["op_margin_delta_yoy", "fwd_ret_4m"]:
            r = [x for x in run_ladder(df, s, dv) if x["spec"] == "4_full"]
            if r:
                out[s][f"full_{dv}"] = {"coef": r[0]["coef"], "p": r[0]["p"], "n": r[0]["n"]}
    return out


def _spear(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 10:
        return None
    rho, p = spearmanr(d.iloc[:, 0], d.iloc[:, 1])
    return {"rho": float(rho), "p": float(p), "n": int(len(d))}


def ic_table(df) -> dict:
    out = {}
    for s in SIGNALS:
        out[s] = {
            "rev_growth": _spear(df[s], df["rev_growth_yoy"]),
            "margin": _spear(df[s], df["op_margin_delta_yoy"]),
            "ret4m": _spear(df[s], df["fwd_ret_4m"]),
        }
        # sector-neutral IC on revenue growth: within-sector ranks, then correlate
        sub = df[[s, "rev_growth_yoy", "sector_larridin"]].dropna()
        if len(sub) >= 10:
            sr = sub.groupby("sector_larridin")[s].rank(pct=True)
            yr = sub.groupby("sector_larridin")["rev_growth_yoy"].rank(pct=True)
            rho, p = spearmanr(sr, yr)
            out[s]["sector_neutral_rev_growth"] = {"rho": float(rho), "p": float(p), "n": int(len(sub))}
    return out


def sorts(df) -> dict:
    out = {}
    cb = df.dropna(subset=["conc", "rev_growth_yoy"]).groupby("conc")["rev_growth_yoy"]
    out["conc_bins"] = {int(k): {"mean": float(v.mean()), "n": int(v.count())} for k, v in cb}
    lo = df[df["conc"].isin([1, 2])]["rev_growth_yoy"].dropna()
    hi = df[df["conc"].isin([4, 5])]["rev_growth_yoy"].dropna()
    # two-sample t
    from scipy.stats import ttest_ind
    t, p = ttest_ind(hi, lo, equal_var=False)
    out["conc_high_minus_low"] = {"diff": float(hi.mean() - lo.mean()), "t": float(t), "n_hi": int(len(hi)), "n_lo": int(len(lo))}

    mq = df.dropna(subset=["maturity_index", "rev_growth_yoy"]).copy()
    mq["q"] = pd.qcut(mq["maturity_index"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    g = mq.groupby("q", observed=True)["rev_growth_yoy"]
    out["maturity_quintiles"] = {int(k): {"mean": float(v.mean()), "n": int(v.count())} for k, v in g}
    q = out["maturity_quintiles"]
    out["maturity_q5_minus_q1"] = q[5]["mean"] - q[1]["mean"]
    # 4-month return by maturity quintile (for the sorts-table note)
    mr = df.dropna(subset=["maturity_index", "fwd_ret_4m"]).copy()
    mr["q"] = pd.qcut(mr["maturity_index"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    out["maturity_quintile_ret4m"] = {int(k): float(v) for k, v in mr.groupby("q", observed=True)["fwd_ret_4m"].mean().items()}
    return out


def coverage(df) -> dict:
    return {
        "total": int(len(df)),
        "maturity": int(df["maturity_index"].notna().sum()),
        "adoption": int(df["adoption_score"].notna().sum()),
        "conc": int(df["conc"].notna().sum()),
        "inv": int(df["inv"].notna().sum()),
        "builder": int(df["builder_rate"].notna().sum()),
        "rev_growth": int(df["rev_growth_yoy"].notna().sum()),
        "margin": int(df["op_margin_delta_yoy"].notna().sum()),
        "ret4m": int(df["fwd_ret_4m"].notna().sum()),
        "log_mktcap": int(df["log_mktcap"].notna().sum()),
        "prior_rev_growth": int(df["prior_rev_growth_yoy"].notna().sum()),
    }


def complete_case(df) -> dict:
    cols = [f"{s}_rk" for s in SIGNALS] + ["rev_growth_yoy", "sector_larridin", "log_mktcap", "prior_rev_growth_yoy"]
    sub = df[cols].dropna()
    out = {"n": int(len(sub)), "signals": {}}
    for s in ["conc", "inv", "adoption_score", "maturity_index", "builder_rate"]:
        m = smf.ols(f"rev_growth_yoy ~ {s}_rk + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy", data=sub).fit(cov_type="HC3")
        out["signals"][s] = {"coef": float(m.params[f"{s}_rk"]), "p": float(m.pvalues[f"{s}_rk"])}
    out["coef"] = out["signals"]["conc"]["coef"]
    out["p"] = out["signals"]["conc"]["p"]
    return out


def heterogeneity(df) -> dict:
    out = {"within_category": {}, "category_mean_ret": {}}
    for cat in ["AI-Infra", "AI-Software", "Data-Rich", "Physical/Late"]:
        sub = df[df["category"] == cat].dropna(subset=["rev_growth_yoy", "conc_rk", "log_mktcap", "prior_rev_growth_yoy"])
        if len(sub) >= 20:
            m = smf.ols("rev_growth_yoy ~ conc_rk + log_mktcap + prior_rev_growth_yoy", data=sub).fit(cov_type="HC3")
            out["within_category"][cat] = {"coef": float(m.params["conc_rk"]), "p": float(m.pvalues["conc_rk"]), "n": int(m.nobs)}
        r = df[df["category"] == cat]["fwd_ret_4m"].dropna()
        out["category_mean_ret"][cat] = {"mean": float(r.mean()), "n": int(len(r))}
    # infra premium: infra vs late-adopter, sector + size controls (paper spec)
    il = df[df["category"].isin(["AI-Infra", "Physical/Late"])].dropna(subset=["fwd_ret_4m", "log_mktcap"]).copy()
    il["is_infra"] = (il["category"] == "AI-Infra").astype(int)
    m = smf.ols("fwd_ret_4m ~ is_infra + C(sector_larridin) + log_mktcap", data=il).fit(cov_type="HC3")
    out["infra_premium_vs_late"] = {"coef": float(m.params["is_infra"]), "p": float(m.pvalues["is_infra"]), "n": int(m.nobs)}
    return out


def placebo(df) -> dict:
    sub = df[["rev_growth_yoy", "namelen_rk", "sector_larridin", "log_mktcap", "prior_rev_growth_yoy"]].dropna()
    m = smf.ols("rev_growth_yoy ~ namelen_rk + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy", data=sub).fit(cov_type="HC3")
    return {"coef": float(m.params["namelen_rk"]), "p": float(m.pvalues["namelen_rk"]), "n": int(m.nobs)}


def permutation(df, n_perm=1000, seed=12345) -> dict:
    cols = ["rev_growth_yoy", "conc_rk", "sector_larridin", "log_mktcap", "prior_rev_growth_yoy"]
    sub = df[cols].dropna().reset_index(drop=True)
    obs = smf.ols("rev_growth_yoy ~ conc_rk + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy", data=sub).fit()
    obs_coef = float(obs.params["conc_rk"])
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        s2 = sub.copy()
        s2["conc_rk"] = rng.permutation(s2["conc_rk"].values)
        m = smf.ols("rev_growth_yoy ~ conc_rk + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy", data=s2).fit()
        if abs(float(m.params["conc_rk"])) >= abs(obs_coef):
            ge += 1
    return {"obs_coef": obs_coef, "n_perm": n_perm, "n_ge": ge, "p": (ge + 1) / (n_perm + 1)}


def leave_one_sector(df) -> dict:
    worst = None
    runs = {}
    for sec in sorted(df["sector_larridin"].dropna().unique()):
        sub = df[df["sector_larridin"] != sec].dropna(subset=["rev_growth_yoy", "conc_rk", "log_mktcap", "prior_rev_growth_yoy"])
        m = smf.ols("rev_growth_yoy ~ conc_rk + C(sector_larridin) + log_mktcap + prior_rev_growth_yoy", data=sub).fit(cov_type="HC3")
        runs[sec] = {"coef": float(m.params["conc_rk"]), "p": float(m.pvalues["conc_rk"]), "n": int(m.nobs)}
        if worst is None or runs[sec]["p"] > runs[worst]["p"]:
            worst = sec
    return {"worst_sector": worst, "worst": runs[worst], "n_significant": sum(v["p"] < 0.05 for v in runs.values()), "n_sectors": len(runs)}


def compute_all(exclude):
    df = build_base(exclude=exclude)
    return {
        "n_rows": int(len(df)),
        "ladder": ladder(df),
        "ic": ic_table(df),
        "sorts": sorts(df),
        "complete_case": complete_case(df),
        "heterogeneity": heterogeneity(df),
        "placebo": placebo(df),
        "permutation": permutation(df),
        "leave_one_sector": leave_one_sector(df),
        "coverage": coverage(df),
    }


def main():
    full = compute_all(exclude=None)
    ex5 = compute_all(exclude=EXCLUDE)
    outdir = Path("data/processed/analysis")
    (outdir / "paper_numbers_full.json").write_text(json.dumps(full, indent=2))
    (outdir / "paper_numbers_ex5.json").write_text(json.dumps(ex5, indent=2))

    def g(d, *ks):
        for k in ks:
            d = d[k]
        return d

    print("=" * 78)
    print("VALIDATION: my full-sample recompute vs paper's stated numbers")
    print("=" * 78)
    L = full["ladder"]
    print("\nLadder conc (paper: .148/.094/.084/.087, n=399):")
    print("  mine: %.3f/%.3f/%.3f/%.3f  n=%d" % (
        L["conc"]["1_univariate"]["coef"], L["conc"]["2_sector"]["coef"],
        L["conc"]["3_size"]["coef"], L["conc"]["4_full"]["coef"], L["conc"]["4_full"]["n"]))
    print("Ladder inv (paper: .129/.076/.057/.048):  mine: %.3f/%.3f/%.3f/%.3f" % (
        L["inv"]["1_univariate"]["coef"], L["inv"]["2_sector"]["coef"],
        L["inv"]["3_size"]["coef"], L["inv"]["4_full"]["coef"]))
    print("Ladder adoption (paper .115/.075/.049/.037): mine: %.3f/%.3f/%.3f/%.3f" % (
        L["adoption_score"]["1_univariate"]["coef"], L["adoption_score"]["2_sector"]["coef"],
        L["adoption_score"]["3_size"]["coef"], L["adoption_score"]["4_full"]["coef"]))
    I = full["ic"]
    print("\nIC rev_growth (paper conc+.236/adopt+.189/mat+.184/impact+.177/inv+.164/prof+.126):")
    print("  mine conc %+.3f(n=%d) adopt %+.3f mat %+.3f impact %+.3f inv %+.3f prof %+.3f" % (
        I["conc"]["rev_growth"]["rho"], I["conc"]["rev_growth"]["n"], I["adoption_score"]["rev_growth"]["rho"],
        I["maturity_index"]["rev_growth"]["rho"], I["impact_score"]["rev_growth"]["rho"],
        I["inv"]["rev_growth"]["rho"], I["proficiency_score"]["rev_growth"]["rho"]))
    print("Sector-neutral IC (paper conc+.153/adopt+.116/mat+.107/impact+.111/inv+.062/prof+.039):")
    print("  mine conc %+.3f adopt %+.3f mat %+.3f impact %+.3f inv %+.3f prof %+.3f" % (
        I["conc"]["sector_neutral_rev_growth"]["rho"], I["adoption_score"]["sector_neutral_rev_growth"]["rho"],
        I["maturity_index"]["sector_neutral_rev_growth"]["rho"], I["impact_score"]["sector_neutral_rev_growth"]["rho"],
        I["inv"]["sector_neutral_rev_growth"]["rho"], I["proficiency_score"]["sector_neutral_rev_growth"]["rho"]))
    S = full["sorts"]
    print("\nConc bins (paper 1:-9.4/2:7.3/3:9.1/4:13.5/5:52.2; hi-lo +8.2 t=4.18):")
    print("  mine:", {k: (round(v["mean"] * 100, 1), v["n"]) for k, v in S["conc_bins"].items()},
          "hi-lo %+.1fpp t=%.2f" % (S["conc_high_minus_low"]["diff"] * 100, S["conc_high_minus_low"]["t"]))
    print("Maturity quintiles (paper Q1 8.5..Q5 16.6, Q5-Q1 +8.1): mine",
          {k: round(v["mean"] * 100, 1) for k, v in S["maturity_quintiles"].items()},
          "Q5-Q1 %+.1f" % (S["maturity_q5_minus_q1"] * 100))
    print("\nComplete-case (paper n=199, 0.076, p=0.11): mine n=%d coef=%.3f p=%.3f" % (
        full["complete_case"]["n"], full["complete_case"]["coef"], full["complete_case"]["p"]))
    H = full["heterogeneity"]
    print("Heterogeneity within-cat conc (paper Phys .064 p.029 n214 / Soft .074 p.050 / Infra .146 p.143 n26):")
    for c in ["Physical/Late", "AI-Software", "AI-Infra", "Data-Rich"]:
        w = H["within_category"].get(c)
        if w:
            print("  %-14s coef %+.3f p %.3f n %d" % (c, w["coef"], w["p"], w["n"]))
    print("Category mean 4m ret (paper Infra+48.9/Soft-3.8/Data-3.5/Phys+1.8): mine",
          {c: round(v["mean"] * 100, 1) for c, v in H["category_mean_ret"].items()})
    print("Infra premium vs late (paper +36.8pp p<1e-4): mine %+.1fpp p=%.2e n=%d" % (
        H["infra_premium_vs_late"]["coef"] * 100, H["infra_premium_vs_late"]["p"], H["infra_premium_vs_late"]["n"]))
    print("Placebo (paper p=0.70): mine p=%.3f | Permutation (paper p<0.002): mine p=%.4f (%d/%d)" % (
        full["placebo"]["p"], full["permutation"]["p"], full["permutation"]["n_ge"], full["permutation"]["n_perm"]))
    print("Leave-one-sector worst (paper drop tech 0.073 p0.030): mine worst=%s %.3f p%.3f; sig in %d/%d" % (
        full["leave_one_sector"]["worst_sector"], full["leave_one_sector"]["worst"]["coef"],
        full["leave_one_sector"]["worst"]["p"], full["leave_one_sector"]["n_significant"], full["leave_one_sector"]["n_sectors"]))

    print("\n" + "=" * 78)
    print("EX-5 BASE (drop NVDA/AVGO/MU/AMD/INTC) -- the new paper main numbers")
    print("=" * 78)
    print("n_rows: full=%d ex5=%d" % (full["n_rows"], ex5["n_rows"]))
    Le = ex5["ladder"]
    print("\nLadder (rev growth) full-spec coef/p, FULL -> EX5:")
    for s in SIGNALS:
        f4, e4 = full["ladder"][s]["4_full"], Le[s]["4_full"]
        print("  %-18s %+.3f (p%.3f) -> %+.3f (p%.3f)  n %d->%d" % (
            SIGNAL_LABEL[s], f4["coef"], f4["p"], e4["coef"], e4["p"], f4["n"], e4["n"]))
    print("\nEX5 conc full ladder: %.3f/%.3f/%.3f/%.3f (p %.3f/%.3f/%.3f/%.3f) n=%d" % (
        Le["conc"]["1_univariate"]["coef"], Le["conc"]["2_sector"]["coef"], Le["conc"]["3_size"]["coef"], Le["conc"]["4_full"]["coef"],
        Le["conc"]["1_univariate"]["p"], Le["conc"]["2_sector"]["p"], Le["conc"]["3_size"]["p"], Le["conc"]["4_full"]["p"],
        Le["conc"]["4_full"]["n"]))
    Ie, Se, He = ex5["ic"], ex5["sorts"], ex5["heterogeneity"]
    print("EX5 IC conc rev_growth %+.3f (n=%d); sector-neutral %+.3f" % (
        Ie["conc"]["rev_growth"]["rho"], Ie["conc"]["rev_growth"]["n"], Ie["conc"]["sector_neutral_rev_growth"]["rho"]))
    print("EX5 conc bins:", {k: (round(v["mean"] * 100, 1), v["n"]) for k, v in Se["conc_bins"].items()},
          "hi-lo %+.1fpp t=%.2f" % (Se["conc_high_minus_low"]["diff"] * 100, Se["conc_high_minus_low"]["t"]))
    print("EX5 maturity Q5-Q1 %+.1fpp" % (Se["maturity_q5_minus_q1"] * 100))
    print("EX5 complete-case n=%d coef=%.3f p=%.3f" % (ex5["complete_case"]["n"], ex5["complete_case"]["coef"], ex5["complete_case"]["p"]))
    print("EX5 within-cat conc:", {c: (round(v["coef"], 3), round(v["p"], 3), v["n"]) for c, v in He["within_category"].items()})
    print("EX5 category mean ret:", {c: round(v["mean"] * 100, 1) for c, v in He["category_mean_ret"].items()})
    print("EX5 infra premium vs late %+.1fpp p=%.2e n=%d" % (
        He["infra_premium_vs_late"]["coef"] * 100, He["infra_premium_vs_late"]["p"], He["infra_premium_vs_late"]["n"]))
    print("EX5 placebo p=%.3f | permutation p=%.4f | leave-one-sector worst=%s %.3f p%.3f sig %d/%d" % (
        ex5["placebo"]["p"], ex5["permutation"]["p"], ex5["leave_one_sector"]["worst_sector"],
        ex5["leave_one_sector"]["worst"]["coef"], ex5["leave_one_sector"]["worst"]["p"],
        ex5["leave_one_sector"]["n_significant"], ex5["leave_one_sector"]["n_sectors"]))
    print("\nWrote paper_numbers_full.json and paper_numbers_ex5.json")


if __name__ == "__main__":
    main()
