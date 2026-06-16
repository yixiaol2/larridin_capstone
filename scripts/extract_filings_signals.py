"""Extract AI signals from latest 10-K filings using the filings-v1 prompt.

Pipeline per company: EDGAR submissions API -> latest 10-K -> text -> keyword
windows around AI terms (with rough section labels so the risk dimension's
scope guard works) -> Sonnet-class scoring -> JSON output.

Collection is free (SEC EDGAR, declared User-Agent); only the LLM call costs
money. Raw filing text cached under data/raw/edgar/10k/. Outputs under
data/processed/filings/<run>/.

Usage:
    python scripts/extract_filings_signals.py --pilot          # 12 stratified companies
    python scripts/extract_filings_signals.py --tickers MSFT,CAT
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

MODEL = "anthropic/claude-sonnet-4.6"
PROMPT_PATH = Path("src/ai_impact_research/llm/prompts/filings_ai_signals.md")
AI_TERMS = re.compile(
    r"\b(artificial intelligence|machine learning|generative ai|\bai\b|large language|llm|gpu|"
    r"data center|datacenter|neural|deep learning|automation|chatbot|copilot)\b",
    re.I,
)
WINDOW_CHARS = 600  # around each hit
MAX_EXCERPT_CHARS = 45000


def edgar_get(url: str, ua: str) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": ua}, timeout=60)
    r.raise_for_status()
    time.sleep(0.15)
    return r


def fetch_latest_10k_text(cik: str, ua: str, cache_dir: Path, ticker: str) -> tuple[str, dict]:
    cache = cache_dir / f"{ticker}.json"
    if cache.exists():
        d = json.loads(cache.read_text())
        return d["text"], d["meta"]
    subs = edgar_get(f"https://data.sec.gov/submissions/CIK{cik}.json", ua).json()
    recent = subs["filings"]["recent"]
    idx = next(
        (i for i, f in enumerate(recent["form"]) if f == "10-K"),
        None,
    )
    if idx is None:
        raise RuntimeError("no 10-K found")
    accession = recent["accessionNumber"][idx].replace("-", "")
    primary = recent["primaryDocument"][idx]
    filing_date = recent["filingDate"][idx]
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}"
    html = edgar_get(url, ua).text
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    meta = {"accession": recent["accessionNumber"][idx], "filing_date": filing_date, "url": url}
    cache.write_text(json.dumps({"text": text, "meta": meta}))
    return text, meta


def section_label(text: str, pos: int) -> str:
    """Rough section label: nearest preceding 'Item N' heading."""
    window = text[max(0, pos - 200000) : pos].lower()
    items = re.findall(r"item\s+(\d+a?b?)[\.\s]", window)
    if not items:
        return "other"
    last = items[-1]
    if last == "1a":
        return "risk_factors"
    if last in ("7", "7a"):
        return "mdna"
    if last == "1":
        return "business"
    return f"item_{last}"


def build_excerpts(text: str) -> list[tuple[str, str]]:
    out, spans = [], []
    for m in AI_TERMS.finditer(text):
        start, end = max(0, m.start() - WINDOW_CHARS), min(len(text), m.end() + WINDOW_CHARS)
        if spans and start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], end)
        else:
            spans.append((start, end))
    total = 0
    for s, e in spans:
        chunk = text[s:e].strip()
        if total + len(chunk) > MAX_EXCERPT_CHARS:
            break
        out.append((section_label(text, s), chunk))
        total += len(chunk)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--all", action="store_true", help="full universe (companies with CIK)")
    parser.add_argument("--tickers", default=None)
    parser.add_argument("--run-name", default="pilot")
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")
    ua = os.environ["SEC_USER_AGENT"]
    key = os.environ["OPENROUTER_API_KEY"]
    system = re.sub(r"```yaml.*?```\n", "", PROMPT_PATH.read_text(), count=1, flags=re.S)

    cx = pd.read_parquet("data/processed/analysis_crosssection.parquet")
    cx = cx[cx["cik"].notna() & cx["maturity_index"].notna()]
    if args.all:
        sel = cx
    elif args.tickers:
        sel = cx[cx["ticker"].isin(args.tickers.split(","))]
    else:  # stratified pilot: 4 high / 4 mid / 4 low maturity, sector-spread
        hi = cx[cx["maturity_index"] >= 4.5].drop_duplicates("sector_larridin").head(4)
        mid = cx[(cx["maturity_index"] >= 3) & (cx["maturity_index"] < 4)].drop_duplicates("sector_larridin").head(4)
        lo = cx[cx["maturity_index"] <= 2.5].drop_duplicates("sector_larridin").head(4)
        sel = pd.concat([hi, mid, lo])
    print(f"selected {len(sel)}: {sel['ticker'].tolist()}")

    cache_dir = Path("data/raw/edgar/10k")
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(f"data/processed/filings/{args.run_name}")
    out_dir.mkdir(parents=True, exist_ok=True)

    usage_in = usage_out = 0
    for _, row in sel.iterrows():
        out_path = out_dir / f"{row.ticker.replace('.', '-')}.json"
        if out_path.exists():
            continue
        try:
            text, meta = fetch_latest_10k_text(str(row["cik"]).zfill(10), ua, cache_dir, row.ticker)
            excerpts = build_excerpts(text)
        except Exception as e:  # noqa: BLE001
            print(f"  FETCH FAIL {row.ticker}: {e}")
            continue
        if not excerpts:
            print(f"  {row.ticker}: no AI-relevant excerpts in 10-K")
            out_path.write_text(json.dumps({"ticker": row.ticker, "no_excerpts": True, "meta": meta}))
            continue
        user_lines = [
            f"COMPANY: {row['name']} (ticker: {row.ticker})",
            f"DOCUMENT: 10-K filed {meta['filing_date']}, accession {meta['accession']}",
            "EXCERPTS (pre-filtered AI-relevant sections; section names included):", "",
        ]
        for sec, chunk in excerpts:
            user_lines.append(f"[{sec}] {chunk}")
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": MODEL,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": "\n".join(user_lines)}],
                      "temperature": 0, "max_tokens": 3000},
                timeout=300,
            )
            r.raise_for_status()
            d = r.json()
            raw = d["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
            parsed = json.loads(raw)
            usage_in += d.get("usage", {}).get("prompt_tokens", 0)
            usage_out += d.get("usage", {}).get("completion_tokens", 0)
        except Exception as e:  # noqa: BLE001
            print(f"  LLM FAIL {row.ticker}: {e}")
            continue
        parsed["_meta"] = {**meta, "model": MODEL, "n_excerpts": len(excerpts),
                           "maturity_index": float(row["maturity_index"]),
                           "extracted_at": dt.datetime.now(dt.UTC).isoformat()}
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=1))
        dims = parsed.get("dimensions", {})
        scores = {k: (v or {}).get("score") for k, v in dims.items()}
        print(f"  {row.ticker} (maturity {row['maturity_index']}): {scores}")

    est = usage_in / 1e6 * 3 + usage_out / 1e6 * 15
    print(f"\ntokens {usage_in}/{usage_out} (~${est:.2f}) | outputs -> {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
