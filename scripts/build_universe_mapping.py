"""Build the study universe: Larridin companies ∪ S&P 500, with ticker/CIK mapping.

Sources:
- data/processed/larridin/companies_clean.parquet (local, from flatten step)
- Wikipedia "List of S&P 500 companies" (Symbol, Security, GICS sector, CIK)
- SEC company_tickers.json (ticker -> CIK, formal title) for non-S&P matches

Matching: normalized-name exact match against S&P names first, then SEC titles,
then a conservative fuzzy pass (difflib >= 0.92) flagged for manual review.
Unmatched rows go to unmatched_larridin.csv for a manual pass — do NOT silently
drop them.

Output: data/processed/universe/universe.parquet (+.csv), unmatched_larridin.csv

Usage:
    python scripts/build_universe_mapping.py
"""

from __future__ import annotations

import difflib
import os
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

SUFFIXES = (
    "incorporated|inc|corporation|corp|company|co|plc|ltd|llc|lp|sa|nv|se|ag|"
    "group|holdings|holding|the"
)

# Name-variant publics the auto-matcher misses, plus fixes for bad fuzzy hits.
# Possibly-delisted names still get their ticker here — the price-pull step
# validates and downgrades tickers with no 2026 price data (don't trust memory
# of corporate actions; let the data decide).
MANUAL_TICKERS = {
    "Alphabet Inc.": "GOOGL",
    "News Corp": "NWSA",
    "AMD": "AMD",
    "Albertsons": "ACI",
    "BJ's Wholesale": "BJ",
    "Burlington": "BURL",
    "Campbell Company": "CPB",
    "Coterra": "CTRA",
    "Dayforce": "DAY",
    "Eli Lilly": "LLY",
    "Foot Locker": "FL",
    "Hologic": "HOLX",
    "Interpublic Group of Companies": "IPG",
    "Kellanova": "K",
    "Kohl's": "KSS",
    "Lowes": "LOW",
    "Lululemon": "LULU",
    "Nordstrom": "JWN",
    "Office Depot": "ODP",
    "Paycom": "PAYC",
    "Petco": "WOOF",
    "PNC Financial": "PNC",
    "Rite Aid": "RAD",
    "UPS": "UPS",
    "Walgreens": "WBA",
    "Walgreens Boots Alliance": "WBA",
}

# Privately held companies or subsidiaries — no listed equity to analyze.
PRIVATE_OR_SUBSIDIARY = {
    "Aldi": "private",
    "Big Lots": "private (post-bankruptcy)",
    "H-E-B": "private",
    "IKEA": "private",
    "JCPenney": "private",
    "Michaels": "private",
    "PetSmart": "private",
    "Publix": "private",
    "Safeway": "subsidiary of Albertsons",
    "Sam's Club": "subsidiary of Walmart",
    "Staples": "private",
    "Trader Joe's": "private",
    "Wegmans": "private",
    "Whole Foods": "subsidiary of Amazon",
}


def normalize(name: str) -> str:
    s = name.lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"[\.,'’\-()]", " ", s)
    s = re.sub(rf"\b({SUFFIXES})\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> int:
    load_dotenv(dotenv_path=".env")
    ua = os.environ.get("SEC_USER_AGENT", "research contact@example.edu")
    out_dir = Path("data/processed/universe")
    out_dir.mkdir(parents=True, exist_ok=True)

    larridin = pd.read_parquet("data/processed/larridin/companies_clean.parquet")

    # S&P 500 constituents (Wikipedia table includes CIK).
    html = requests.get(WIKI_URL, headers={"User-Agent": ua}, timeout=60).text
    sp500 = next(t for t in pd.read_html(StringIO(html)) if "Symbol" in t.columns)
    sp500 = sp500.rename(
        columns={"Symbol": "ticker", "Security": "sp500_name", "GICS Sector": "gics_sector", "CIK": "cik"}
    )[["ticker", "sp500_name", "gics_sector", "cik"]]
    sp500["cik"] = sp500["cik"].astype(str).str.zfill(10)
    sp500["norm"] = sp500["sp500_name"].map(normalize)

    # SEC full ticker->CIK registry (covers non-S&P names).
    sec = pd.DataFrame(
        requests.get(SEC_TICKERS_URL, headers={"User-Agent": ua}, timeout=60).json().values()
    ).rename(columns={"cik_str": "cik", "title": "sec_title"})
    sec["cik"] = sec["cik"].astype(str).str.zfill(10)
    sec["norm"] = sec["sec_title"].map(normalize)
    # One row per normalized name. company_tickers.json is ordered with primary
    # listings first, so keep first occurrence — do NOT re-sort (an unstable
    # sort here once mapped Alphabet to the secondary listing GGLAP).
    sec_by_norm = sec.drop_duplicates("norm")

    larridin["norm"] = larridin["name"].map(normalize)

    sp_by_norm = sp500.drop_duplicates("norm").set_index("norm")
    sec_idx = sec_by_norm.set_index("norm")

    rows, unmatched = [], []
    for _, c in larridin.iterrows():
        row = {
            "company_id": c["company_id"],
            "name": c["name"],
            "sector_larridin": c["sector"],
            "in_larridin": True,
        }
        if c["name"] in PRIVATE_OR_SUBSIDIARY:
            row.update(ticker=None, cik=None, gics_sector=None, in_sp500=False,
                       match_method=f"private:{PRIVATE_OR_SUBSIDIARY[c['name']]}")
        elif c["name"] in MANUAL_TICKERS:
            t = MANUAL_TICKERS[c["name"]]
            sp_hit = sp500[sp500["ticker"] == t]
            sec_hit = sec[sec["ticker"] == t]
            cik = (sp_hit["cik"].iloc[0] if len(sp_hit)
                   else (sec_hit["cik"].iloc[0] if len(sec_hit) else None))
            gics = sp_hit["gics_sector"].iloc[0] if len(sp_hit) else None
            row.update(ticker=t, cik=cik, gics_sector=gics, in_sp500=bool(len(sp_hit)),
                       match_method="manual")
        elif c["norm"] in sp_by_norm.index:
            m = sp_by_norm.loc[c["norm"]]
            row.update(ticker=m["ticker"], cik=m["cik"], gics_sector=m["gics_sector"],
                       in_sp500=True, match_method="sp500_exact")
        elif c["norm"] in sec_idx.index:
            m = sec_idx.loc[c["norm"]]
            row.update(ticker=m["ticker"], cik=m["cik"], gics_sector=None,
                       in_sp500=False, match_method="sec_exact")
        else:
            cand = difflib.get_close_matches(c["norm"], sp_by_norm.index.tolist(), n=1, cutoff=0.92)
            if cand:
                m = sp_by_norm.loc[cand[0]]
                row.update(ticker=m["ticker"], cik=m["cik"], gics_sector=m["gics_sector"],
                           in_sp500=True, match_method=f"sp500_fuzzy:{cand[0]}")
            else:
                cand = difflib.get_close_matches(c["norm"], sec_idx.index.tolist(), n=1, cutoff=0.92)
                if cand:
                    m = sec_idx.loc[cand[0]]
                    row.update(ticker=m["ticker"], cik=m["cik"], gics_sector=None,
                               in_sp500=False, match_method=f"sec_fuzzy:{cand[0]}")
                else:
                    row.update(ticker=None, cik=None, gics_sector=None,
                               in_sp500=False, match_method="unmatched")
                    unmatched.append({"name": c["name"], "norm": c["norm"], "sector": c["sector"]})
        rows.append(row)

    uni = pd.DataFrame(rows)
    # S&P 500 companies not covered by Larridin -> fill-in rows.
    matched_tickers = set(uni["ticker"].dropna())
    fill = sp500[~sp500["ticker"].isin(matched_tickers)]
    fill_rows = pd.DataFrame(
        {
            "company_id": None,
            "name": fill["sp500_name"],
            "sector_larridin": None,
            "in_larridin": False,
            "ticker": fill["ticker"],
            "cik": fill["cik"],
            "gics_sector": fill["gics_sector"],
            "in_sp500": True,
            "match_method": "sp500_fill_in",
        }
    )
    uni = pd.concat([uni, fill_rows], ignore_index=True)

    # Same ticker mapped from multiple Larridin rows (e.g. "Walgreens" and
    # "Walgreens Boots Alliance") — flag so analysis keeps one row per ticker.
    uni["ticker_dup"] = uni["ticker"].notna() & uni.duplicated("ticker", keep=False)

    # Same company under multiple share classes (GOOGL/GOOG, FOXA/FOX, NWSA/NWS):
    # flag every row after the preferred one per CIK (prefer the Larridin row,
    # then first listed) so analysis keeps one row per company.
    uni = uni.sort_values(["cik", "in_larridin"], ascending=[True, False], kind="stable")
    uni["share_class_dup"] = uni["cik"].notna() & uni.duplicated("cik", keep="first")
    uni = uni.sort_index()

    uni.to_parquet(out_dir / "universe.parquet", index=False)
    uni.to_csv(out_dir / "universe.csv", index=False)
    pd.DataFrame(unmatched).to_csv(out_dir / "unmatched_larridin.csv", index=False)

    n_larridin = int(uni["in_larridin"].sum())
    print(f"universe total: {len(uni)}")
    print(f"  larridin matched: {n_larridin - len(unmatched)}/{n_larridin}  (unmatched -> unmatched_larridin.csv)")
    print(f"  of which in S&P 500: {int((uni['in_larridin'] & uni['in_sp500']).sum())}")
    print(f"  S&P 500 fill-ins:  {len(fill_rows)}")
    print("match methods:", uni["match_method"].str.split(":").str[0].value_counts().to_dict())
    fz = uni[uni["match_method"].str.contains("fuzzy", na=False)][["name", "ticker", "match_method"]]
    if len(fz):
        print(f"\nfuzzy matches to eyeball:\n{fz.to_string(index=False)}")
    print(f"\noutputs -> {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
