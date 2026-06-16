# Responsible AI and Research Risks

This repository is a reproducible research system for testing whether AI adoption signals predict future company performance. LLM extraction is an enrichment POC and must remain evidence-first, auditable, and separable from sponsor-provided canonical scores.

## Reliability Risks

LLM outputs can vary by model, prompt, source language, sampling parameters, and document quality. Every extraction must preserve model_name, prompt_version, schema_version, evidence, confidence, created_at, and limitations so changes can be audited.

Models may hallucinate specific AI programs, infer maturity from promotional language, or overstate the importance of generic mentions. The extraction prompt and schema require null scores when evidence is insufficient.

## Disclosure Bias

Companies that disclose more AI activity may appear more advanced than companies that adopt AI quietly. Large-cap technology and communication-services companies may also have richer public disclosures than smaller or less public-facing firms.

Research analysis should treat LLM-derived features as noisy disclosure signals unless validated against independent source data.

Phase 14 includes a disclosure-bias proxy interface. When source document counts, filing lengths, or other disclosure-volume fields are unavailable, the diagnostic skips gracefully and records that limitation rather than inventing a proxy.

## Copyright and Source Handling

The system should store short evidence spans only. Do not store full copyrighted articles, transcripts, filings, or web pages in outputs unless the project has explicit permission and a data governance basis.

Sample files in this repository must be synthetic or clearly public-domain/open data. Proprietary Larridin raw data and private sponsor documents must not be committed.

## Security and Secrets

Do not commit API keys, tokens, service-account files, private endpoints, credentials, or raw proprietary datasets. Use environment variables and `.env` files for local configuration, and keep `.env` ignored by git.

LLM prompts and extraction outputs should not include credentials or confidential business information. Tests must run offline and must not require a real API key.

## Research Misuse

The system must not present findings as investment advice, automated trading instructions, or causal proof. Quantitative outputs describe associations under documented assumptions and should include limitations, sample sizes, and timing rules.

## Look-Ahead and Timing Risk

LLM-derived features are model features only if they have a defensible source_date and extraction_created_at or available_at timestamp. Panel construction must not use documents that were unavailable at prediction time.

If source timing is ambiguous, downstream panel logic should flag the row and exclude it in strict mode.

## Human Review

Ticker-level reports should show evidence and uncertainty notes beside any LLM-derived signal. Low-confidence signals, duplicated evidence, unsupported scores, or surprising outputs require human review before publication or sponsor-facing use.

## Robustness and Fairness Boundaries

Sector-neutral IC, size buckets, missingness diagnostics, lag sensitivity, and LLM reliability checks are responsible research diagnostics. They can reveal fragility or data-quality concerns, but they do not prove fairness, remove bias, or establish that AI adoption caused company performance.

If robustness checks disagree with baseline results, sponsor-facing summaries should present the disagreement plainly and avoid selective reporting.

## Real API Integration Guardrails

Future real LLM clients should:

- use deterministic settings where practical
- version prompts and schemas
- log model names and response metadata
- validate every response with Pydantic
- retry only on transport or schema-repairable failures
- never silently coerce invalid score ranges
- preserve raw response references in secure local or governed storage when allowed
