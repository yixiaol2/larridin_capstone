# 分阶段搭建代码库的 Prompt Pack

> **Historical record — not a current map of the repo.** This is the original phased build prompt-pack used to scaffold the project (via Codex). The file names, doc numbers, and page names in the prompts below reflect the *plan at build time* and have drifted from the final repo — e.g., the data dictionary is `04_DATA_DICTIONARY.md`, backtesting methodology is `05_BACKTESTING_METHODOLOGY.md`, the LLM rubric is now `08_LLM_SIGNAL_RUBRIC.md`, and the dashboard ships five pages (Overview / Company Explorer / Signal Analysis / Backtest / Methodology). For the current structure, see `README.md` and `CLAUDE.md`; do not treat the paths inside this file as current.

下面的 prompts 设计给 Cursor、Claude Code、ChatGPT coding agent 或 Windsurf 使用。建议按阶段逐条粘贴，不要一次性让模型做完整系统。每个阶段都要求模型先读当前 repo，再最小改动地实现，避免生成无法集成的大段代码。

## 全局约束 Prompt：每个阶段前都先粘贴

```text
你是这个 repo 的 senior data/ML engineer。项目是 Larridin × CMU AI Capstone：验证 AI adoption signals 是否能预测公司未来表现。请严格遵守以下约束：

1. 这是 research-grade pipeline，不是单纯 dashboard。
2. 所有 feature 必须保留 source、snapshot_date、available_at，避免 look-ahead bias。
3. 不要提交真实 API key、真实 sponsor 私有数据、PII 或数据库密码。
4. 优先写可测试、可复现的小模块；不要把业务逻辑塞进 notebook 或 Streamlit 页面。
5. 每次修改后更新相关 docs，并补充或修改 tests。
6. 任何 backtest 输出都必须标注为 hypothetical research result，不是 investment advice。
7. 保持现有目录结构：src/ 放 package，scripts/ 放入口，docs/ 放文档，infra/ 放 schema，tests/ 放测试。
8. 先给出实现计划和要修改的文件列表，再开始改代码。
```

---

## Phase 0 — Repo audit 与技术设计冻结

```text
请先完整阅读当前代码库，输出一份 repo audit：

目标：
- 确认当前文件结构是否适合 AI adoption signal → company performance research pipeline。
- 检查是否已有 companies、scores、market_data、financials、analytic_panel、analysis、dashboard、llm、agent 模块。
- 找出缺失模块、重复模块、命名不一致、潜在 look-ahead bias 风险。

请输出：
1. 当前 repo 结构摘要。
2. 推荐的最终架构。
3. P0/P1/P2 开发任务列表。
4. 需要立刻修复的技术债。
5. 本阶段不要写代码，除非发现明显的 README 或 doc typo。
```

验收标准：得到一份可执行的 backlog；团队确认 scope 后再进入 Phase 1。

---

## Phase 1 — 项目骨架、依赖、配置和 CI

```text
请实现项目基础工程骨架。

目标：
- 确保 repo 可以被新成员 clone 后快速运行。
- 配置 pyproject.toml、ruff、pytest、Makefile、.env.example、GitHub Actions。
- 建立 src/ai_impact_research/ package，并保证 pytest 可以跑通。

需要创建或修改：
- README.md
- pyproject.toml
- Makefile
- .env.example
- .gitignore
- .github/workflows/ci.yml
- src/ai_impact_research/__init__.py
- src/ai_impact_research/config.py
- tests/test_imports.py

技术要求：
- Python >= 3.11。
- 使用 pandas/numpy/scipy/statsmodels/streamlit/plotly/pydantic。
- 不要引入复杂 orchestration；先用 scripts + Makefile。
- 所有配置从 env 或 configs/base.yaml 读取。

验收标准：
- `make test` 通过。
- `make lint` 通过。
- README 包含 quick start。
```

---

## Phase 2 — 数据模型和数据库 schema

```text
请实现核心数据模型和 schema。

目标：
- 建立 company-quarter research panel 所需的最小表结构。
- 数据库 schema 先支持 Postgres，同时本地可以用 CSV / DuckDB 跑 smoke test。

需要创建或修改：
- infra/db_schema.sql
- docs/03_DATA_DICTIONARY.md
- src/ai_impact_research/db/connection.py
- src/ai_impact_research/db/schema.py 或 models.py
- tests/test_schema_contract.py

必须包含这些逻辑表：
- companies
- company_identifiers
- larridin_scores
- financial_metrics
- market_prices
- source_documents
- llm_extractions
- analytic_panel_snapshots
- model_runs
- backtest_results

关键字段：
- company_id
- ticker
- cik
- sector / industry
- snapshot_date
- fiscal_quarter
- available_at
- source_name
- source_url 或 source_path
- created_at

验收标准：
- schema 文件可被 Postgres 初始化。
- 文档解释每张表用途和关键字段。
- tests 至少校验核心字段存在。
```

---

## Phase 3 — Larridin score ingestion

```text
请实现 Larridin score ingestion 模块。

目标：
- 支持从 sponsor-provided CSV export 导入。
- 预留 API client，但不要假设真实 endpoint 已确定。
- 对 AI Adoption / Fluency / Impact / Hiring 四个 1–5 分数字段做严格校验。

需要创建或修改：
- src/ai_impact_research/ingestion/larridin.py
- scripts/ingest_larridin.py
- tests/test_larridin_ingestion.py
- docs/03_DATA_DICTIONARY.md

输入 CSV 最小字段：
- ticker
- company_name
- snapshot_date
- ai_adoption_score
- ai_fluency_score
- ai_impact_score
- ai_hiring_score
- source_url 或 source_name

实现要求：
- 标准化 ticker 大小写。
- score 必须是 1 到 5；非法值直接 raise ValueError。
- 保留 raw columns，不要丢掉 sponsor 原始字段。
- 输出 normalized DataFrame 或写入 DB 的 records。

验收标准：
- 可以读取 data/samples/larridin_scores.csv。
- 非法 score 测试会失败。
- ingestion 结果包含 available_at。
```

---

## Phase 4 — Public financial and market data ingestion

```text
请实现 public financial and market data ingestion 的接口层。

目标：
- 支持本地 CSV smoke test。
- 预留 Yahoo Finance / SEC EDGAR / vendor API adapter，但先不要把外部 API 调用写死到核心逻辑里。
- market data 和 fundamentals 都要带 available_at。

需要创建或修改：
- src/ai_impact_research/ingestion/market_data.py
- src/ai_impact_research/ingestion/financials.py
- scripts/ingest_market_data.py
- scripts/ingest_financials.py
- tests/test_financial_ingestion.py
- docs/03_DATA_SOURCES.md

Market data 最小字段：
- ticker
- price_date
- adjusted_close
- volume
- source_name
- available_at

Financial metrics 最小字段：
- ticker
- fiscal_quarter
- fiscal_period_end
- revenue
- operating_margin
- employee_count
- source_name
- available_at

验收标准：
- 可以读取 data/samples/market_prices.csv 和 fundamentals.csv。
- 同一 ticker / quarter 的重复记录可以被检测。
- 所有输出字段类型稳定。
```

---

## Phase 5 — Company-quarter analytical panel builder

```text
请实现 analytical panel builder。

目标：
- 将 companies、Larridin scores、financial metrics、market prices 合并成 company-quarter panel。
- 构造 forward outcomes：fwd_return_1q、revenue_growth_qoq、operating_margin_delta_qoq、revenue_per_employee。
- 显式避免 look-ahead bias。

需要创建或修改：
- src/ai_impact_research/processing/panel_builder.py
- scripts/build_panel.py
- tests/test_panel_builder.py
- docs/04_BACKTESTING_METHODOLOGY.md

实现要求：
- 一行 = company_id + score_quarter。
- features 使用 score_quarter 或之前可获得的数据。
- outcomes 使用 t+1 或后续季度。
- 对每个 outcome 标注 outcome_start_date / outcome_end_date。
- 记录 panel_snapshot_id 和 created_at。

验收标准：
- sample 数据能生成 data/processed/analytic_panel.csv。
- panel 没有重复 company_id + score_quarter。
- tests 覆盖 forward return 是否正确 shift。
```

---

## Phase 6 — IC、regression、backtest 分析层

```text
请实现 baseline research analysis。

目标：
- 对每个 AI signal 计算 Spearman IC。
- 实现 quintile portfolio backtest。
- 实现基础 OLS regression，支持 sector fixed effects 和 quarter fixed effects。

需要创建或修改：
- src/ai_impact_research/analysis/ic.py
- src/ai_impact_research/analysis/backtest.py
- src/ai_impact_research/analysis/regressions.py
- scripts/run_baseline_analysis.py
- tests/test_ic.py
- tests/test_backtest.py
- reports/interim_findings.md

分析输出：
- IC by quarter
- mean IC
- IC hit rate
- quintile returns
- Q5-Q1 long-short return
- regression coefficient table

验收标准：
- `make sample-analysis` 生成 reports/tables/*.csv。
- 空值和小样本时不会静默输出错误结论。
- 所有结果文件写入 metadata：run timestamp、input panel path、signal、outcome。
```

---

## Phase 7 — LLM signal extraction POC

```text
请实现 LLM-powered signal enrichment 的 POC。

目标：
- 对 SEC filing / earnings transcript / news / job posting 文本抽取结构化 AI evidence。
- 使用 Pydantic 或 JSON schema 强制输出格式。
- 先做 offline parser 和 schema validation；真实 LLM API 调用用 adapter 封装。

需要创建或修改：
- src/ai_impact_research/llm/schemas.py
- src/ai_impact_research/llm/extract.py
- src/ai_impact_research/llm/eval.py
- src/ai_impact_research/llm/prompts/ai_signal_extraction.md
- scripts/run_llm_extraction_poc.py
- tests/test_llm_schema.py
- docs/05_LLM_SIGNAL_RUBRIC.md

Schema 至少包含：
- company
- period
- source_type
- evidence_items[]
- signal_scores
- confidence
- model_name
- prompt_version

实现要求：
- 每个 score 必须有 evidence。
- 支持 binary evidence first，再 aggregation 到 1–5 score。
- 输出必须可追踪到 source_document_id。

验收标准：
- 给定 sample text，可以输出合法 JSON。
- 缺 evidence 的 score validation 失败。
- prompt 文件中包含 1–5 rubric 和 evidence requirement。
```

---

## Phase 8 — Streamlit dashboard

```text
请实现 dashboard v1。

目标：
- 让 sponsor 可以在本地或云端看见 coverage、company explorer、signal analysis、backtest。
- Dashboard 只读取已经构建好的 panel 和 results，不在页面里做重型数据处理。

需要创建或修改：
- src/ai_impact_research/dashboard/app.py
- src/ai_impact_research/dashboard/components.py
- src/ai_impact_research/dashboard/pages/1_Company_Explorer.py
- src/ai_impact_research/dashboard/pages/2_Signal_Analysis.py
- src/ai_impact_research/dashboard/pages/3_Backtest.py
- docs/06_DASHBOARD_SPEC.md

页面要求：
1. Overview：company count、quarter count、sector coverage、missingness。
2. Company Explorer：ticker 查询，展示 scores、financial metrics、peer rank。
3. Signal Analysis：score vs forward outcome、IC table。
4. Backtest：quintile returns、long-short curve。
5. Methodology caveat：不是 investment advice。

验收标准：
- `make dashboard` 可以启动。
- 无 data 文件时给出明确错误提示。
- 所有图表标题清楚，显示样本量。
```

---

## Phase 9 — Ticker-level research report agent

```text
请实现 ticker-level research report generator。

目标：
- 输入 ticker，自动整理公司 AI scores、财务表现、peer comparison、signal evidence、backtest context，并生成 narrative brief。
- 第一版可以 deterministic template，不需要复杂 multi-agent。

需要创建或修改：
- src/ai_impact_research/agent/tools.py
- src/ai_impact_research/agent/company_report_agent.py
- src/ai_impact_research/llm/prompts/company_report.md
- scripts/generate_company_report.py
- tests/test_company_report.py

Report sections：
- Company snapshot
- AI maturity summary
- Signal trajectory
- Financial performance context
- Peer comparison
- Evidence snippets
- Methodology caveats

实现要求：
- Report 不允许编造数据；缺字段就写 unavailable。
- 每个结论要能追溯到 panel 或 evidence record。
- 不输出投资建议。

验收标准：
- sample ticker 可以生成 markdown report。
- 缺 ticker 时清晰报错。
- tests 验证 report 包含 caveat。
```

---

## Phase 10 — Robustness、deployment、final polish

```text
请完善 robustness checks、deployment docs 和最终交付打包。

目标：
- 提高 research credibility。
- 准备 midterm/final demo。
- 确保别人能复现实验。

需要创建或修改：
- src/ai_impact_research/analysis/robustness.py
- scripts/run_robustness_checks.py
- docs/07_RESPONSIBLE_AI_AND_RISKS.md
- infra/deployment_notes.md
- reports/final_paper_outline.qmd
- README.md

Robustness checks：
- sector-neutral IC
- size bucket analysis
- missingness by sector / size
- lag sensitivity
- disclosure bias proxy，例如 filing length / transcript availability

Final requirements：
- README 有完整复现命令。
- docs 写清楚 limitations。
- dashboard 有 caveat。
- reports 有 final paper outline。
- CI 全绿。

验收标准：
- 一个新成员可以从 README 跑通 sample pipeline。
- 所有交付物路径清楚。
- 没有 secrets 或 private data 被提交。
```
