"""Flatten the local Larridin snapshot into clean analysis tables.

Input:  data/raw/larridin/<date>/companies.json + company_pages.json
Output: data/processed/larridin/companies_clean.parquet (+.csv)
        data/processed/larridin/scores_flat.parquet (+.csv)
        data/processed/larridin/dedup_log.csv

Cleaning rules (documented for the paper's data section):
- Drop obvious test rows (name == "Test Company").
- Companies with duplicate names: keep the id whose latest aiScores page is
  most recent (fallback: latest created_at); log every drop.
- Score source: per company, the highest-version page whose content has
  aiScores; pages without aiScores (old maturityAssessment format) are only
  used if no aiScores page exists (then scores stay NaN).

Usage:
    python scripts/flatten_larridin_scores.py [--snapshot 2026-06-10]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

SUBDIMS = [
    "deploymentBreadth",
    "hiringIntensity",
    "vendorFootprint",
    "governanceSignals",
    "workforceFluency",
    "enablementInfra",
    "leadershipDepth",
    "useSophistication",
    "quantifiedOutcomes",
    "financialLinkage",
    "repeatability",
]
EVIDENCE_SOURCE_TYPES = ["sec", "news", "corporate", "blog", "other"]


def latest_snapshot_dir(root: Path) -> Path:
    dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if not dirs:
        raise FileNotFoundError(f"no snapshot dirs under {root}")
    return dirs[-1]


def flatten_ai_scores(content: dict) -> dict:
    ais = content.get("aiScores") or {}
    row: dict = {
        "maturity_index": pd.to_numeric(ais.get("maturityIndex"), errors="coerce"),
        "maturity_stage": ais.get("maturityStage"),
        "assessed_at": ais.get("assessedAt"),
    }
    ev_counts = dict.fromkeys(EVIDENCE_SOURCE_TYPES, 0)
    for dim in ("adoption", "proficiency", "impact"):
        d = ais.get(dim) or {}
        row[f"{dim}_score"] = pd.to_numeric(d.get("score"), errors="coerce")
        row[f"{dim}_label"] = d.get("label")
        row[f"{dim}_confidence"] = d.get("confidence")
        row[f"{dim}_n_evidence"] = len(d.get("evidence") or [])
        row[f"{dim}_n_missing_evidence"] = len(d.get("missingEvidence") or [])
        for e in d.get("evidence") or []:
            st = e.get("sourceType")
            ev_counts[st if st in ev_counts else "other"] += 1
        for sd in d.get("subDimensions") or []:
            name = sd.get("name")
            if name in SUBDIMS:
                row[f"sub_{name}"] = pd.to_numeric(sd.get("score"), errors="coerce")
    for st, n in ev_counts.items():
        row[f"evidence_{st}"] = n
    row["n_ai_apps_used"] = len(content.get("aiAppsUsed") or [])
    row["n_impact_metrics"] = len(content.get("impactMetrics") or [])
    row["n_initiatives"] = len(content.get("initiatives") or [])
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default=None, help="snapshot date folder; default latest")
    args = parser.parse_args()

    raw_root = Path("data/raw/larridin")
    snap_dir = raw_root / args.snapshot if args.snapshot else latest_snapshot_dir(raw_root)
    out_dir = Path("data/processed/larridin")
    out_dir.mkdir(parents=True, exist_ok=True)

    companies = json.loads((snap_dir / "companies.json").read_text(encoding="utf-8"))
    pages = json.loads((snap_dir / "company_pages.json").read_text(encoding="utf-8"))

    # Best scores page per company: highest version among pages that carry aiScores.
    best_page: dict[str, dict] = {}
    page_meta: dict[str, dict] = {}
    for p in pages:
        cid = p["company_id"]
        has_scores = bool((p.get("content") or {}).get("aiScores"))
        meta = page_meta.setdefault(cid, {"n_pages": 0, "max_version": 0})
        meta["n_pages"] += 1
        meta["max_version"] = max(meta["max_version"], p.get("version") or 0)
        if not has_scores:
            continue
        cur = best_page.get(cid)
        if cur is None or (p.get("version") or 0) > (cur.get("version") or 0):
            best_page[cid] = p

    # Dedupe companies by exact name.
    dedup_log: list[dict] = []
    by_name: dict[str, dict] = {}
    for c in companies:
        name = c["name"].strip()
        if name == "Test Company":
            dedup_log.append({"action": "drop_test_row", "name": name, "id": c["id"]})
            continue
        prev = by_name.get(name)
        if prev is None:
            by_name[name] = c
            continue

        def score_recency(row: dict) -> str:
            bp = best_page.get(row["id"])
            return (bp or {}).get("created_at") or row.get("created_at") or ""

        keep, drop = (c, prev) if score_recency(c) > score_recency(prev) else (prev, c)
        by_name[name] = keep
        dedup_log.append(
            {"action": "drop_duplicate_name", "name": name, "id": drop["id"], "kept_id": keep["id"]}
        )

    clean = pd.DataFrame(
        [
            {
                "company_id": c["id"],
                "name": c["name"].strip(),
                "slug": c.get("slug"),
                "sector": c.get("sector"),
                "website": c.get("website"),
                "created_at": c.get("created_at"),
                "n_pages": page_meta.get(c["id"], {}).get("n_pages", 0),
            }
            for c in by_name.values()
        ]
    ).sort_values("name")

    score_rows = []
    for cid in clean["company_id"]:
        page = best_page.get(cid)
        row = {"company_id": cid}
        if page is not None:
            row.update(
                {"page_version": page.get("version"), "page_created_at": page.get("created_at")}
            )
            row.update(flatten_ai_scores(page.get("content") or {}))
        score_rows.append(row)
    scores = clean.merge(pd.DataFrame(score_rows), on="company_id", how="left")

    clean.to_parquet(out_dir / "companies_clean.parquet", index=False)
    clean.to_csv(out_dir / "companies_clean.csv", index=False)
    scores.to_parquet(out_dir / "scores_flat.parquet", index=False)
    scores.to_csv(out_dir / "scores_flat.csv", index=False)
    pd.DataFrame(dedup_log).to_csv(out_dir / "dedup_log.csv", index=False)

    print(f"snapshot: {snap_dir}")
    print(f"companies raw={len(companies)} clean={len(clean)} dropped={len(dedup_log)}")
    print(f"with aiScores: {scores['maturity_index'].notna().sum()}/{len(scores)}")
    print(f"\nscore summary:\n{scores[['adoption_score','proficiency_score','impact_score','maturity_index']].describe().round(2)}")
    print(f"\nsector coverage:\n{scores.groupby('sector')['maturity_index'].agg(['count','mean']).round(2)}")
    print(f"\noutputs -> {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
