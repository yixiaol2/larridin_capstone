"""Validate the job-posting classification prompt against Larridin's 657 labeled postings.

Ground truth: data/raw/larridin/<snap>/job_posting_extractions.json (their
ai_role_type labels). Input simulation: title + URL + first 500 chars of
raw_text, to approximate Exa snippet conditions (stricter than their full-text
pipeline — noted in the report).

Outputs predictions + agreement metrics; writes
data/processed/hiring/classifier_validation/predictions.csv

Usage:
    python scripts/validate_job_classifier.py [--max-batches N] [--model MODEL]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
BATCH_SIZE = 20
SNIPPET_CHARS = 500
PROMPT_PATH = Path("src/ai_impact_research/llm/prompts/job_posting_classification.md")
BOILERPLATE = re.compile(r"cookie|privacy|browser|sign in|navigation|advertis", re.I)


def make_snippet(raw_text: str, title: str) -> str:
    """Approximate an Exa-style snippet: strip boilerplate lines, prefer text
    starting at the job title occurrence, then truncate."""
    lines = [ln for ln in (raw_text or "").splitlines() if ln.strip() and not BOILERPLATE.search(ln)]
    text = " ".join(lines)
    if title:
        pos = text.lower().find(title.lower()[:30])
        if pos > 0:
            text = text[pos:]
    return text[:SNIPPET_CHARS]


def load_system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    # strip the yaml metadata fence (file header, not part of the LLM prompt)
    return re.sub(r"```yaml.*?```\n", "", text, count=1, flags=re.S)


def call_openrouter(model: str, system: str, user: str, key: str) -> tuple[str, dict]:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 4000,
        },
        timeout=180,
    )
    r.raise_for_status()
    d = r.json()
    return d["choices"][0]["message"]["content"], d.get("usage", {})


def parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    key = os.environ["OPENROUTER_API_KEY"]

    snap = sorted(Path("data/raw/larridin").iterdir())[-1]
    raw = {p["id"]: p for p in json.loads((snap / "job_postings_raw.json").read_text())}
    labels = json.loads((snap / "job_posting_extractions.json").read_text())
    comps = {c["id"]: c["name"] for c in json.loads((snap / "companies.json").read_text())}

    rows = []
    for ext in labels:
        p = raw.get(ext["posting_id"])
        if p is None:
            continue
        rows.append(
            {
                "posting_id": p["id"],
                "company": comps.get(p["company_id"], "?"),
                "title": p.get("title") or "",
                "url": p.get("url") or "",
                "snippet": make_snippet(p.get("raw_text") or "", p.get("title") or ""),
                "snapshot_month": p.get("snapshot_month"),
                "true_ai_role_type": ext.get("ai_role_type"),
                "true_seniority": ext.get("seniority"),
                "true_requirement_strength": ext.get("requirement_strength"),
            }
        )
    df = pd.DataFrame(rows)
    print(f"labeled postings joined: {len(df)} across {df['company'].nunique()} companies")

    system = load_system_prompt()
    preds: list[dict] = []
    usage_in = usage_out = 0
    n_batches = 0
    for company, grp in df.groupby("company"):
        grp = grp.reset_index(drop=True)
        for start in range(0, len(grp), BATCH_SIZE):
            if args.max_batches is not None and n_batches >= args.max_batches:
                break
            chunk = grp.iloc[start : start + BATCH_SIZE].reset_index(drop=True)
            lines = [f"TARGET COMPANY: {company} (ticker: n/a)",
                     f"SNAPSHOT MONTH: {chunk['snapshot_month'].iloc[0]}", "", "RESULTS:"]
            for i, r in chunk.iterrows():
                lines += [f"[{i}] title: {r['title']}", f"    url: {r['url']}",
                          f"    snippet: {r['snippet']}"]
            try:
                text, usage = call_openrouter(args.model, system, "\n".join(lines), key)
                out = parse_json_array(text)
            except Exception as e:  # noqa: BLE001 - report and continue
                print(f"  batch failed ({company} @{start}): {e}")
                continue
            usage_in += usage.get("prompt_tokens", 0)
            usage_out += usage.get("completion_tokens", 0)
            for o in out:
                idx = o.get("result_index")
                if idx is None or idx >= len(chunk):
                    continue
                preds.append(
                    {
                        "posting_id": chunk.loc[idx, "posting_id"],
                        "pred_company_match": o.get("is_company_match"),
                        "pred_ai_role_type": o.get("ai_role_type"),
                        "pred_seniority": o.get("seniority"),
                        "pred_requirement_strength": o.get("ai_requirement_strength"),
                        "pred_confidence": o.get("confidence"),
                        "pred_evidence": o.get("evidence"),
                    }
                )
            n_batches += 1
            time.sleep(0.3)
        if args.max_batches is not None and n_batches >= args.max_batches:
            break

    res = df.merge(pd.DataFrame(preds), on="posting_id", how="inner")
    out_dir = Path("data/processed/hiring/classifier_validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    res.to_csv(out_dir / "predictions.csv", index=False)

    print(f"\nmodel: {args.model} | batches: {n_batches} | predictions: {len(res)}")
    print(f"tokens: {usage_in} in / {usage_out} out")

    # company match sanity (all postings came from official careers crawls)
    print(f"\npred is_company_match=True: {(res['pred_company_match'] == True).mean():.1%}")  # noqa: E712

    # ai_role_type agreement (only where model said company-match)
    m = res[res["pred_company_match"] == True].copy()  # noqa: E712
    agree = (m["pred_ai_role_type"] == m["true_ai_role_type"]).mean()
    bin_true = m["true_ai_role_type"].ne("non-ai")
    bin_pred = m["pred_ai_role_type"].ne("non-ai")
    print(f"4-class agreement: {agree:.1%} (n={len(m)})")
    print(f"binary AI-vs-non agreement: {(bin_true == bin_pred).mean():.1%}")
    tp = (bin_true & bin_pred).sum()
    fp = (~bin_true & bin_pred).sum()
    fn = (bin_true & ~bin_pred).sum()
    print(f"binary AI precision: {tp / max(tp + fp, 1):.1%}  recall: {tp / max(tp + fn, 1):.1%}")
    print("\nconfusion (rows=truth, cols=pred):")
    print(pd.crosstab(m["true_ai_role_type"], m["pred_ai_role_type"]).to_string())
    print(f"\npredictions -> {out_dir / 'predictions.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
