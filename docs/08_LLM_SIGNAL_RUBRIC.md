# LLM Signal Rubric

> ⚠️ **The active prompts are the versioned files**, not this doc: `src/ai_impact_research/llm/prompts/job_posting_classification.md` (hiring) and `filings_ai_signals.md` (filings, version filings-v2). This remains the original POC rubric for context — see [`HANDOFF.md`](../HANDOFF.md).

This POC extracts AI adoption evidence from unstructured public documents. It is designed to enrich research features, not to replace the canonical Larridin scores or produce standalone conclusions.

## Evidence-First Workflow

1. Parse a source document with stable provenance: source_document_id, source_type, source_date, company_id or ticker.
2. Extract short evidence spans that directly mention AI-related activity, hiring, infrastructure, training, or claimed impact.
3. Map the evidence to structured signal judgments.
4. Assign 1-5 scores only when the evidence supports a dimension.
5. Return null for a score when the document does not provide enough evidence.
6. Store prompt_version, schema_version, model_name, confidence, extraction_created_at, and limitations.

The model must not directly invent a total company score. Composite research features should be computed downstream from validated structured fields.

## Supported Source Types

- sec_filing
- earnings_transcript
- job_posting
- news_article
- company_web_page

## Signal Dimensions

| Signal | Description |
|---|---|
| ai_strategy_specificity | Specificity of AI strategy, roadmap, named initiatives, ownership, or execution plans. |
| ai_operational_maturity | Degree to which AI appears exploratory, piloted, productionized, or scaled across workflows. |
| ai_workforce_training | Evidence of AI fluency, training, upskilling, governance training, or responsible-use enablement. |
| ai_hiring_intensity | Evidence of AI, machine learning, data science, model operations, or AI infrastructure hiring demand. |
| ai_capex_or_infrastructure_signal | Evidence of AI-related cloud, GPU, data center, model platform, data infrastructure, or capex investment. |
| ai_productivity_claim | Evidence that AI is claimed to improve productivity, automation, revenue, margin, cycle time, quality, or cost. |

## Job Posting Sampling Notes

Job postings are useful for `ai_hiring_intensity`, but they are noisy. A posting can indicate hiring demand, vendor implementation, compliance work, or ordinary technical hiring depending on context.

The Phase 11 framework uses deterministic keyword matching before any LLM enrichment. Matching terms include artificial intelligence, machine learning, generative AI, LLM, NLP, computer vision, data scientist, ML engineer, prompt engineer, AI product, AI platform, and automation engineer.

Sampled postings are grouped into:

- `ai_keyword_matched`
- `technical_non_ai`
- `non_technical`
- `leadership_strategy`

LLM extraction from sampled job postings must still quote short evidence spans, preserve source_document_id or job_posting_id provenance, and return null for any signal dimension not supported by the posting text.

## 1-5 Anchors

| Score | Anchor | Interpretation |
|---|---|---|
| 1 | Minimal or negative | Explicit evidence of no meaningful activity, cancellation, or very limited exploration. |
| 2 | Vague exploration | Generic statements, awareness, or early exploration without named use cases. |
| 3 | Pilot or limited use | Named pilots, limited deployments, or credible function-level initiatives. |
| 4 | Production use | Production deployment in one or more functions with operating detail, governance, or repeatable workflow evidence. |
| 5 | Scaled transformation | Enterprise-scale transformation with measurable outcomes, resourcing, infrastructure, and a repeatable operating model. |

If the evidence is absent or too ambiguous, the score must be null, not 1.

## Required Provenance

Every extraction must preserve:

- company_id or ticker
- source_document_id
- source_type
- source_date
- extraction_created_at
- model_name
- prompt_version
- schema_version
- short evidence spans
- evidence references for every non-null score
- confidence for every signal
- limitations or uncertainty notes

## Quality Checks

The evaluation helpers report:

- schema validity rate
- evidence coverage rate
- missing score rate
- confidence distribution
- duplicate evidence detection

Low evidence coverage, high missing score rates, repeated evidence, or low confidence should trigger human review before the fields are used in research analysis.
