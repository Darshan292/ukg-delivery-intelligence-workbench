# Stack feasibility and AI-vs-deterministic boundaries (as of 2026-11-18)

Method note: ~15 tool calls. WebSearch returns summarised snippets, not full pages; WebFetch worked only for github.com (Docling). reactflow.dev and pymupdf.readthedocs.io were fetched-blocked (host not in session network allowlist; reactflow.dev appeared only via search snippets). Context7 MCP failed to connect (ERR_PROXY_TUNNEL). Claim labels: [FACT]=documented, [VENDOR]=vendor claim, [RESEARCH]=study/benchmark, [INFER]=my inference. Many sources are secondary blogs; verify before contractual/licensing decisions.

## 1. Document processing (Docling, PyMuPDF, alternatives, openpyxl, XML, pandas)

### Takeaway
Docling (MIT code) is a credible, actively hosted (LF AI & Data) parser, but its table accuracy figures vary widely (63-85% TEDS independent vs a widely repeated, unsourced 97.9%), so benchmark on your own synthetic UKG exports. PyMuPDF is AGPL-3.0 or Artifex commercial: a licensing risk for a commercial SaaS; recommend replacing it or budgeting a commercial licence.

### Cited Findings
- [FACT] Docling codebase is MIT; "for individual model usage, please refer to the model licenses found in the original packages" (model licences are separate and must be audited). Supports PDF, DOCX, PPTX, XLSX, HTML, images etc., OCR, runs locally/air-gapped, Python >=3.10 (3.9 dropped in 2.70.0), hosted by LF AI & Data, started by IBM Research Zurich. — [Docling GitHub](https://github.com/docling-project/docling)
- [RESEARCH] Docling layout stage is an RT-DETR-derived object detector trained on DocLayNet; the technical report says EasyOCR on CPU can take 30+ s per page (OCR step only). — [Docling Technical Report](https://arxiv.org/html/2408.09869v5)
- [FACT] Docling GPU docs: higher page_batch_size enables GPU batch inference for layout detection; no VRAM figures found. — [Docling GPU docs](https://docling-project.github.io/docling/usage/gpu)
- [VENDOR/secondary] granite-docling-258M VLM reported as Apache 2.0 (secondary source; verify on model card). — [llmrun.dev](https://llmrun.dev/model/ibm-granite-granite-docling-258m)
- [RESEARCH, conflicting] Docling table accuracy: ~97.9% repeated by secondary sites with no verifiable primary source; independent 17-parser study ~84.5% TEDS (markdown output) vs pymupdf4llm 84.8%; Tensorlake OmniDocBench comparison Docling 63.3% TEDS vs Azure Document Intelligence 78.6% and AWS Textract 81.0% (Tensorlake is a competitor vendor). Metrics and datasets differ. — [Tensorlake benchmarks](https://docs.tensorlake.ai/document-ingestion/benchmarks); [Ertas summary](https://www.ertas.ai/blog/pdf-parsing-accuracy-benchmark-docling-unstructured); [IDP benchmarks guide](https://idp-software.com/guides/document-parsing-benchmarks/)
- [RESEARCH] Academic scientific-PDF table benchmark: Docling promising but no tool achieves perfect end-to-end table extraction; borderless tables defeat most rule-based parsers. — [Moonlight review](https://www.themoonlight.io/review/benchmarking-table-extraction-from-heterogeneous-scientific-extraction-documents)
- [FACT] PyMuPDF is dual-licensed: AGPL, or commercial licence via Artifex (exclusive commercial licensing agent for MuPDF; Artifex maintains PyMuPDF). Artifex says commercial licence removes AGPL obligations (open-sourcing the whole app, etc.). — [Artifex: PyMuPDF acquired](https://artifex.com/blog/pymupdf-acquired-by-artifex); [PyMuPDF about](https://pymupdf.readthedocs.io/en/latest/about.html) (via search snippet)
- [secondary, competitor-authored] Comparison sites claim SaaS/Docker distribution needs a commercial licence and that pricing is unpublished; treat as unverified, not legal advice. — [file2markdown](https://www.file2markdown.ai/blog/is-pymupdf-free-for-commercial-use); [pypdf comparison](https://pdf.oxide.fyi/docs/comparison/pymupdf-vs-pypdf)
- [FACT/community] openpyxl does not evaluate formulas; `data_only=True` returns Excel's cached value or `None` if never calculated; formulas and cached values cannot be read simultaneously in one load (must open workbook twice); saving a data_only workbook drops formulas; shared/array formula cached values are inconsistent. — [openpyxl issue 1425](https://foss.heptapod.net/openpyxl/openpyxl/-/issues/1425); [openpyxl-users thread](https://groups.google.com/g/openpyxl-users/c/XDVh8spS-lc); [openpyxl tutorial](https://openpyxl.readthedocs.io/en/3.1/tutorial.html)
- [FACT] OWASP: ZIP archives are not recommended for upload; zip bombs cause DoS (third-party suggests aborting at >100x expansion); DOCX/XLSX/SVG are XML/ZIP so XXE applies; defusedxml recommended for Python. — [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html); [OWASP XXE Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html)

### Inferences
- [INFER] Licence audit is a gate: PyMuPDF (AGPL) in a network-served SaaS is the main risk; pypdf/pdfplumber (permissive, as commonly understood; confirm) plus Docling cover text/tables, with Textract/Azure only if customers accept cloud residency. Pick one PDF library and keep it behind an interface so it is swappable.
- [INFER] Provenance needs coordinates: use Docling's element bounding boxes/page numbers for PDF; for Excel use openpyxl directly (sheet, cell address, merged-range anchor, hidden state, formula text AND cached value loaded in two passes), not pandas, which discards cell addresses unless row offsets are recorded manually. Reject/flag `.xlsm`/macros and external links.
- [INFER] Docling's DOCX/XLSX paths are convenient but a deterministic openpyxl/python-docx path gives stricter control for structural truth.
- [INFER] Docling model weights and first-run downloads conflict with air-gapped/customer-hosted deployments unless pre-baked into images; pin versions and hashes.

### Gaps
- No primary Docling memory/VRAM/throughput numbers found; no primary pdfplumber/pypdf/Unstructured/Tika licence confirmation retrieved; python-docx and lxml specifics, openpyxl merged-cell/hidden-sheet docs, Textract/Azure data-residency terms not verified (search returned nothing). PyMuPDF commercial pricing unpublished in sources found.

## 2. Graph visualisation

### Takeaway
React Flow is right for an editable, node-rich impact view of tens to a few hundred nodes; use server-side subgraph/neighbourhood queries and collapse/filter rather than rendering whole graphs. For thousands of nodes, Sigma.js (WebGL) or Cytoscape.js is the evidence-backed alternative.

### Cited Findings
- [FACT] React Flow's performance guide attributes slowdowns mainly to unnecessary re-renders; advises memoisation and not subscribing to full node/edge arrays. — [React Flow performance](https://reactflow.dev/learn/advanced-use/performance) (snippet only; page fetch blocked)
- [community] A maintainer comment suggests ~1,000 nodes as a practical ceiling depending on node complexity; forum reports of slowdown past ~100 custom nodes. — [Lightrun/GitHub issue summary](https://lightrun.com/answers/wbkd-react-flow-performance-drop-when-panning-or-zooming)
- [VENDOR, competitor] Ogma (Linkurious) claims Sigma renders 100k edges easily but struggles with ~5k nodes with icons. — [Ogma vs Sigma.js](https://doc.linkurious.com/ogma/latest/compare/sigmajs.html)
- [secondary] Cytoscape.js positioned for network analysis; React Flow for editable node UIs. — [First AI Movers](https://radar.firstaimovers.com/react-flow-vs-cytoscape-graph-engine-choice.md)

### Inferences
- [INFER] Impact analysis returns a bounded traversal (downstream set), typically far smaller than the full graph: React Flow + elkjs/dagre layered layout fits. Use a separate large-graph overview only if measured need.

### Gaps
- No React Flow MIT/Pro licensing page, no elkjs/dagre or G6 evidence retrieved (reactflow.dev blocked). I recall React Flow core is MIT with paid Pro examples, but this is unverified here.

## 3. Backend and storage

### Takeaway
Keep Postgres FTS first; semantic search is a complement justified only when users query by meaning and keyword recall measurably fails. For ingestion jobs, a Postgres-backed queue is adequate at this scale. For tenancy, shared schema + RLS is the common default; contractual dedicated-storage customers need database-per-tenant.

### Cited Findings
- [secondary] Native `ts_rank` lacks BM25 properties; hybrid = FTS/BM25 + pgvector fused with Reciprocal Rank Fusion; BM25 options include ParadeDB pg_search and Tiger Data pg_textsearch (vendor-authored sources). — [ParadeDB hybrid search](https://paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual); [TigerData pg_textsearch](https://www.tigerdata.com/blog/pg-textsearch-bm25-full-text-search-postgres)
- [secondary] Queues: Dramatiq/Celery/ARQ need Redis/RabbitMQ; Procrastinate is Postgres-only; SKIP LOCKED queues cause dead tuples/bloat and lack per-task rate limits; suited to small-to-medium volume. — [Abilian job queues](https://lab.abilian.com/Tech/Python/Useful%20Libraries/Job%20queues); [Microsoft on Postgres as queue](https://techcommunity.microsoft.com/blog/adforpostgresql/potential-consequences-of-using-postgres-as-a-job-queue/4514332); [DBOS](https://dbos.dev/blog/making-postgres-queues-scale)
- [secondary] RLS: no per-tenant catalog cost, scales to many tenants, but should be defence in depth alongside app filtering; schema-per-tenant gives harder boundary but catalog bloat past thousands; contractual dedicated storage requires database-per-tenant. — [DEV: RLS vs schema](https://dev.to/itsjayanth/multi-tenant-postgresql-row-level-security-vs-schema-per-tenant-when-to-use-which-3joe); [ClickHouse multi-tenant guide](https://clickhouse.com/resources/engineering/multi-tenant-saas-postgres-architecture)

### Inferences
- [INFER] Ingestion is low-volume and long-running per file; a Postgres queue (Procrastinate or small SKIP LOCKED table) avoids Redis and fits customer-hosted installs. Run parsing workers in sandboxed, resource-limited processes.
- [INFER] Design schema with tenant_id on every row + RLS from day one so single-tenant/customer-hosted deployment is the same code with one tenant.

### Gaps
- FastAPI/Pydantic v2 maturity, pgvector licence/limits not researched (no sources retrieved); I did not verify current versions.

## 4. Security and compliance

### Takeaway
Treat every upload as hostile and every LLM call as a data egress. Provider no-training and zero-data-retention (ZDR) terms are contract-dependent and shifted during 2026; confirm in current official terms before any real customer data.

### Cited Findings
- [FACT] See Section 1 for OWASP upload/XXE guidance (limit archives, cap decompressed size, disable external entities, strip macros per third-party guidance).
- [secondary] Anthropic API and commercial tiers do not train on inputs/outputs per Commercial Terms; standard API retention up to 30 days unless ZDR agreed; OpenAI API excludes training by default and offers ZDR for eligible customers (~30 days abuse-monitoring retention otherwise). — [Axoflow privacy map](https://axoflow.com/blog/privacy-map-for-claude-gpt-gemini-2026); [Gupta: ZDR](https://guptadeepak.com/zero-data-retention-ai-providers/)
- [secondary, dates/model names inconsistent] In 2026 Anthropic required 30-day retention for its most capable models then partly reversed after enterprise pushback; OpenAI previewed "Private Safety Processing" to preserve ZDR. — [CX Today](https://www.cxtoday.com/security-privacy-compliance/anthropic-zero-data-retention-enterprise-ai/); [Axios, 2026-08-19](https://axios.com/2026/08/19/openai-previews-zero-retention-safety-system-as-anthropic-requires-data-logs)

### Inferences
- [INFER] Phase 1 (synthetic data): no compliance gate, but design for it. Before real data: redact/pseudonymise employee PII before any LLM call, per-tenant opt-in for LLM features, a model-provider allowlist, audit log of every prompt/response hash, and a no-LLM mode. UKG customers/SIs will likely expect customer-hosted or private deployment (inference; unverified).

### Gaps
- No primary sources for SOC 2 Type II, ISO 27001, GDPR/data residency, Azure/AWS residency, or UKG customer deployment expectations; official provider retention pages not read.

## 5. AI boundaries

### Takeaway
Deterministic parsing owns structure and relationships; LLM output is a proposed, span-cited, validated candidate that stays "suggested" until a human confirms. Citations show origin but do not prove correctness, so verify the cited span programmatically.

### Cited Findings
- [RESEARCH] LLMs invent parts of otherwise-valid references (DOIs, venues, authors) and experts rarely catch it without structured checklists. — [arXiv 2602.21059](https://arxiv.org/pdf/2602.21059)
- [RESEARCH] Sentence-level accuracy metrics miss distortions of relational structure; one benchmark reported citation omission up to 91.9% (single study, bibliometric domain). — [arXiv 2603.01341](https://arxiv.org/abs/2603.01341)
- [RESEARCH] Citation-checking against authoritative registries found 36-61% "unresolved" citations, many likely fabricated (software-engineering literature). — [arXiv 2603.07287](https://arxiv.org/html/2603.07287v1)
- [RESEARCH] Span-level traceability outperforms document/passage-level checks in one financial QA paper (domain-specific). — [ACL FNP 2026](https://aclanthology.org/2026.fnp-1.4.pdf)
- [secondary] OWASP LLM09 (misinformation) mitigations: grounding, output validation, human review for high-stakes; output moderation alone is insufficient. A single small test found adding a citation requirement slightly worsened results; citations do not guarantee accuracy. — [OWASP LLM Top 10 2025 summary](https://dev.to/amasen/owasp-llm-top-10-what-every-engineer-building-with-ai-needs-to-know-in-2025-2gp8); [KodeKloud](https://kodekloud.com/blog/ground-llm-answers-with-citations/)

### Inferences
- [INFER] Split: deterministic = parsing, cell/table structure, ID/code matching, exact-name entity resolution, edge creation from explicit references, impact traversal, coverage checks. LLM-assisted = entity/relationship candidates from prose, fuzzy alias matching (as suggestions with score), explanations of already-computed impact (must cite graph node IDs/evidence IDs), diagnostics hypotheses. Never LLM = confirming a relationship.
- [INFER] Controls: structured output schema with required `source_span` (doc, page/cell, char offsets); verifier checks span text exists and entities appear in it; reject otherwise; status `suggested` -> `confirmed` only by named reviewer; append-only audit (who, when, evidence, prior state, model/prompt version).
- [INFER] RAG/semantic search is justified only for free-text prose retrieval (runbooks, tickets) as a retrieval aid; for configuration objects use structured and keyword lookup. A knowledge graph adds value for multi-hop dependency traversal; a relational edge table plus recursive CTEs likely suffices before a graph DB at this scale.

### Gaps
- No extraction-specific LLM hallucination-rate benchmark found (search returned citation-hallucination studies, an adjacent domain); no regulatory audit requirements (SOC 2 change-approval evidence) sourced.

## 6. Deployment and testing

### Takeaway
Not researched with sources in this pass.

### Cited Findings
- [secondary] RLS/schema/database-per-tenant options and contractual dedicated storage (see Section 3).

### Inferences
- [INFER] Ship as containers runnable single-tenant/customer-hosted from day one (same codebase, one tenant); multi-tenant SaaS later. Testing: golden synthetic fixtures with expected cell/page provenance; property-based tests (Hypothesis) for graph traversal invariants (e.g. impact set closed under dependency, no duplicates, idempotent ingestion); LLM tests via recorded fixtures plus verifier tests that fabricated spans are rejected; Playwright CLI for UI.

### Gaps
- No sources retrieved on UKG customer/SI deployment expectations, golden-dataset practice, Hypothesis, or Playwright; SaaS vs on-prem expectations remain unverified.
