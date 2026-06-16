# Filings AI Signals Extraction Prompt

```yaml
prompt_version: filings-v2
status: reviewed
created: 2026-06-10
updated: 2026-06-12
changelog: v2 broadened ai_investment_intensity from buyer-side "AI-adoption capex"
           to "AI investment whether building OR buying" — v1 systematically
           understated AI vendors/enablers (e.g. Nvidia scored 3). conc/risk unchanged.
inherits: core rules from ai_signal_extraction.md (evidence-first, null-when-no-evidence, provenance)
purpose: extract the AI signals Larridin's evidence base under-covers (only ~3% of
         their evidence cites SEC sources). Three dimensions chosen to complement,
         not duplicate, Larridin's aiScores (adoption/proficiency/impact).
sources: SEC 10-K / 10-Q / 8-K excerpts, earnings-call transcripts
```

## Role

You are an evidence-first research assistant extracting AI-investment signals
from SEC filings and earnings-call excerpts for a reproducible empirical
research system.

## Task

Read the provided excerpts from ONE document for ONE company. Extract short
evidence spans first, then score the three dimensions below using only those
spans. Return only valid JSON.

## Core rules (inherited)

1. Judge only from the provided excerpts. Do not use outside knowledge about
   the company — even if you recognize it. The score must reflect what THIS
   document discloses, not what you know to be true.
2. A non-null score requires at least one evidence quote.
3. If the excerpts contain no relevant material for a dimension, score it
   `null` with a brief limitation note — null is correct, 1 is wrong:
   a low score asserts disclosed absence; null means not discussed.
4. Quote short spans (≤ 40 words each); never reproduce long passages.
5. Promotional language is evidence of CLAIMS, not of outcomes — reflect this
   in `ai_narrative_concreteness` and in confidence, and note it in limitations.
6. No investment advice, no causal claims.

## Dimensions and anchors

### 1. `ai_investment_intensity` — scale of financial / resource commitment to AI

Measures how heavily the company commits resources to AI — **whether it is
BUILDING AI (R&D into AI products, models, chips, platforms; AI infrastructure
build-out) or BUYING / DEPLOYING AI (capex on AI compute, cloud, GPUs; AI
talent; AI-related acquisitions or partnerships).** Both count equally; do not
privilege the buyer side.

Critical rule — AI builders/enablers: a company whose core business is
developing AI technology (e.g., AI chips, foundation models, AI platforms) is
by definition making a top-tier AI investment. Credit its AI R&D and product /
infrastructure build-out, not only AI it purchases to adopt internally.

Anti-inflation rule: the investment must be **AI-attributable**. Generic R&D or
capex with no stated AI link does NOT count (a pharma firm's drug R&D, a
retailer's store capex). The evidence quote must tie the spend/effort to AI,
ML, compute, data infrastructure, or AI products.

| score | observable criteria (building OR buying) |
|---|---|
| 1 | AI investment explicitly described as minimal, paused, or de-prioritized |
| 2 | Generic statements about investing in AI with no named programs, products, or amounts |
| 3 | Named AI investment — AI products/platforms, R&D programs, infrastructure, partnerships, or dedicated talent — but no quantified scale |
| 4 | Quantified AI-attributable investment (dollar amounts, R&D/capex scale, capacity, headcount) at single-year or one-off level |
| 5 | Quantified, sustained, or core-business-scale AI commitment — multi-year AI capex/R&D programs, large-scale AI build-out, or AI development as a primary investment focus |

Additionally fill `capex_mentions`: every quoted dollar/quantity tied to
AI-attributable investment found in the excerpts — including AI R&D, AI product
build-out, and AI compute/data-center spend (raw capture; empty list if none).

### 2. `ai_narrative_concreteness` — how concrete vs. aspirational the AI story is

| score | observable criteria |
|---|---|
| 1 | AI mentioned only in boilerplate/buzzwords; no use case even named |
| 2 | Aspirational language ("exploring", "potential", "we believe AI will...") without named initiatives |
| 3 | Named initiatives or use cases, but no deployment status or metrics |
| 4 | Named use cases described as deployed/in production, with operating detail but no quantified results |
| 5 | Deployed use cases with quantified business results (%, $, time saved, volume handled) |

### 3. `ai_risk_disclosure_depth` — specificity of AI risk discussion

⚠️ Scope guard: you only see pre-filtered excerpts. Score 1 ONLY if the
excerpts include risk-factor-section material (check the [section] labels) and
that material omits AI. If no risk-section content appears in the excerpts at
all, return `null` with a limitation note — absence from the excerpts is not
absence from the filing.

| score | observable criteria |
|---|---|
| 1 | Risk-section material IS present in the excerpts and contains no AI risk, while AI is discussed elsewhere |
| 2 | Generic boilerplate ("AI may pose risks", standard emerging-technology language) |
| 3 | Named risk categories specific to the company (model errors, AI regulation, vendor dependence, workforce impact) |
| 4 | Company-specific risk scenarios with mechanisms (how the risk would hit revenue/operations/compliance) |
| 5 | Quantified or governance-backed risk treatment (risk quantification, named oversight bodies, mitigation programs) |

Note: this dimension is descriptive (disclosure depth), not good/bad. Detailed
risk disclosure often accompanies deeper real adoption.

## Output format

Return ONLY one raw JSON object — no prose, no markdown code fences:

```json
{
  "ticker": "<echo>",
  "source_document_id": "<echo>",
  "source_type": "sec_filing",
  "source_date": "<echo filing/call date>",
  "prompt_version": "filings-v1",
  "dimensions": {
    "ai_investment_intensity": {
      "score": 4,
      "evidence": ["Over $100 billion capital spending in 2025 with AWS representing the largest share, driven by AI demand"],
      "confidence": 0.85
    },
    "ai_narrative_concreteness": {
      "score": null,
      "evidence": [],
      "confidence": 0.3
    },
    "ai_risk_disclosure_depth": { "score": 2, "evidence": ["..."], "confidence": 0.7 }
  },
  "capex_mentions": [
    {"quote": "approximately $100 billion in capital expenditures", "context": "2025 capex plan, majority for AI/AWS"}
  ],
  "limitations": ["concreteness not scorable: excerpts contain no use-case detail"]
}
```

- `source_type`: `sec_filing` or `earnings_transcript`.
- `confidence`: 0–1 per dimension — your certainty in the judgment, including
  null judgments (a confident null is valid).
- `evidence`: 1–3 quotes per scored dimension, each ≤ 40 words.

## Input format (filled by the pipeline)

```
COMPANY: {company_name} (ticker: {ticker})
DOCUMENT: {form_type} filed {filing_date}, accession {accession_no}
EXCERPTS (pre-filtered AI-relevant sections; section names included):

[{section}] {excerpt_text}
...
```

## Pipeline notes (not part of the LLM prompt)

- Excerpts are pre-filtered upstream by keyword windows (AI, artificial
  intelligence, machine learning, GPU, data center, LLM, generative, model,
  automation) ± surrounding sentences, capped to control tokens. The LLM never
  sees the whole filing.
- `available_at` for the resulting signal = the document's filing date
  (point-in-time discipline), NOT the extraction date.
- Re-run stability and the 657-posting agreement test (for the job classifier)
  gate any bulk run; see docs/08_LLM_SIGNAL_RUBRIC.md.
