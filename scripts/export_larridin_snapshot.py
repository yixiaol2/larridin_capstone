"""Export a read-only snapshot of Larridin's Supabase project to local files.

Read-only by construction: only HTTP GET requests are issued. Writes go to
data/raw/larridin/<date>/ (raw JSON per table, plus a manifest) — never to the
remote database.

Self-contained on purpose (requests + stdlib only): the local conda env runs
Python 3.10 while the package targets >=3.11, and the existing
ingestion/larridin.py is written for the old assumed CSV schema. Revisit and
fold into the package when the env is upgraded.

Usage:
    python scripts/export_larridin_snapshot.py [--out-root data/raw/larridin]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

TABLES = [
    "agent_completion",
    "ai_tool_agent_completions",
    "ai_tool_company",
    "ai_tool_customers",
    "ai_tool_raw_sources",
    "ai_tool_security",
    "ai_tool_tag_assignments",
    "ai_tool_tags",
    "ai_tool_traction",
    "ai_tools",
    "changelogs",
    "companies",
    "company_pages",
    "job_posting_extractions",
    "job_postings_raw",
    "pipeline_state",
    "research_snapshots",
    "research_sources",
    "synthesis_runs",
    "synthesis_sources",
    "workforce_snapshots",
]

PAGE_SIZE = 1000


def fetch_table(base_url: str, headers: dict, table: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        resp = requests.get(
            f"{base_url}/rest/v1/{table}",
            headers={**headers, "Range": f"{start}-{start + PAGE_SIZE - 1}"},
            params={"select": "*"},
            timeout=120,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not isinstance(batch, list):
            raise RuntimeError(f"{table}: unexpected response {str(batch)[:200]}")
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", default="data/raw/larridin")
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    base_url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not base_url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env", file=sys.stderr)
        return 1
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    snapshot_date = dt.date.today().isoformat()
    out_dir = Path(args.out_root) / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "supabase_url": base_url,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tables": {},
    }
    for table in TABLES:
        rows = fetch_table(base_url, headers, table)
        path = out_dir / f"{table}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        manifest["tables"][table] = {"rows": len(rows), "file": path.name}
        print(f"{table:28s} {len(rows):>6d} rows -> {path}")

    (out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {out_dir / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
