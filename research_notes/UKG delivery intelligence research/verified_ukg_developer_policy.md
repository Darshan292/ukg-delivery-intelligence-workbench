# Verified: UKG Developer Policy vs. the Workbench

**Source:** UKG Developer Policy, https://developer.ukg.com/proplatform/docs/developer-policy
**Retrieved:** 2026-11-18, full text, via the page's markdown rendition (`…/developer-policy.md`, HTTP 200). Page metadata `updatedAt: 2026-09-30T19:27:09Z`. SHA-256 of the retrieved text: `1bf9782bf4412058cceb6904d1eb31ccb88e170448aea68a34740f8e29004b1a`.
**Status:** primary-read. Every quote below is verbatim. Interpretation is labelled **[Inference]** and is not legal advice.

> **Not a conclusion on legality.** This note does not decide whether the Workbench is prohibited or permitted. Several clauses, above all "Competitive Product or Service", need independent legal review (and, where needed, UKG's own interpretation) before any commercial use or real data. The note maps what the policy says onto what we plan to do, and lists who must approve what.

## 1. Scope: what the policy governs

- It governs "the access and use of any UKG-provided and UKG-approved technical interfaces for accessing, receiving, transmitting or exchanging data". Listed: REST/SOAP APIs (UKG Pro, UKG WFM/Dimensions, UKG Ready), SDKs, webhooks, "Customer Data Warehouse / People Fabric Data Platform (BYOBI, GraphQL)", "MCP Gateway (AI agent tool access)", and "Other datafeeds, databases, data lakes" (§1).
- It "is incorporated by reference into the applicable Master License Agreement (MLA) and/or Master Service Agreement (MSA). In the event of conflict, the MLA/MSA controls" (§1).
- "Customer Data" means "All data submitted to or generated within UKG services by or on behalf of a Customer" (Appendix A).
- "Developer" is **not defined** in the glossary. **[Inference]** It is therefore unclear whether the policy binds a customer's own staff, a consultancy acting for a customer, or only registered partners. That is a question for Legal.

**[Inference]** The policy's obligations attach to using a UKG Data Interface. Offline processing of files a customer supplies does not obviously involve a Data Interface. But configuration exports and reports are "generated within UKG services", so they are Customer Data, and the customer's own MSA governs whether the customer may share them. The policy alone does not settle the offline case.

## 2. Clause-by-clause findings

### 2.1 Approved interfaces and developer registration (§2)
- "Developers may only access UKG Data Interfaces that are provisioned and approved by UKG. Developers must register their access with UKG using an active, approved credential prior to accessing the UKG Data Interface."
- "Developers must not access, submit, receive, query, transmit, or exchange data or functionality with or through a UKG solution without using a UKG Data Interface."
- Access tiers: Production APIs via "Partner Portal credential + Customer consent"; Beta/Preview APIs via "Beta enrollment"; Data Warehouse (BYOBI) via a "Separate Data Access Agreement".

### 2.2 Partner Portal credentials and customer consent (§3)
- "All credentials are issued through the UKG Partner Portal or Developer Console."
- Customer-Specific Credentials "requires explicit customer consent (via a UKG-approved method) before issuance". Multiple-Customer Credentials require "explicit consent from all customers".
- Rotation: tenant-specific credentials with access to customer PII "once at least every 90 days". Generic and multiple-customer credentials every 12 months. All credentials "immediately upon suspected compromise".
- Credentials "must not be stored in source code, logs, or public repositories".
- If a customer withdraws consent, "the Developer must immediately cease usage of the credentials … and all data processing related to that Customer". Revoked credentials "cannot be reinstated".

### 2.3 Competitive products and competitive intelligence (§4)
- **Competitive Product or Service:** "Creating a competitive product or service to UKG's offerings."
- **Competitive Intelligence:** "Using UKG data to benchmark, analyze, or inform products that compete with UKG offerings."
- "Offerings" is not defined. **[Inference]** UKG offers Setup Data Manager with a compare function, Bryte AI, a reported "UKG in Claude" integration, implementation services and a Pro WFM Migration Assessment service. Depending on interpretation, drift comparison, AI explanation or migration assurance could be read as competing. Equally, an assurance layer over artefacts UKG does not hold (requirements, test inventories, defects) may not be. **Only independent legal review (and, where needed, UKG's own interpretation) can decide this.** The second clause matters as well: using UKG data to "inform" a competing product could reach the use of real configuration to design our rules.

### 2.4 Cross-tenant data aggregation (§4)
- "Aggregating or comparing data across multiple Customer tenants without a signed Data Sharing Agreement and consent from all involved tenants. This includes anonymized or aggregated benchmarking data derived from multiple tenants unless explicitly authorized under a Data Sharing Agreement."
- **[Inference]** This is directly relevant to a consultancy. Comparing one customer's configuration against another's, building a "common patterns" library from several customers, or benchmarking across projects would all need a Data Sharing Agreement. Comparing two environments of the **same** customer (dev against prod) is not cross-tenant. But a customer's non-production and production tenants are separate tenants, and whether "Multiple Customer tenants" covers one customer's own tenants needs Legal.

### 2.5 AI training, fine-tuning and evaluation (§4)
- "Using Customer Data to train, fine-tune, or evaluate AI or machine learning models without explicit Customer and UKG written consent."
- **[Inference]** "Evaluate" is the critical word. Measuring our LLM extraction accuracy on real customer artefacts counts as evaluating a model on Customer Data, which needs customer and UKG written consent. Evaluation sets must be synthetic unless that consent exists.

### 2.6 Autonomous and semi-autonomous AI agents (§4, §7)
- Prohibited: "Deploying semi-autonomous or generative AI systems that plan, select, or execute sequences of UKG API calls without MCP Gateway registration or explicit UKG authorization."
- Also prohibited under Scraping and Bulk Extraction: "agentic loops, screen scraping, session replay, or unpublished endpoint enumeration".
- §7: every agent tool call must be logged (timestamp, tool, PII-redacted input, status, human operator or agent session id). Logs are retained "a minimum of twelve (12) months following cessation". The Developer "is responsible for all actions taken by that agent". An AI Integration Agreement governs autonomous agents (Appendix A).
- **Drafting defect:** the "Credential Sharing" row repeats the AI-agent text word for word instead of describing credential sharing. §11 cites a "Section 7.4" that does not exist.

### 2.7 Encryption and data residency (§5)
- In transit: "TLS 1.3 (preferred) or TLS 1.2 at minimum", with a planned move to TLS 1.3 only.
- At rest: "AES-256 or an equivalent standard recognized by NIST", and "Developers must be able to demonstrate compliance with FIPS 140-2 or FIPS 140-3 validated cryptographic modules upon request."
- Residency: process and store Customer Data "only in the geographic jurisdictions authorized in credential issuance or as specified in the applicable Data Processing Agreement".

### 2.8 Sub-processors (§5)
- "Developers must obtain prior written authorization from UKG prior to engaging their own sub-processors to process Customer Data", must flow down equivalent obligations, keep a current list, and "remain fully liable".
- **[Inference]** A cloud host, a managed database provider and an LLM API provider (Anthropic or any other) would each be a sub-processor once they process Customer Data. Each would need prior written UKG authorisation **for data obtained through a UKG Data Interface**. Whether this also covers offline customer-supplied files is for Legal (see §1).

### 2.9 Data minimisation and purpose (§4, §5)
- "Storing PII Beyond Purpose" is prohibited. Process "only for the limited and specific purpose provided at the time the Developer requests and receives approval of access by UKG". Request "only the OAuth scopes, data fields, and access time period strictly necessary".
- **[Inference]** Configuration objects are mostly not PII, but employee assignments are. Scoping ingestion to configuration and excluding person records reduces exposure considerably.

### 2.10 Customer-data deletion (§5, §3.4)
- Delete "immediately and permanently … all Customer Data and any copies … including from shared environments, backups, archives, and derivative datasets" when the engagement ends, credentials are revoked, or the customer or UKG asks. Provide "written confirmation" on request.
- **Drafting defect:** §3.4 refers to deletion in "Section [8]", but deletion is in §5.
- **[Inference]** Derived artefacts count: the canonical IR, evidence snippets, graph edges, impact reports and caches. Backups must be purgeable per customer, which is a strong argument for per-customer storage keys (deleting the key renders that customer's backups unreadable) and per-customer isolation.

### 2.11 Security incident reporting (§5)
- Report "any suspected or confirmed unauthorized access or export of Customer Data or a breach" to UKG Security Operations "within twenty-four (24) hours of discovery", via security-incidents@ukg.com or the Partner Portal form, with discovery time, nature and scope, containment and a contact.

### 2.12 Audit and enforcement (§6, §8, §10, §11)
- UKG may throttle, suspend or revoke access "as determined by UKG in its sole discretion" (§10). It monitors usage for anomalies and may suspend (§8). It may require IP allowlisting (§8).
- Audit scope includes access logs, credential usage records, storage and encryption practices, AI agent designs and logs, sub-processor arrangements, and compliance documentation (§11). Developers "must retain logs of UKG data interface and data access".
- Policy changes take effect on posting; "Continued use … constitutes acceptance" (§12). Revision history shows version 1.0 with an empty date ("[--]").

## 3. The four activity classes

| Activity | Uses a UKG Data Interface? | Customer Data involved? | What the policy appears to require **[Inference]** | Needs |
|---|---|---|---|---|
| **1. Synthetic-data development** (Milestone 1) | No | No | Policy obligations do not appear to attach. Residual question: whether building and selling the product is itself a "Competitive Product or Service" under the MSA or any partner agreement, independent of data. | Legal clarification on the competitive clause before commercial positioning. No UKG approval needed to keep building on synthetic data. |
| **2. Offline processing of authorised customer-supplied artefacts** | No, if the customer exports and hands over files | Yes, for UKG-generated exports and reports. No, for project-authored documents (requirements, test inventories, design workbooks), though those may still hold customer confidential data | Not clearly within the policy. Governed by the customer's MSA (may the customer share UKG-generated data with us?) and our contract and DPA with the customer. Must not be designed as a workaround to "Bypassing Consent Flows" or §2's "with or through a UKG solution". Deletion, residency and minimisation good practice applies either way. | Written customer consent and a DPA. Legal clarification on whether policy obligations (sub-processor approval, deletion, 24-hour reporting) apply to offline exports. Sanitisation rules. |
| **3. Customer-authorised API integration** (read-only configuration GETs) | Yes | Yes | Partner Portal or Developer Console credential, customer consent via a UKG-approved method, registration before access, a declared purpose approved by UKG, least-privilege scopes, 90-day rotation, residency, sub-processor authorisation, deletion with written confirmation, 24-hour incident reporting, access-log retention and audit, rate limits. No agentic call sequences without MCP Gateway registration or authorisation. | **Written UKG approval** (registration, purpose, sub-processors), **customer consent** via UKG's flow, Legal sign-off on the competitive clause. |
| **4. Commercial deployment using UKG customer data** (multi-customer SaaS or hosted) | Possibly both routes | Yes, across several customers | Everything in row 3, plus: no cross-tenant comparison or benchmarking without a Data Sharing Agreement; no model training, fine-tuning or evaluation on Customer Data without customer and UKG written consent; every sub-processor (host, database, LLM) approved in writing; per-customer deletion including backups; FIPS-validated crypto evidence; audit readiness. | **Written UKG approval**, **customer consent and a DPA per customer**, a **Data Sharing Agreement** for any cross-customer feature, and **Legal interpretation** of the competitive clauses. |

## 4. Product features mapped to clauses

| Workbench feature | Most relevant clause | Risk if unaddressed **[Inference]** |
|---|---|---|
| Drift / snapshot compare (same customer) | §4 Competitive Product (Setup Data Manager has compare); cross-tenant if environments count as tenants | Medium–high, pending Legal |
| Cross-customer pattern library or benchmarks | §4 Cross-Tenant Data Aggregation | **High. Do not build without a Data Sharing Agreement** |
| LLM extraction on real artefacts | §5 Sub-processor; §4 AI training and evaluation | High until the LLM provider is authorised and evaluation stays synthetic |
| AI explanations or diagnostics calling UKG APIs | §4 Unapproved AI Agents; §7 | **High. Not planned; keep it out** |
| Read-only configuration GETs | §2, §3, §5 | Manageable with registration, consent and approval |
| Storing evidence snippets and derived graphs | §5 deletion ("derivative datasets") | Must be designed for per-customer purge |
| Employee or person records | §4 PII beyond purpose | Avoid. Ingest configuration only |
| Migration assurance (WFC to Pro WFM) | §4 Competitive (UKG sells a Migration Assessment) | Pending Legal |

## 5. What this changes in earlier notes
- It corroborates, at primary level, the snippet-level claim that agentic access needs UKG authorisation (`native_ukg_and_ai_policy.md`). The MSA, AUP and API Call Pack texts themselves remain unread.
- It **adds** obligations the earlier research missed: sub-processor pre-authorisation, 90-day rotation, FIPS-validated crypto on request, 24-hour incident reporting, deletion including backups and derivative datasets, and audit rights.
- It confirms that an MCP Gateway exists as a governed UKG interface for AI agents. It does not show how "UKG in Claude" relates to that gateway.

## Gaps
- "Developer" is undefined, so whether the policy binds a consultancy acting for a customer, or a customer's own staff, is unknown.
- How the policy interacts with the MSA, the AUP and the API Call Pack terms is unknown, because those were not readable (Cloudflare challenge).
- No Partner Portal documentation was read: how consent is captured, what "UKG-approved method" means, approval timelines.
- Whether a customer's non-production and production tenants count as "multiple Customer tenants".
- Legal must resolve the drafting defects (duplicated "Credential Sharing" row, broken section references, undated v1.0).
