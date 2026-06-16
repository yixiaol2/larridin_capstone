"""Classify collected Exa job-posting results with the validated jobclass prompt,
then aggregate to a per-company AI hiring signal.

Input:  data/raw/exa/<snapshot>/jobs_*.json (from collect_hiring_exa.py)
Per-company predictions cached in data/processed/hiring/<snapshot>/preds/<ticker>.json
(idempotent resume). Final outputs:
  data/processed/hiring/<snapshot>/postings_classified.parquet
  data/processed/hiring/<snapshot>/company_hiring_signal.parquet (+.csv)

Usage:
    python scripts/classify_hiring_postings.py --snapshot 2026-06 [--limit N] [--model M]
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
BATCH_SIZE = 25
PROMPT_PATH = Path("src/ai_impact_research/llm/prompts/job_posting_classification.md")
VALID_TYPES = {"ai-builder", "ai-user", "ai-leader", "non-ai"}


def load_system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return re.sub(r"```yaml.*?```\n", "", text, count=1, flags=re.S)


def call_openrouter(model: str, system: str, user: str, key: str) -> tuple[list[dict], dict]:
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
            "max_tokens": 6000,
        },
        timeout=240,
    )
    r.raise_for_status()
    d = r.json()
    text = d["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text), d.get("usage", {})


def build_user_message(company: str, ticker: str, snapshot: str, chunk: list[dict]) -> str:
    lines = [f"TARGET COMPANY: {company} (ticker: {ticker})", f"SNAPSHOT MONTH: {snapshot}", "", "RESULTS:"]
    for i, res in enumerate(chunk):
        snippet = " ... ".join(res.get("highlights") or [])[:900] or "(not available)"
        lines += [
            f"[{i}] title: {res.get('title') or '(none)'}",
            f"    url: {res.get('url') or ''}",
            f"    published: {str(res.get('published_date'))[:10]}",
            f"    snippet: {snippet}",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    key = os.environ["OPENROUTER_API_KEY"]
    system = load_system_prompt()

    files = sorted(glob.glob(f"data/raw/exa/{args.snapshot}/jobs_*.json"))
    if args.limit:
        files = files[: args.limit]
    preds_dir = Path(f"data/processed/hiring/{args.snapshot}/preds")
    preds_dir.mkdir(parents=True, exist_ok=True)

    usage_in = usage_out = 0
    n_done = n_skip = n_fail = 0
    for fp in files:
        doc = json.loads(Path(fp).read_text())
        ticker = doc["ticker"]
        out_path = preds_dir / f"{ticker.replace('.', '-')}.json"
        if out_path.exists():
            n_skip += 1
            continue
        rows: list[dict] = []
        ok = True
        results = doc["results"]
        for start in range(0, len(results), BATCH_SIZE):
            chunk = results[start : start + BATCH_SIZE]
            user = build_user_message(doc["company"], ticker, args.snapshot, chunk)
            try:
                out, usage = call_openrouter(args.model, system, user, key)
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {ticker} @{start}: {e}")
                ok = False
                break
            usage_in += usage.get("prompt_tokens", 0)
            usage_out += usage.get("completion_tokens", 0)
            for o in out:
                idx = o.get("result_index")
                if idx is None or idx >= len(chunk):
                    continue
                t = o.get("ai_role_type")
                rows.append(
                    {
                        "url": chunk[idx].get("url"),
                        "title": chunk[idx].get("title"),
                        "published_date": chunk[idx].get("published_date"),
                        "is_company_match": bool(o.get("is_company_match")),
                        "ai_role_type": t if t in VALID_TYPES else ("non-ai" if t else None),
                        "seniority": o.get("seniority"),
                        "ai_requirement_strength": o.get("ai_requirement_strength"),
                        "confidence": o.get("confidence"),
                        "evidence": o.get("evidence"),
                    }
                )
            time.sleep(0.2)
        if not ok:
            n_fail += 1
            continue
        out_path.write_text(
            json.dumps(
                {"ticker": ticker, "company": doc["company"], "snapshot": args.snapshot,
                 "model": args.model, "prompt_version": "jobclass-v1",
                 "classified_at": dt.datetime.now(dt.UTC).isoformat(), "postings": rows},
                ensure_ascii=False,
            )
        )
        n_done += 1
        if n_done % 50 == 0:
            est = usage_in / 1e6 * 1 + usage_out / 1e6 * 5
            print(f"  {n_done} companies classified, tokens {usage_in}/{usage_out} (~${est:.2f})")

    # aggregate everything present
    all_rows, agg = [], []
    for pf in sorted(preds_dir.glob("*.json")):
        d = json.loads(pf.read_text())
        for p in d["postings"]:
            all_rows.append({"ticker": d["ticker"], "company": d["company"], **p})
        dfp = pd.DataFrame(d["postings"])
        matched = dfp[dfp["is_company_match"]] if len(dfp) else dfp
        counts = matched["ai_role_type"].value_counts() if len(matched) else {}
        n_b = int(counts.get("ai-builder", 0))
        n_u = int(counts.get("ai-user", 0))
        n_l = int(counts.get("ai-leader", 0))
        n_m = int(len(matched))
        agg.append(
            {
                "ticker": d["ticker"], "company": d["company"], "snapshot": d["snapshot"],
                "n_results": len(dfp), "n_matched": n_m,
                "n_ai_builder": n_b, "n_ai_user": n_u, "n_ai_leader": n_l,
                "builder_rate": n_b / n_m if n_m else None,
                "ai_rate": (n_b + n_u + n_l) / n_m if n_m else None,
            }
        )

    out_root = Path(f"data/processed/hiring/{args.snapshot}")
    pd.DataFrame(all_rows).to_parquet(out_root / "postings_classified.parquet", index=False)
    sig = pd.DataFrame(agg)
    sig.to_parquet(out_root / "company_hiring_signal.parquet", index=False)
    sig.to_csv(out_root / "company_hiring_signal.csv", index=False)

    est = usage_in / 1e6 * 1 + usage_out / 1e6 * 5
    print(f"\ndone={n_done} skipped={n_skip} failed={n_fail}")
    print(f"tokens {usage_in} in / {usage_out} out  (~${est:.2f} this run)")
    print(f"companies aggregated: {len(sig)}")
    if len(sig):
        print(f"\nbuilder_rate summary:\n{sig['builder_rate'].describe().round(3)}")
        print(f"\ntop10 by builder count:\n{sig.nlargest(10, 'n_ai_builder')[['company','n_matched','n_ai_builder','builder_rate']].to_string(index=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
