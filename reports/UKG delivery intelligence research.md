# Build the evidence engine, not the platform

The UKG Delivery Intelligence Workbench is **technically feasible and partly differentiated, but the commercial case rests on a problem nobody has yet measured**. The core engineering is sound and proven elsewhere. It means turning artefacts into a canonical representation with cell- and page-level evidence, building a typed dependency graph, and running a deterministic, tiered change-impact traversal. Salesforce, SAP and Workday each support paying vendors for configuration dependency mapping, environment compare and impact-driven test selection. Nothing found offers that for UKG configuration. The weak points are elsewhere. No practitioner source quantifies the manual cross-referencing the product claims to remove. The richest real input, Pro WFM configuration read through UKG's REST API, is documented but sits under contract terms (MSA, AUP, API Call Packs Exhibit A) that could not be read. UKG's own Setup Data Manager already offers a per-item compare. And two of the eight capability areas fail on evidence or timing: G, the WFC migration "factory", faces a support window that closes on 31 March 2027, and H, cost intelligence, has no data behind it. The defensible core is a narrow one: provenance on every edge, OBSERVED/INFERRED/CONFIRMED status with human-only confirmation, snapshot history UKG does not appear to keep, and requirement/configuration/test coverage that crosses tool boundaries UKG does not own. The smallest product that proves the idea is close to the repo's Milestone 1 plan, with five corrections: drop PyMuPDF, rename the impact tiers, add a "not modelled" tier, make the ground truth independent of the fixture generator, and add a two-snapshot diff as the change source. Before anyone calls this production-ready, it needs four things: real sanitised artefacts, legal review of UKG's terms, practitioner interviews, and validation against real regression or parallel-pay outcomes.

> **Revision 2 (18 November 2026): UKG Developer Policy incorporated.** The full UKG Developer Policy (updated 30 September 2026) has now been read at primary level ([policy](https://developer.ukg.com/proplatform/docs/developer-policy); analysis in `research_notes/UKG delivery intelligence research/verified_ukg_developer_policy.md`). It changes the access picture more than anything else in this report, in four ways:
>
> - **It prohibits "Creating a competitive product or service to UKG's offerings" and "Competitive Intelligence".** This report does **not** conclude whether the Workbench falls under either; that needs UKG and TCS Legal interpretation (decision D1).
> - **It sets conditions on any UKG Data Interface use:** registration through the Partner Portal or Developer Console, customer consent through a UKG-approved method, and a declared purpose approved by UKG.
> - **It forbids certain uses outright** without the right agreements: cross-tenant aggregation or benchmarking without a Data Sharing Agreement; training, fine-tuning **or evaluating** AI models on Customer Data without customer **and** UKG written consent; and AI agents calling UKG APIs without MCP Gateway registration or authorisation.
> - **It imposes operating obligations:** prior written UKG authorisation for every sub-processor (hosting, database and LLM providers included); deletion that reaches backups and derivative datasets; incident reporting within 24 hours; FIPS-validated encryption on request; and audit rights.
>
> Development on synthetic data does not use a Data Interface and can continue. Offline processing of customer-supplied exports, customer-authorised API integration and commercial deployment each need different approvals (section 10). The architecture decisions that follow from this research are recorded in `docs/decisions-for-approval.md`, with risks in `docs/risk-register.md`.
>
> **Evidence caveat. Read this before relying on any claim.** Most research notes behind this report were built from search-result snippets, because full-page fetches were blocked in the research sessions. Only two notes contain full-text primary-source verification. The first, `verified_ukg_technical.md`, covers developer.ukg.com pages, artifex.com/licensing and the PyMuPDF docs. The second, `verified_ukg_policy.md`, covers developer.ukg.com policy and hub pages. The third, `verified_ukg_developer_policy.md` (revision 2), covers the complete UKG Developer Policy. Where they conflict with earlier notes, this report follows them. **UKG's legal terms were NOT readable.** The Master Services Agreement, Acceptable Use Policy and API Call Packs Services Description / Exhibit A all returned a Cloudflare challenge (HTTP 403). Every policy conclusion below is therefore provisional. You need to obtain those PDFs, from UKG or a customer, and have them reviewed by a lawyer before any design depends on them. Also unverified at primary level: Setup Data Manager behaviour and export format (all *.mykronos.com help hosts were blocked), Workforce Central end-of-life dates (www.ukg.com blocked), every competitor's actual feature depth, and every incident figure (news summaries only, no audit PDFs read).
>
> Claim labels used throughout: **[Documented]** means a vendor document, standard or official record. It is marked *(primary-read)* when the full page was read and *(snippet)* when only a search summary was seen. **[Vendor claim]** means marketing, an analyst summary of a vendor briefing, or a partner selling services. **[User report]** means a practitioner or customer account. **[Inference]** means this report's own reasoning.

---

## 1. Executive product definition: an assurance layer, not a UKG tool

The Workbench should be defined as **a read-only, evidence-first assurance layer that sits beside UKG**, not inside it. It ingests the documents and exports an implementation already produces: design workbooks, requirement lists, test inventories, defect exports, mapping specifications, and, where lawfully obtained, configuration snapshots. It turns them into a canonical intermediate representation (IR) in which every fact points to a page, cell, XPath or JSON pointer in a hashed source file. It builds a typed dependency graph over that IR, and it answers four questions deterministically. What references this object? What changed between two snapshots? What could this change reach, and through which evidence? Which requirements and configuration objects have no test? AI proposes candidate relationships from prose and explains computed results. It never decides structure, and it can never mark a relationship CONFIRMED.

Three properties separate this from what already exists. First, **every edge carries its own evidence and verification status**. None of the provenance and lineage systems reviewed (Jama, Polarion, DataHub, OpenMetadata, Salesforce's dependency API) gives per-edge OBSERVED/INFERRED/CONFIRMED status with cell-level evidence. DataHub, for example, only offers an optional `confidenceScore` on file-based lineage ([DataHub](https://docs.datahub.com/docs/generated/ingestion/sources/file-based-lineage)) **[Documented, snippet]**. Second, **impact is reported in tiers with explicit blind spots**, never as a "safe" verdict. Third, **the graph crosses tool boundaries** (spreadsheets, test tools, defect trackers, integration specs) that no single vendor owns **[Inference]**.

What it is not: a UKG replacement, a configuration editor, a test runner, a ticketing system, an integration monitor or a chatbot over UKG data. The brief already says this. The evidence below shows each of those spaces is occupied by UKG itself, by test vendors, or by ServiceNow and Boomi.

## 2. The problem is plausible and real at the edges, but unmeasured at the centre

### What the evidence actually shows

The strongest evidence that configuration errors cost real money is public-sector audits, and they fit the change-impact thesis closely. A Manatee County, Florida audit (reported June 2026) found EMS workers **underpaid by at least $336,607 over nine months** because the system did not count hours toward overtime as the collective bargaining agreement required. Reporting ties this to new overtime rules after a June 2025 agreement ([WUSF](https://www.wusf.org/politics-issues/2026-06-27/manatee-county-underpaid-ems-workers-by-at-least-336-607-audit-finds); [EMS1](https://www.ems1.com/labor-issues/audit-finds-fla-county-underpaid-ems-personnel-more-than-336k)) **[Documented via news, snippet; audit PDF not read]**. Volusia County EMS reportedly saw underpayments of up to $2,000 and overpayments above $10,000. Nearly 30 EMTs faced repayment demands of $76 to $62,000 after a payroll coding error ([EMS1](https://www.ems1.com/labor-issues/fla-emts-told-to-repay-overpayments-after-payroll-error)) **[Documented via news, snippet; dates and totals unconfirmed]**. In Australia, ALDI settled a class action over a Kronos clock rounding configuration for about A$55M covering 32,308 staff, without admitting liability ([HC Online](https://www.hcamag.com/au/specialisation/employment-law/aldis-55m-class-action-settles-unpaid-shift-work-for-32000-staff/594780)) **[Documented via news, single secondary source; approval date unverified]**.

Read carefully, the Manatee case is the clearest example of the product's target failure. A contract changed, and the rule configuration did not follow it correctly **[Inference]**. A requirement-to-configuration-to-test trace, with the contract change as the seed, is exactly what would have flagged it. But the causal chain comes from news summaries, not the audit itself.

Other municipal audits point to a different and important problem. Fayetteville, NC found Kronos rules **set from verbal guidance and past practice rather than written policy** ([Fayetteville audit](https://fayettevillenc.gov/home/showpublisheddocument/21178/637922792448230000)) **[Documented, snippet]**. Dallas found missing input controls for paid leave ([Dallas A15-011](https://dallascityhall.com/departments/auditor/DCH%20Documents/Audit%20Reports%20FY%202015%20(3-20-2015%20to%2009-30-2015)/A15-011%20-%20Audit%20of%20City%20of%20Dallas'%20Civilian%20Timekeeping%20Internal%20Controls%20and%20Processes%2008-14-2015.pdf)) **[Documented, snippet]**. Albuquerque and Springfield found approval gaps at interfaces ([Albuquerque](https://www.cabq.gov/audit/documents/17-104-final-04252019-js.pdf/@@download/file/17-104%20Final%2004252019%20JS.pdf); [Springfield](https://www.springfield-ma.gov/audit/fileadmin/auditor/Internal_Audit_Reports/Fiscal_Year_2023/Payroll_Audit_Report.pdf)) **[Documented, snippet]**. This is a direct challenge to the product. **A traceability tool cannot trace a requirement that was never written down.** Where rules live in people's heads, the Workbench would only report "configuration with no linked requirement". That finding is useful, but it is not the advertised value **[Inference]**.

### Where the evidence is thin, and what that means

**No practitioner source was found that describes, let alone quantifies, manual cross-referencing between workbooks, exports, tests and tickets in UKG projects.** The implementation-lifecycle research says so outright: searches for traceability matrices, workbook-to-tenant reconciliation and time spent returned only release notes and marketing. The closest evidence is a partner remark that configuration updates are "frequently missed during the rush to go live" ([Argano](https://argano.com/insights/articles/best-practices-for-optimizing-ukg-pro-wfm-after-golive.html)) **[Vendor claim, snippet]**. A healthcare advisor also says design teams overlook things and testers should include people outside the configuration sessions ([Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/7-things-worth-getting-right-before-your-ukg-pro-wfm-implementation-kicks-off/)) **[Vendor claim, snippet]**. Reddit, the UKG Community and LinkedIn were not reachable, so the user-report tier is essentially empty.

The quantitative evidence is weak. The UKG/KPMG survey (38% of large-employer leaders report $1M–$5M in annual "payroll leakage") is **vendor-sponsored**, defines leakage broadly, and does not measure configuration error ([BusinessWire](https://www.businesswire.com/news/home/20260331209752/en/UKG-and-KPMG-Nearly-40-of-Employers-Suffer-Millions-of-Dollars-in-Preventable-Losses-Annually-Due-to-Global-Payroll-Errors)) **[Vendor claim]**. It should not appear in any pitch as evidence for this product. The December 2021 Kronos Private Cloud ransomware outage and its wage settlements ([AHA H-ISAC](https://www.aha.org/h-isac-reports/2021-12-13-h-isac-tlp-white-kronos-private-cloud-kpc-ransomware-incident-causes); [HR Dive, Cargill](https://www.hrdive.com/news/court-approves-cargill-settlement-kronos-ransomware-outage/702068/)) were an **availability incident, not a configuration error**. They are not evidence for this product either **[Inference]**.

The structural case is still reasonable. UKG states that **validating every release is the customer's responsibility** ([UKG blog](https://www.ukg.com/blogs/ukg-blog-post/make-ukg-dimensions-changes-confidence)) **[Documented/vendor, snippet]**. Configuration lives in the tenant while design lives in documents. And no documented setup-change audit trail was found in the public API (see section 3). So reconciliation work must happen somewhere **[Inference]**. But "must happen" is a hypothesis to test with interviews, not a finding.

### Personas, ranked by evidence of need

| Persona | Job the Workbench serves | Evidence of the need | Notes |
|---|---|---|---|
| Implementation consultant (partner or UKG) | Design-vs-build reconciliation, coverage before UAT | Partner remarks only ([Argano](https://argano.com/insights/articles/best-practices-for-optimizing-ukg-pro-wfm-after-golive.html)); SOW puts Phase 1 at ~4 months ([UKG SOW](https://www.ukg.com/sites/default/files/2026-04/UKG-Pro-WFM-Standard-SOW-2026-04-03-English.pdf)) [Documented, snippet] | Partners sell labour. A tool that cuts hours must improve fixed-fee margin or quality to be bought [Inference] |
| Customer WFM administrator / support engineer | "What does this change touch?" after go-live; release validation | UKG puts release validation on the customer [Documented, snippet]; audit cases above | Likely the clearest buyer of change impact [Inference] |
| Migration engineer (WFC→Pro WFM) | Mapping evidence, rebuilt-integration coverage | Partners describe migration as a rebuild ([Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/)) [Vendor claim] | Time-limited window (section 4) |
| Delivery lead | Coverage and open-gap view across a project | No direct evidence | A view on top of the other personas, not a separate product |
| Administrator (security) | Access-profile review | No evidence found for access misconfiguration incidents | Do not prioritise |

## 3. UKG Pro WFM exposes configuration through documented APIs, but not as a portable export

### What is verified at primary level

The most important correction to the earlier notes is good news. **Pro WFM setup objects can be read through documented REST operations.** The v1-to-v2 replacement table on developer.ukg.com lists read paths that include `/v2/timekeeping/setup/pay_codes`, `/v2/timekeeping/setup/payrules`, `/v2/timekeeping/setup/work_rules`, `/v2/timekeeping/setup/accrual_profiles`, `/v2/timekeeping/setup/employment_terms`, `/v2/timekeeping/setup/deduct_rules`, `/v2/scheduling/setup/schedule_groups` and `/v2/commons/labor_categories` ([Version 2 resources](https://developer.ukg.com/wfm/docs/version-2-resources-and-operations-doc)) **[Documented, primary-read]**. The API reference also lists resource groups for Overtime Rules, Combination Rules, Combined Paycodes, Paycode Distributions, Function Access Profiles, Generic/Paycode/Work Rule Data Access Profiles, Locations and Payroll Job Maps. Many of these have create, update and delete siblings ([API reference](https://developer.ukg.com/wfm/reference)) **[Documented, primary-read, titles only]**. Only the paths named above should be cited. The reference page is rendered by JavaScript, and response schemas were not visible.

One configuration relationship is documented in UKG's own words. "Employment terms are used to group employees who share a number of pay policies, including pay rule, accrual profile, cascading profile, holiday profile, and timeoff rule." The sample `employment_terms` response shows effective-dated versions with nested `payRule`, `accrualProfile`, `holidayProfile` and `workHours.workHourDef[].payCode` references ([Employment Term Assignments](https://developer.ukg.com/wfm/docs/employment-term-assignments-doc)) **[Documented, primary-read]**. Function Access Profiles contain access control points, and Generic Data Access Profiles "divide configured pay rules and accruals data among different business units" ([Configure access for a person](https://developer.ukg.com/wfm/docs/configure-access-for-a-person-doc)) **[Documented, primary-read]**. This primary reading **corrects an earlier inference**. Work rule profiles appear in the employee Timekeeping template, not on the employment term.

Several other relationships remain **unverified at primary level**. These include pay rule to work rule, work rule to overtime and zone rules, paycode to payroll mapping, and work rules as combinations of building blocks. All rest on help-page snippets ([Pay rules reference](https://library.ukg.com/Prebuilt/newgen/WorkforceMgmt/Content/WFMPayRules-r_x52705.html); [Payroll to Paycode Mappings](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/configure_payroll_to_paycode_mappings.html)) **[Documented, snippet]**. The graph must not hard-code any of them as truth.

### Five gaps that shape the product

First, **no configuration-wide bulk export API was found**. Bulk operations exist for transactions (punches, paycode edits, payroll export), and it is unverified whether "Bulk Downloads" covers setup data ([API reference](https://developer.ukg.com/wfm/reference)) **[Documented, primary-read, titles only]**. A snapshot therefore means many per-resource GET calls.

Second, **no setup-change audit trail was found in the public API**. Audit operations cover attendance, leave, schedules and forecasting, not pay rules or paycodes ([API reference](https://developer.ukg.com/wfm/reference)) **[Documented, primary-read]**. If history matters, the product must keep its own snapshots **[Inference]**. This is a genuine opening.

Third, **Setup Data Manager (SDM) is the native configuration-transport tool, and its export format is undocumented** in anything readable. Search summaries say SDM copies setup data tenant-to-tenant "using the system's REST APIs", exports to a file, and offers "Compare setup items … on your source and target servers" ([Copy Setup Data](https://sso-hlp01.mykronos.com/help/en_US/Content/SDM/CopySetupData.htm)) **[Documented, snippet only; host blocked]**. Older customer-hosted help mentions same-version requirements and GUID validation ([customer-hosted help](https://emstelestaff.albertahealthservices.ca/help/Content/Access/Components/IM_c.htm)) **[Documented, snippet, possibly WFC-era]**. **Do not plan to parse SDM files without a UKG-provided specification.** This is a technical dead end until one appears **[Inference]**.

Fourth, **webhooks exist, but whether they include setup-change events is unknown**. The event catalogue page was not read ([WFM Webhook Events](https://developer.ukg.com/wfm/docs/wfm-webhook-events)) **[Documented, primary-read; catalogue unread]**.

Fifth, **no numeric rate limit is published**. Throttling returns HTTP 429. The documented limits are per-request caps, for example Hyperfind responses of at most 50,000 rows and Information Access of at most 500 employees ([Limits](https://developer.ukg.com/wfm/docs/limits-doc)) **[Documented, primary-read]**.

### Platform and release facts

Pro WFM runs on Google's public cloud, ships year.R1/R2 releases with numbered Express Upgrades, and publishes release notes with resolved issues, known issues and implementation considerations ([2024R2 release notes](https://hlp02.gss.mykronos.com/help/en_US/Content/Resources/ReleaseNotesPDFs/ProWFM_2024R2_ReleaseNotesRevT.pdf)) **[Documented, snippet]**. Customers get one production tenant and one partial-copy non-production tenant by default ([Non-production environments DS, 2023](https://www.ukg.com/sites/default/files/2023-09/DIY0365-USv2-UKG-Pro-WFM-non-Production-Environments-DS.pdf)) **[Documented, snippet, dated]**. Snapshot comparison is therefore mostly a two-environment problem, plus history over time.

### Workforce Central is a different product

WFC used an XML Developer's Toolkit API and Workforce Integration Manager (WIM) interface files ([WFC 8.1 DTK reference, unofficial copy](https://www.scribd.com/document/696889274/WFC81-IntegrationMgrDTKRef)) **[Documented, snippet, unofficial copy]**. It used labour levels rather than Pro WFM's business structure. A customer reports that business structure is "the backbone of Dimensions" and took four iterations to settle ([Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/)) **[User report via partner blog]**. UCSB documents that a Reports To field replaced ACN and TMAA for manager approval ([UCSB](https://timekeeping.ucsb.edu/ucsb-timekeeping-refresh-project)) **[Documented, customer]**. No field-level WFC-to-Pro WFM mapping documentation was found. This confirms the repo rule that the two products are separate profiles, and that **name matches across them are hints, not mappings**.

## 4. The lifecycle has clear handoffs, and the WFC migration window is closing

UKG's own Launch model has five phases: Welcome, Requirements, Build, Test, Go Live ([UKG Pro: Creating Your Project Team](https://library.ukg.com/documents/Launch/UKG_Pro_Creating%20Your%20Project%20Team.pdf)) **[Documented, snippet]**. "Discover/Design/Build/Test/Deploy" is partner usage, not UKG's model. The 2026 Standard SOW puts customer UAT in the Test phase and a typical Phase 1 at **four months from kick-off** ([UKG SOW](https://www.ukg.com/sites/default/files/2026-04/UKG-Pro-WFM-Standard-SOW-2026-04-03-English.pdf)) **[Documented, snippet]**. UKG's performance-testing sheet runs tests before UAT and again on the signed-off go-live configuration ([UKG performance testing](https://www.ukg.com/sites/default/files/2023-09/DIY0225-UKG-Dimenions-Performance-Testing.pdf)) **[Vendor claim, dated]**. A secondhand podcast account says two clean parallel payroll runs were required before go-live ([podcast](https://working-smarter-cafe.buzzsprout.com/1629862/9630643)) **[User report, single, dated]**.

Mapping the product onto this lifecycle gives four pain points. Requirements and design, captured in documents, must be reconciled with what is built in the tenant. SDM promotion between tenants carries a documented warning to keep the source aligned with production to avoid overwriting it ([SDM publish](https://sso-hlp02.gss-kcfn.mykronos.com/help/setup/Content/SDM/PublishTool.htm)) **[Documented, snippet]**. Testing is where design gaps surface. And post-go-live, release "implementation considerations" must be matched by hand against the tenant **[Inference]**. Each pain point is a handoff between artefacts held in different tools. That is the Workbench's natural territory. But **the hours spent at each handoff are unknown**, and no source supports a number. Published implementation cost figures range from $48k–$127k to "0.8–1.4x annual subscription" and are inconsistent partner marketing ([Soon.works](https://soon.works/blog/what-a-ukg-implementation-actually-costs); [Outsail](https://www.outsail.co/post/how-much-does-ukg-cost-in-2026)) **[Vendor claim, low reliability]**.

On migration, the earlier notes agree with each other but are all secondary. WFC retirement was announced on 20 October 2022. Kronos Private Cloud support ended on **31 December 2025**. On-premises support ends on **31 March 2027** ([RSM](https://www.rsmus.com/insights/technology/ukg/ukg-workforce-central-support-is-ending-do-you-have-a-plan); [Healthcare IT Leaders](https://healthcareitleaders.com/blog/ukg-workforce-central-wfc-end-of-life)) **[Vendor claim/partner, snippet; UKG primary page blocked]**. As of 18 November 2026 that is about four and a half months away. Partners describe the migration as rebuild-heavy. Timecard and schedule history does not transfer. WIM integrations must be rebuilt on the Boomi-based Integration Hub ([Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/); [Workaxle](https://www.workaxle.com/blog/kronos-workforce-central-end-of-life-migration)) **[Vendor claim]**. UC San Diego moved on 1 February 2026, and UC Berkeley phased complex 24-hour-shift groups in May 2026 ([UCSD](https://rrsshr.ucsd.edu/timekeeping/index.html); [Berkeley](https://caltime.berkeley.edu/caltime-replacement-project)) **[Documented, customer]**. The implication is blunt. **A "Migration Assurance Factory" built from today would reach market after most migrations have finished or committed to a partner.** It survives only as a narrow mapping-evidence ledger for late movers, and only if real WFC exports can be obtained **[Inference]**.

## 5. UKG's own tools and test vendors cover adjacent slices, but none builds an evidenced configuration graph

The pattern from other ecosystems is the most useful lens. **The platform owner ships a basic compare, and third parties win on depth, governance and test linkage.** Workday ships Tenant Compare ([Workday doc](https://doc.workday.com/admin-guide/en-us/manage-workday/tenant-configuration/implementation-tools/customer-central/tenant-compare/compare-tenant-configuration-data.html)) **[Documented, snippet]** and Kainos sells audit and test on top of it ([Kainos Smart](https://www.kainos.com/workday/products/smart)) **[Vendor claim]**. Salesforce has a beta dependency API that third parties such as Gearset and Elements.cloud extend ([Gearset](https://gearset.com/blog/salesforce-impact-analysis/); [Elements.cloud](https://elements.cloud/understand-salesforce-complexity)) **[Vendor claim]**. SAP has Tricentis LiveCompare ([Tricentis](https://www.tricentis.com/products/impact-analysis-livecompare)) **[Vendor claim]**. Each analogue depends on a vendor metadata API. UKG's equivalent is its setup REST API, which is documented but contract-gated (section 10).

Every competitor assessment below is based on search snippets. **No vendor product page, demo or datasheet was read in full**, so "does not appear to do" means "no evidence found in limited search", not "confirmed absent".

| Product | What it does | What it does not appear to do | Overlap with Workbench | Worth building the overlapping part? | Redundancy risk |
|---|---|---|---|---|---|
| **UKG Setup Data Manager** (native) | Copies setup data tenant-to-tenant and to file; per-item "Compare setup items"; changes logged in the audit trail as if entered manually ([SDM](https://hlp03.gss.mykronos.com/help/HCM/administration/Setup_data_manager_SDM/using_setup_data_manager_368192.html)) [Documented, snippet] | Snapshot history, dependency-aware or semantic diff, provenance, test linkage | Environment compare / drift (D) | Only snapshot history plus dependency-aware diff. Never rebuild copy/promote | **High.** UKG owns the data and could extend compare cheaply |
| **UKG Bryte AI / Bryte Agents** | Assistive and agentic AI for HR, payroll, scheduling and frontline decisions ([Nucleus, Spring 2026](https://nucleusresearch.com/wp-content/uploads/2026/06/26107-UKG-Spring-Global-Analyst-Day-2026-updates.pdf)) [Vendor claim, analyst summary] | No evidence of dependency graphs, drift or requirement traceability | Explanations and diagnostics (F) | No generic Q&A. Only explanation of computed, evidenced results | **High** for generic explanation; low for artefact-grounded provenance |
| **UKG "Configuration Assistant"** | Reported AI aid that "significantly reduces build time" during implementation ([Nucleus, Aspire 2025](https://nucleusresearch.com/wp-content/uploads/2025/11/z192-UKG-Aspire-Global-Analyst-Day-2025-updates.pdf)) [Vendor claim via analyst; no UKG doc found] | Unknown | Possibly B and F | Cannot judge until UKG documentation is obtained | **Unknown, potentially the biggest threat** |
| **"UKG in Claude"** (reported beta, Oct 2026, MCP) | Plain-language questions on schedules, hours, pay rules and labour policies, with permission-limited actions ([BusinessWire](https://www.businesswire.com/news/home/20261020356990/en/UKG-in-Claude-Makes-AI-Work-Beyond-the-Chat)) [Vendor claim, unverified: press release unreachable] | No evidence of covering configuration dependencies or artefacts outside UKG | F | Do not build a chat interface to UKG data | High for conversational access to tenant data |
| **Workforce Intelligence Hub** | Unified workforce data; API usage monitor; **MVP for a limited set of US customers** ([WIH](https://developer.ukg.com/proplatform/docs/welcome-to-workforce-intelligence-hub)) [Documented, primary-read] | Configuration engineering | Low | No | Low |
| **UKG Compose** | Low-code workflow automation on n8n, for opted-in US/CA customers ([Compose](https://developer.ukg.com/proplatform/docs/welcome-to-ukg-compose)) [Documented, primary-read] | Configuration analysis | A customer could script narrow checks | No (workflow builder is out of scope) | Low |
| **Pro WFM Data Hub** | Data pipelines to analytics; configuration portal with job and audit history ([Data Hub](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/data_hub_configuration_portal_2.html)) [Documented, snippet] | Configuration dependencies | Low | No | Low |
| **Opkey** | No-code UKG test automation; per-update "Impact Analysis" flagging affected processes and tests; claims WFC and Dimensions coverage ([Opkey](https://www.opkey.com/kronos)) [Vendor claim] | No evidence of a configuration-object graph or customer-change impact | E and D (test selection by impact) | Ingest Opkey test inventories. Do not execute tests | **Medium.** Already markets impact analysis |
| **TestAssure** | Automated WFM regression testing plus managed services; UKG partner ([UKG blog](https://www.ukg.com/blogs/ukg-blog-post/make-ukg-dimensions-changes-confidence); [TechIntelPro](https://techintelpro.com/news/hr/workforce-management/testassure-launches-wfm-regression-testing-to-cut-payroll-risk)) [Vendor claim] | Search found no environment configuration comparison | E | Ingest results. No execution | Medium-low |
| **Tricentis / Worksoft** | Generic UKG test automation pages ([Tricentis](https://tricentis.com/solutions/ukg-testing); [Worksoft](https://www.worksoft.com/applications/ukg)) [Vendor claim]; LiveCompare is SAP-only | UKG impact analysis | Low | Learn from LiveCompare's tiered output | Low today; high if Tricentis ports LiveCompare |
| **Boomi** | Powers UKG Integration Hub; Meta Hub "Universal Lineage" is design-time with an open ingest API ([Boomi blog](https://boomi.com/ja/blog/introducing-universal-lineage-in-boomi-meta-hub/)) [Vendor claim] | UKG configuration semantics | Integration lineage (C) | Import integration definitions as nodes. No runtime monitoring | Low-medium |
| **ServiceNow** | UKG spoke for employee self-service; CMDB impact analysis that uses an LLM workflow with confidence and a 250-CI cap ([ServiceNow impact](https://www.servicenow.com/docs/r/q4dSP2Icgr1SFv5wanVXvQ/~p6mlH3iSpQH9FQYNZo24w)) [Documented, snippet] | UKG configuration items in the CMDB | "Change governance" perception | Link out to change records. No ticketing | Low for config semantics |
| **Jama / Polarion** (requirements tools) | Requirement-test traceability with "suspect links" that a human clears ([Jama](https://www.jamasoftware.com/blog/5-ways-jama-connect-makes-traceability-easy/); [Polarion](https://docs.plm.automation.siemens.com/content/polarion/20/help/en_US/user_and_administration_help/administrators_guide/configure_work_item_linking.html)) [Documented, snippet] | UKG configuration objects | **E, generic traceability** | Only the UKG-configuration end of the trace | **Medium.** Generic traceability is a commodity |
| **Partner consultancies** (RSM, Surety, Argano, CloudApper and others) | Migration and assessment services sold as labour ([Surety](https://www.suretysystems.com/consulting/kronos/); [PeopleTech](https://resource.peopletech.com/workshops/ukg-wfc-migration-to-pro-wfmdimensions)) [Vendor claim] | Productised configuration intelligence (none found) | B, G | They are channel and customer, not only competitor | Low as product. **Their private spreadsheets and scripts are the real incumbent** |

The honest positioning claim is narrow. **No third-party, UKG-specific configuration dependency graph product was found in limited search.** Native SDM and test vendors cover adjacent slices, and unindexed consultancy accelerators almost certainly exist **[Inference]**. "No competitor does this" must not appear in any material.

## 6. The canonical data model separates claims, evidence and review

The model follows the W3C PROV vocabulary of Entity, Activity, Agent and derivation ([PROV overview](https://www.w3.org/TR/prov-overview/Overview.html)) **[Documented, snippet]**. It is held in plain relational tables, not an RDF store **[Inference]**. Its central design move is to keep **what is claimed** (an entity, attribute value or relationship) apart from **where it came from** (evidence locators) and **who has vouched for it** (review events).

| Concept | Purpose | Key fields (design, not UKG schema) |
|---|---|---|
| Engagement | Tenancy and isolation boundary | engagement_id; every row carries it; row-level security |
| SourceDocument | Immutable uploaded file | sha256, media type, size, product_profile (`ukg_pro_wfm`, `workforce_central`, `unknown`), fictional/synthetic flag, uploaded_by |
| IngestionRun (PROV Activity) | How facts were produced | parser name and version, rule-set version, model id and prompt hash if an LLM was used, start and end, status |
| Agent (PROV Agent) | Who or what acted | type: parser, rule, llm, human; a human has an identity |
| Fragment (IR) | Normalised content unit | type (table row, cell, paragraph, XML node, JSON node), text or value, locator |
| EvidenceLocator | Typed pointer into the source | document version, page plus bbox; sheet, row and cell (or merged-range anchor); XPath; JSON pointer; character offsets; quoted text hash |
| Snapshot | A configuration state at a time | environment label, captured_at (recorded time), valid-from/valid-to where the source states effective dates |
| Entity / EntityVersion | Configuration objects, requirements, tests, defects, integrations, mappings | stable key, type (closed list per profile), product_profile, one version per (key, snapshot) |
| AttributeValue | A field value with evidence | entity version, name, value, unit, evidence ids, `assumption` flag |
| Relationship | Typed edge | from, to, type (closed list), status OBSERVED, INFERRED or CONFIRMED, method (explicit reference, name-match rule id, LLM), confidence (INFERRED only, stored as uncalibrated) |
| Evidence link | Many-to-many from claims to locators | one claim can rest on many locators |
| ReviewEvent (append-only) | Status transitions | reviewer identity, prior and new status, reason, timestamp, evidence shown |
| CoverageRegistry | What was *not* modelled | per document and type: parsed, partially parsed, unsupported; edge types with no extractor |
| ChangeSet / ImpactRun | Inputs and outputs of analysis | change set as an IR diff; graph snapshot ids; rules version; result hash |

Five design rules carry the weight. **Enforce "AI never sets CONFIRMED" in the database**, with a constraint that requires a human agent on any transition to CONFIRMED, not only in API code. The milestone plan routes promotion through an endpoint, and a database check backs it up **[Inference]**. **Mark confirmed edges "needs re-review" when their source version changes**, borrowing Jama's human-cleared suspect-link mechanism ([Jama](https://www.jamasoftware.com/blog/5-ways-jama-connect-makes-traceability-easy/)) **[Documented, snippet]**. **Version entities by snapshot rather than mutating rows**, keeping the time a configuration was effective apart from the time it was recorded. This bitemporal advice is background knowledge, not sourced in the notes **[Inference]**. **Model coverage explicitly.** Salesforce's own dependency API is beta, capped at 2,000 records per query and excludes reports ([Salesforce docs](https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_metadatacomponentdependency.htm)) **[Documented, snippet]**. Even vendor dependency data is incomplete, so "not modelled" must be a first-class state. And **OBSERVED means "the source states it", not "it is semantically correct"**. A dangling ID is itself a finding.

## 7. PostgreSQL adjacency tables carry the graph at plausible scale

Store the graph as node and typed-edge tables in the same PostgreSQL database as the evidence and review tables. Traverse it with a bounded, ordered breadth-first search, either in Python over a loaded subgraph or as a recursive CTE with the `CYCLE` clause, available since PostgreSQL 14 ([vb-consulting](https://vb-consulting.github.io/blog/recursion-postgresql/part3-cycle-detection)) **[Documented, snippet]**. Every alternative brings a concrete cost. **Neo4j** Community is GPLv3, and Enterprise needs a commercial licence for closed-source use ([Neo4j licensing](https://neo4j.com/licensing/?ref=blog)) **[Documented, snippet]**. **Kuzu's repository is archived** after Apple's acquisition ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)) **[Documented via news]**. **Apache AGE 1.8.0** supports only PostgreSQL 18 ([EDB release notes](https://www.enterprisedb.com/docs/pg_extensions/apache_age/rel_notes/apache_age_1.8.0_rel_notes/)) **[Documented, snippet]**. **SQL/PGQ** was committed to PostgreSQL master in March 2026, so it is likely PostgreSQL 19 and not yet available ([pgsql-committers](https://www.postgresql.org/message-id/E1w247I-0000Tk-2Y%40gemulon.postgresql.org)) **[Documented, snippet]**. A separate graph store would also force dual writes against the provenance tables, breaking foreign-key integrity between an edge and its evidence **[Inference]**.

Scale is an assumption, not a fact. **No source gives the size of a real UKG tenant's configuration.** An estimate of 10³–10⁵ nodes and 10⁴–10⁶ edges per tenant, excluding employees, is a guess to check against the first real export **[Inference]**. Benchmarks are anecdotal and conflicting. One write-up reports a 6-hop indexed recursive CTE on a 200K-node graph in under 2 ms ([Postgres-as-graph](https://landing-page-3tt.pages.dev/blog/postgres-as-a-graph-database/)) **[Vendor claim/anecdote, weak]**. The real risk is **hub nodes**: one paycode referenced by thousands of objects inflates path enumeration. So test on a deliberately hub-heavy synthetic graph, keep a visited set, and cap depth **[Inference]**.

Make traversal semantics data, not code. An edge-type table states, for each relationship type, whether it propagates impact and in which direction. Results are sorted by stable keys so that the same inputs always give byte-identical output. A second, independent traversal (for example SQL against an in-memory Python graph) is run in tests to catch disagreement **[Inference]**. For display, React Flow suits bounded impact subgraphs of tens to a few hundred nodes. A maintainer comment suggests around 1,000 nodes as a practical ceiling ([React Flow issue summary](https://lightrun.com/answers/wbkd-react-flow-performance-drop-when-panning-or-zooming)) **[User report]**. Never render the whole tenant. Revisit a graph database only if measured p95 impact queries miss target at real scale **[Inference]**.

## 8. Change impact must report candidates, tiers and blind spots, never a pay delta

### The synthetic 40 → 37.5 scenario and what it actually needs

*Harborline Logistics and its weekly overtime threshold change from 40 to 37.5 hours are fictional. Nothing here describes how UKG evaluates overtime.* To produce a useful candidate impact set, the scenario needs the following information **[Inference]**:

- **The threshold itself.** Its value, unit, period definition (workweek start, or pay period versus week) and effective dates, with evidence.
- **The object that contains it.** The milestone plan puts it on work rule `WR-OT-WEEKLY`. That is a fictional modelling choice. UKG's API reference lists **"Overtime Rules" as their own resource group** ([API reference](https://developer.ukg.com/wfm/reference)) **[Documented, primary-read, title only]**, and the containment path in real Pro WFM is unverified. The fixture should say so.
- **What references the container.** Paycodes, combination rules and other rules, each with an edge and evidence.
- **Assignments.** Which employment terms, pay rules, work rule profiles and org nodes carry it. Only the employment-term-to-pay-rule link is primary-documented.
- **Downstream consumers.** Payroll export mappings and hours buckets, and integration specifications.
- **Requirements that cite "40"**, including a source CBA or policy clause if one exists.
- **Test scenarios with expected results hard-coded to 40.** These are the most likely silent breakages, and they are deterministically findable by value search over test artefacts.
- **Past defects touching the rule.**
- **Each environment snapshot**, to show whether the value already differs between non-production and production.

Artefacts cannot reveal the following, and the report must list it every time. They cannot show **evaluation order and precedence between competing rules**, how period boundaries, rounding and units are applied, interaction with daily overtime, holidays, accruals or retro-adjustments, or **which employees actually reach the threshold**. Nor can they show hard-coded values inside downstream payroll code that was never exported, or whether 37.5 complies with statute or a union contract, which is a legal question. Most of all, they cannot give **the money or hours delta**. Those need a non-production tenant, a rule simulation, or a parallel-pay comparison. **The product must never output a pay-impact number** **[Inference]**.

### Representing uncertainty

Report three tiers per impacted node, each with its shortest path, hop count and evidence ids:

- **Established impact candidate:** reached by at least one path made only of established edges (human-accepted, or unreviewed with an explicit source reference).
- **Possible impact candidate:** every path contains a rule- or LLM-based unreviewed edge. Show the **weakest edge's** basis, method and confidence.
- **Not modelled:** a boundary where coverage is missing. Examples are an integration whose target configuration was not supplied, an `unknown` product profile, an untyped edge, a depth cut-off, or an unparsed document.

Revision 2 adds two non-impact categories so that reachability is never mistaken for impact: **upstream constraints** (one hop against the propagation direction from each changed object) and **context** (non-propagating links such as documents and past defects). Traversal is **directional**, following a declared propagation rule per relationship type. The full semantics are in `docs/architecture/impact-propagation.md`.

Do **not multiply confidences into a probability**. The edges are not independent and the scores are uncalibrated. Weakest-edge is simple, deterministic and explainable **[Inference]**. LiveCompare and Panaya add usage-frequency weighting ([LiveCompare docs](https://docs.tricentis.com/livecompare-2026.1/content/smart_impact_learning_app.htm); [Panaya](https://success.panaya.com/docs/how-to-analyze-impact-and-risk.md)) **[Vendor claim]**. Usage data does not exist in design documents, so the Workbench must not imitate their "risk scores". It should present coverage gaps as facts instead.

Terminology (resolved in revision 2): impact tiers were once called "confirmed impact", which collided with the CONFIRMED relationship status (human-reviewed). The plan and the `configuration-change-impact-review` skill now say "established" and "possible" impact candidates, plus "not modelled".

### Independent validation

The literature sets a sobering baseline. One study of dynamic change-impact techniques found even the most cost-effective method averaged **38–50% precision and 50–56% recall** ([Buffalo study](https://researchconnect.buffalo.edu/en/publications/a-comprehensive-study-of-the-predictive-accuracy-of-dynamic-chang/)) **[Research]**. Combining static techniques improves on either alone ([comparative study](https://www.bohrium.com/paper-details/static-change-impact-analysis-techniques-a-comparative-study/814604185264717824-2502)) **[Research]**. These are software studies, and **no impact-analysis research specific to HR or WFM configuration was found**.

Validation should therefore run on five layers **[Inference]**:

- **Golden expected impact sets.** Authored by hand, by someone other than the person who wrote the fixture generator, so the test is not circular.
- **Mutation tests.** Delete or alter an edge and assert that the impact set changes as predicted (recall). Add decoy non-propagating edges and assert that it does not (precision).
- **Differential testing.** Compare two independent traversal implementations.
- **Property tests.** Idempotent ingestion, order-independence and guaranteed termination on cycles.
- **Real outcomes, later.** Precision and recall against actual regression or parallel-pay results from a real project, which is the only validation that would justify an accuracy claim.

## 9. Deterministic code owns structure; AI proposes, narrates and never confirms

| Responsibility | Owner | Output status | Why |
|---|---|---|---|
| File validation, parsing, cell/page/XPath locators | Deterministic | n/a | Structural truth; must be reproducible |
| Explicit ID references in workbooks, XML/JSON parent-child links, mapping rows, test-to-requirement columns | Deterministic | OBSERVED | The source states the link; dangling IDs become findings |
| Exact-name matches of configuration names in prose; ID patterns ("REQ-123") inside text | Deterministic rule | INFERRED (rule id plus span) | High precision but not certain |
| Requirement-to-configuration links from prose, implied design dependencies, defect root-cause hypotheses | LLM-assisted | INFERRED only, in a review queue | Relationships are ambiguous in prose |
| Alias and fuzzy entity matching | LLM or similarity, as a suggestion | INFERRED | Matching names are hints |
| Snapshot diff, impact traversal, coverage gaps, orphan and dangling detection | Deterministic | Report | Must be byte-identical across runs |
| Narrating a computed impact report | LLM, constrained | Text that cites node and evidence ids | It may not add, remove or rank impacts |
| Accepting or rejecting a relationship | **Named human only** | review state accepted or rejected (displayed as CONFIRMED when accepted) | Enforced in the database (`docs/architecture/relationship-model.md`) |

The case for capping AI at INFERRED is empirical. In the DEPTH paper, one model predicted a relation in **96.9% of no-relation cases** on a scientific benchmark ([arXiv 2508.14391](https://arxiv.org/pdf/2508.14391)) **[Research; one model, non-enterprise data, do not extrapolate]**. TraceLLM found that LLM traceability over-predicts links without domain context and is sensitive to prompting ([arXiv 2602.01253](https://arxiv.org/pdf/2602.01253)) **[Research]**. Studies of citation generation show that models fabricate parts of otherwise valid references ([arXiv 2602.21059](https://arxiv.org/pdf/2602.21059)) **[Research]**. So **a citation shows where a claim came from but does not prove it**.

Revision 2 proposes separating a relationship's **evidence basis** (explicit source, deterministic rule, LLM suggestion; one claim per source, each with immutable locators) from its **review state** (unreviewed, accepted, rejected, superseded). OBSERVED, INFERRED and CONFIRMED become derived display labels. See `docs/architecture/relationship-model.md`; decision D3. Policy note: evaluating extraction models on real customer artefacts would need customer and UKG written consent (Developer Policy §4), so evaluation sets stay synthetic.

Five approval controls follow **[Inference]**:

- **Constrained output.** Structured output with a closed edge-type list and a required source span.
- **Code-checked spans.** A verifier rejects any proposal whose quoted span does not exist verbatim at the stated location.
- **Full recording.** The model id, prompt hash and run are recorded for every proposal.
- **Human-only confirmation, with history.** CONFIRMED is set only by a named reviewer through an append-only review event, and confirmed edges revert to "needs re-review" when their source changes.
- **Evaluation and fallback.** Recall-weighted (F2) evaluation plus a hand-checked precision sample on labelled synthetic data. A **no-LLM mode** that still produces every deterministic result.

**Where RAG is justified:** retrieval over free-text prose that has no structure, such as runbooks, defect descriptions, design narratives and the "implementation considerations" sections of release notes. Even there it is a retrieval aid that feeds INFERRED proposals. **Where it is not justified:** configuration objects, IDs, values and relationships. These are structured, so keyword search, exact lookup and graph traversal answer more accurately and reproducibly. PostgreSQL full-text search comes first. Add pgvector only if users measurably fail to find prose by keyword. Note that native `ts_rank` is not BM25 ([ParadeDB](https://paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)) **[Vendor claim]**. A generic "ask anything about your UKG tenant" chatbot competes head-on with Bryte, the Developer Hub's GenAI search ([GenAI Search](https://developer.ukg.com/general/docs/genai-search)) **[Documented, primary-read]** and the reported "UKG in Claude". It would also invert the product's evidence-first rule.

## 10. Security and UKG access: customer-supplied files are the only clear path today

### What UKG documents about API access (primary-read)

Pro WFM supports three token flows: Authorization Code (preferred for new clients), ROPC, and **Client Credentials, "tailored for system-to-system communications"**. Each client is associated with a Function Access Profile that limits its access ([UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc)) **[Documented, primary-read]**. The documentation fixes several constraints:

- **The customer creates the credentials.** They are made in the customer's tenant (Administration > Application Setup > Common Setup > Client Management, or the Developer Console where UKG Authentication is enabled), and they are **tenant-specific**. A non-production credential cannot obtain a production token, and a lost secret cannot be recovered.
- **Client Credentials calls carry no user identity.** "User-specific audits or user-specific context is not supported for Client Credential."
- **Tokens are short-lived.** Access tokens expire after 30 minutes and refresh tokens after 8 hours, "subject to change without notice".
- **Network protections stay on.** "Requests to whitelist IP ranges or relax authentication protections are not supported."

All from [UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc) and [Developer Console](https://developer.ukg.com/proplatform/docs/developer-console-quick-start) **[Documented, primary-read]**.

The Developer Hub says it is free and public. All published API resources except partner-only ones (background check, benefits) "are available for customers & 3rd parties to use in building integrations" ([Developer Hub FAQ](https://developer.ukg.com/general/docs/ukg-developer-hub-faq)) **[Documented, primary-read]**.

### What the UKG Developer Policy requires (primary-read, revision 2)

The policy governs UKG Data Interfaces: APIs, SDKs, webhooks, the data warehouse and the MCP Gateway. It is incorporated into the MLA or MSA, and the MLA or MSA controls if the two conflict ([Developer Policy](https://developer.ukg.com/proplatform/docs/developer-policy) §1) **[Documented, primary-read]**. Key requirements:

| Area | Requirement (verbatim or close paraphrase) | Effect on the Workbench **[Inference]** |
|---|---|---|
| Approved interfaces, registration | Only UKG-provisioned interfaces; "register their access with UKG using an active, approved credential" (§2) | No scraping or unofficial access; register before any API use |
| Credentials and consent | Production APIs via "Partner Portal credential + Customer consent"; customer-specific credentials need "explicit customer consent (via a UKG-approved method)"; 90-day rotation for credentials with PII access (§2–3) | The API route needs a partner-grade onboarding path |
| Competitive clauses | Prohibits "Creating a competitive product or service to UKG's offerings" and using UKG data to "inform products that compete with UKG offerings" (§4) | **Undetermined. Needs Legal (D1).** "Offerings" is undefined |
| Cross-tenant aggregation | Prohibited without a Data Sharing Agreement and consent from all tenants, "anonymized or aggregated benchmarking" included (§4) | No cross-customer pattern libraries or benchmarks |
| AI training and evaluation | Prohibits using Customer Data to "train, fine-tune, or evaluate AI or machine learning models without explicit Customer and UKG written consent" (§4) | Extraction evaluation stays synthetic |
| AI agents | Prohibits systems that "plan, select, or execute sequences of UKG API calls without MCP Gateway registration or explicit UKG authorization"; 12-month agent audit logs (§4, §7) | No agentic UKG access in the roadmap |
| Encryption and residency | TLS 1.2+ (1.3 preferred); AES-256 at rest with FIPS 140-2/3 validated modules on request; processing only in authorised jurisdictions (§5) | Key management and region pinning from the first real deployment |
| Sub-processors | "prior written authorization from UKG" before engaging sub-processors (§5) | Hosting, database and LLM providers each need approval for interface-sourced data |
| Deletion | Delete all copies "including from shared environments, backups, archives, and derivative datasets"; written confirmation on request (§5) | Per-customer isolation and key-based purge; the IR and graph count as derivatives |
| Incidents | Report to UKG Security Operations "within twenty-four (24) hours of discovery" (§5) | An incident runbook is needed before real data |
| Audit and enforcement | UKG may audit logs, encryption, agent designs and sub-processors, and may suspend access "in its sole discretion" (§10–11) | Log retention and an evidence pack |

The policy has drafting defects: the "Credential Sharing" row repeats the AI-agent text, there are broken section references, "Developer" is undefined, and the version is undated. Legal should resolve these.

### Four activity classes and what each needs

| Activity | Policy engaged? **[Inference]** | Needs |
|---|---|---|
| **Synthetic-data development** (Milestone 1) | No Data Interface and no Customer Data | Nothing from UKG to continue building. Legal view on the competitive clause before commercial positioning |
| **Offline processing of authorised customer-supplied artefacts** | Unclear: no Data Interface, but UKG-generated exports are Customer Data, and the customer's MSA governs sharing | **Customer written consent and a DPA**; **Legal clarification** of applicability (D2); sanitisation; per-customer purge. Never designed as a workaround to consent flows |
| **Customer-authorised API integration** (read-only configuration GETs) | Yes | **Written UKG approval** (registration, purpose, sub-processors) and **customer consent via UKG's flow**, plus every operating obligation above |
| **Commercial deployment using UKG customer data** | Yes, across customers | All of the above per customer, plus a **Data Sharing Agreement** for any cross-customer feature, sub-processor authorisations, and a **Legal interpretation** of the competitive clauses |

### What the contracts may say (unverified, provisional)

Earlier notes report, from search summaries only, three restrictions. The **July 2026 MSA** reportedly prohibits programmatic or automated access, "expressly including AI programs and agentic access", without UKG's written authorisation ([MSA PDF](https://www.ukg.com/sites/default/files/2026-07/MSA-2026-07-01-US.EN_.pdf)). The **AUP** reportedly bars bulk extraction, replication and excessive polling ([AUP PDF](https://www.ukg.com/sites/default/files/2026-07/AUP-English-2026-07-01.pdf)). And **API Call Packs Exhibit A** reportedly bars "spiders, crawlers, scrapers or agents" and sets 10 million calls per pack per tenant per month ([API Call Packs SD](https://www.ukg.com/sharepoint/view/01WMTN4D3XI35U4LFZ7BC37IPT6C37O3TV)). **All three are unverified. The documents could not be read, and the "agents" wording comes from a single summary.** The public developer-hub invitation and the reported contract restrictions may both be true at once. Only the clause text and a lawyer can settle what a third-party product may do with customer-provisioned credentials.

Until then, rank access paths by risk **[Inference, not legal advice]**:

1. **Customer-supplied files processed offline.** Lowest risk, though the customer's own confidentiality terms for exports are unchecked.
2. **Customer-run, read-only extraction with customer-provisioned, least-privilege credentials at modest volume.** Ambiguous. Needs legal review and probably written authorisation from UKG.
3. **Automated extraction at scale.** Higher risk under the reported AUP terms.
4. **AI agents acting inside a tenant.** The Developer Policy prohibits these without MCP Gateway registration or UKG authorisation (primary-read). Out of scope.

This matches the repo rule of no live tenant access.

### Security controls the product needs regardless

- **Treat every upload as hostile.** Allow-list types, cap sizes, and cap decompressed size, since DOCX and XLSX are ZIP files ([OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)) **[Documented, snippet]**. Disable external entities with `defusedxml` against XXE, which applies to DOCX, XLSX and XML exports ([OWASP XXE](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html)) **[Documented, snippet]**. Reject macros and external links. Parse in sandboxed, resource-limited workers.
- **Treat every LLM call as data egress.** Redact or pseudonymise before any call, use per-engagement opt-in and a provider allowlist, and keep an audit log of prompt and response hashes. Confirm provider retention terms first: zero-data-retention terms shifted during 2026 ([CX Today](https://www.cxtoday.com/security-privacy-compliance/anthropic-zero-data-retention-enterprise-ai/)) **[Vendor claim/news, inconsistent]**.
- **Isolate engagements.** Put `engagement_id` on every row with row-level security as defence in depth, and design for single-tenant, customer-hosted deployment from day one ([RLS vs schema](https://dev.to/itsjayanth/multi-tenant-postgresql-row-level-security-vs-schema-per-tenant-when-to-use-which-3joe)) **[secondary]**.
- **Decide authentication before any non-synthetic data enters**, as the milestone plan already notes.

## 11. Keep the proposed stack, minus PyMuPDF and plus stricter parsing

| Layer | Proposed | Recommendation | Evidence and reasoning |
|---|---|---|---|
| PDF parsing | PyMuPDF | **Revision 2 decision (D5): pdfplumber 0.11.10 (MIT).** Its dependencies are pdfminer.six (MIT) and pypdfium2 (BSD-3/Apache-2.0, with bundled permissive PDFium licences). pypdf 7.1.0 (BSD-3) was rejected for Milestone 1. In a test on a generated two-page PDF, pdfplumber returned **page-absolute word bounding boxes** for the target ID on both pages, and its text strategy recovered an unruled table. pypdf returned only page plus character offset, with text-line-relative coordinates and no word boxes, which is not enough for a locator that reopens the exact span **[Documented licences via PyPI metadata; test result is this project's own]**. PyMuPDF is excluded because Artifex: "You cannot deploy our open-source as part of a server-based application or service, without disclosing your own application's full source code under AGPL"; pricing is "Contact Sales" ([Artifex licensing](https://artifex.com/licensing); [PyMuPDF docs](https://pymupdf.readthedocs.io/en/latest/about.html)) **[Documented, primary-read]**. M1 slice 3 currently specifies PyMuPDF |
| Layout-heavy PDFs | Docling | Keep deferred, as the plan says. Adopt only when a real document needs it, then pin and pre-bake model weights | Code is MIT, model licences are separate ([Docling](https://github.com/docling-project/docling)) [Documented]. Table accuracy reports range from 63% to 85% TEDS, against an unsourced 97.9% ([Tensorlake](https://docs.tensorlake.ai/document-ingestion/benchmarks)) [Vendor claim/Research, conflicting]. CPU OCR can take 30+ s per page ([Docling report](https://arxiv.org/html/2408.09869v5)) [Research] |
| Excel | openpyxl, pandas | **openpyxl directly for provenance.** Use pandas only after locators are attached | openpyxl does not evaluate formulas. `data_only=True` gives cached values or `None`, and reading formula plus value needs two loads ([openpyxl issue](https://foss.heptapod.net/openpyxl/openpyxl/-/issues/1425)) [Documented/community]. pandas drops cell addresses [Inference] |
| XML / JSON | (not specified) | `defusedxml`; JSON pointers as locators | OWASP XXE guidance [Documented] |
| Graph | Relational adjacency | Keep. Add an edge-type propagation table, `CYCLE` or a visited set, and a second implementation for differential tests | Section 7 |
| Search | PostgreSQL FTS; pgvector if justified | Keep. pgvector only after measured keyword-recall failure on prose | Section 9 |
| Jobs | (not specified) | A PostgreSQL-backed queue (for example Procrastinate). No Redis | Low volume; fits customer-hosted installs; SKIP LOCKED queues bloat at high volume ([Microsoft](https://techcommunity.microsoft.com/blog/adforpostgresql/potential-consequences-of-using-postgres-as-a-job-queue/4514332)) [secondary] |
| Backend | FastAPI, Pydantic | Keep | Typed boundaries match the repo rules. Current versions not researched |
| Frontend | Next.js, Tailwind, shadcn/ui, React Flow | Keep React Flow for bounded subgraphs. Next.js is acceptable, though a static single-page app would do since FastAPI serves all data | React Flow ceiling around 1,000 nodes [User report]. Next.js server features go unused [Inference] |
| Deployment | (not specified) | Containers, single-tenant and customer-hostable first | Likely buyer expectation, unverified [Inference] |

## 12. Roadmap: prove the engine, then earn real data, then widen

The eight capability areas are not equal. Ordered by defensibility and by evidence:

| Priority | Capability | Scope | Gate to start |
|---|---|---|---|
| **P0** | A (narrow), C, D (impact), E (coverage) on synthetic data | Milestone 1 with the corrections in section 13 | None |
| **P0, in parallel** | Problem validation | 8–12 structured interviews with consultants and WFM administrators about reconciliation effort, change-control practice and release validation; collect sanitised artefact samples with permission | None. **This is the most important unbuilt piece** |
| **P1** | D (snapshot diff, orphans, dangling refs) | Diff two IR snapshots on stable keys. Detect dangling references, unreferenced objects and requirement/config/test gaps | A sanitised real export or workbook in hand |
| **P1** | E (test inventory import) | Import Opkey, TestAssure, Jira or spreadsheet test inventories as nodes. No execution | Sample inventories |
| **P2** | A (LLM-assisted) | INFERRED-only proposals from prose, review queue, span verifier, F2 evaluation | Labelled synthetic set; provider terms checked |
| **P2** | B (Pro WFM JSON snapshots) | Parse customer-supplied JSON shaped like the documented setup responses | **Legal review of MSA, AUP and Exhibit A**; real samples |
| **P3** | F (explanations) | LLM narration of computed reports, citing ids | P2 controls proven |
| **P3, conditional** | G (narrow) | WFC→Pro WFM mapping-evidence ledger, with each mapped pair evidenced | Real WFC exports and a paying late-migration customer before March 2027 |
| **Drop** | H (cost intelligence) | Not built | No data source. Repo rule 9 forbids invented savings |

## 13. The MVP is Milestone 1, corrected, with pass/fail criteria

**Revision 2:** all corrections below, plus hostile-input requirements, a synthetic-only data boundary with a future real-data gate (G-REAL), upstream-constraint and context categories, and the product profile `synthetic`, are now in `docs/plans/milestone-1.md` (revision 2). That plan's acceptance criteria supersede the table below.

The milestone plan is well scoped and agrees with most of this research. It builds one vertical slice, has no LLM, defers Docling, uses an in-memory breadth-first search, keeps "no safe verdict" and reports coverage gaps. Seven changes are warranted.

1. **Replace PyMuPDF in slice 3** with a permissively licensed parser behind an interface (section 11), so that licensing debt does not set in on day one.
2. **Rename "confirmed impacts" to "established impacts"** in the plan and in the `configuration-change-impact-review` skill, so impact tiers cannot be confused with human-CONFIRMED edges.
3. **Add tier C, "not modelled", to the expected output.** For example, make the Harborline payroll integration's target configuration deliberately absent, so the report must name a blind spot.
4. **Break the circularity in slices 2 and 4.** When one YAML spec generates both the fixtures and the ground truth, "matches the ground truth exactly" mostly proves the parser reads what the generator wrote. Add a hand-authored expected impact set, a "messy" fixture variant (renamed sheets, merged cells, hidden rows, a dangling ID, an alias spelling, a formula with no cached value), and mutation tests.
5. **Enforce CONFIRMED in the database (slice 5)**, not only through the review endpoint.
6. **Derive the change set from two snapshots.** Generate a "before" and an "after" workbook and diff them, rather than hand-writing the change. This proves drift detection and impact in one demo, at almost no extra cost.
7. **Label the threshold-on-a-work-rule modelling as a fictional assumption**, because Pro WFM lists Overtime Rules as a separate resource group and the real containment is unverified. Extend the upload checks in slice 3 to cover ZIP expansion and XXE.

Measurable acceptance criteria (proposed thresholds, not evidence-derived):

| # | Criterion | Measure |
|---|---|---|
| 1 | Every entity, attribute value and relationship resolves to a locator that reopens the exact source span | 100% by automated check; zero orphan claims |
| 2 | Determinism | Two runs on the same inputs give byte-identical impact reports (hash equality) |
| 3 | Correctness against an independent oracle | Exact match to the hand-authored expected impact set; 100% of at least 20 mutation cases detected |
| 4 | Tiering | Report contains established, possible (with weakest edge method and confidence) and not-modelled sections; no "safe" wording (string test) |
| 5 | Coverage | At least one requirement and one configuration object with no test reported as gaps; hard-coded "40" expected results in tests flagged |
| 6 | Status integrity | A direct database insert or update setting CONFIRMED without a human reviewer fails; every promotion has reviewer and timestamp |
| 7 | Hostile input | Oversized, wrong-type, ZIP-bomb (over 100x expansion), XXE-bearing and macro-enabled files are rejected with tests |
| 8 | Hub resilience | Impact on a synthetic hub-heavy graph of about 10⁵ edges finishes within a team-set target (for example p95 under 2 s on CI hardware), with no duplicate paths |
| 9 | UI | Playwright CLI on localhost: graph renders; clicking a node or edge shows document, location and snippet; edge styling distinguishes statuses |
| 10 | Usefulness signal | At least 5 practitioners walk through the demo; record whether they recognise the reconciliation problem and would supply sanitised artefacts. Below 3 of 5, revisit the thesis |

## 14. Technical risks and unresolved assumptions

The full, maintained register is `docs/risk-register.md`. The table below summarises it.

| Risk or assumption | Status | Consequence if wrong | Mitigation |
|---|---|---|---|
| Product read as a "competitive product or service" or "competitive intelligence" (Developer Policy §4) | **Clause verified; interpretation open** | Loss of interface access; legal exposure | UKG and TCS Legal interpretation (D1) before commercial positioning or real data |
| Sub-processor authorisation for LLM, host and database (§5) | Clause verified; applicability to offline files unclear | Breach on the first real deployment | No LLM on real data before authorisation; gate G-REAL |
| Cross-customer features breach aggregation ban (§4) | Clause verified | Breach | Not built; per-customer isolation |
| Model evaluation on real artefacts (§4) | Clause verified | Breach | Synthetic evaluation sets only |
| Offline customer-supplied exports fall outside the policy | **Unverified inference** | Same obligations may apply | Legal clarification (D2); customer DPA |
| Practitioners spend meaningful time cross-referencing artefacts | **Unverified; no source** | No buyer | Interviews before P1 (`docs/research/practitioner-interview-guide.md`) |
| Real artefacts carry explicit, parseable cross-references | Unverified; Fayetteville shows rules from verbal guidance | Most edges become INFERRED and need review, eroding value | Measure the OBSERVED/INFERRED ratio on the first real samples |
| Lawful access to configuration data | **MSA, AUP and Exhibit A unread** | Pro WFM API-based ingestion is blocked | Obtain the PDFs; legal review; customer-supplied files first |
| SDM export is parseable | Format undocumented | Dead end | Do not build against it without a UKG specification |
| Setup GET responses contain enough to rebuild relationships | Only the employment-terms sample was seen | Graph from API data is shallow | Validate on a real non-production response with customer permission |
| UKG extends SDM compare or ships Configuration Assistant features | Plausible; roadmap unknown | Drift and explanation features commoditised | Anchor value in provenance, history and cross-tool coverage |
| Opkey or other test vendors deepen config-level impact | Medium | E and D overlap | Integrate as data sources; position as complementary |
| WFC migration market closes 31 March 2027 | Secondary sources agree; UKG page unread | G investment stranded | Keep G conditional and narrow |
| Tenant graph scale | No source | Traversal performance | Hub-heavy synthetic tests; measure on first real export |
| LLM extraction precision on HR/WFM prose | No domain benchmark | Review burden explodes | INFERRED cap, span verifier, F2 plus precision audit |
| Change-impact recall is inherently limited | Literature: 50–56% recall for dynamic CIA | Missed impacts read as "safe" | Tier C blind spots; never "safe"; validate against real outcomes |
| Docling or other ML parsing accuracy on real exports | 63–85% TEDS reported | Bad structure becomes false OBSERVED edges | Deterministic parsers for structured files; ML only for layout-heavy PDFs, output INFERRED |
| Buyers require customer-hosted deployment and certifications | Unverified | Sales blocked | Containerised single-tenant from day one; plan SOC 2 later |
| Synthetic fixtures do not resemble real exports | Certain at M1 | A demo that does not transfer | Say so in every demo; get sanitised samples |

## 15. Research bibliography

**Primary-read (full text verified)**
- UKG Developer Policy (updatedAt 2026-09-30; retrieved 2026-11-18; SHA-256 1bf9782b…4b1a): https://developer.ukg.com/proplatform/docs/developer-policy
- pdfplumber (PyPI metadata, MIT): https://pypi.org/project/pdfplumber/
- pypdf (PyPI metadata, BSD-3-Clause): https://pypi.org/project/pypdf/
- pdfminer.six (PyPI metadata, MIT): https://pypi.org/project/pdfminer.six/
- pypdfium2 (PyPI metadata, BSD-3-Clause/Apache-2.0): https://pypi.org/project/pypdfium2/
- UKG Authentication: https://developer.ukg.com/talk/docs/ukg-authentication-doc
- Developer Console Quick Start: https://developer.ukg.com/proplatform/docs/developer-console-quick-start
- Pro WFM Limits: https://developer.ukg.com/wfm/docs/limits-doc
- Version 2 resources and operations: https://developer.ukg.com/wfm/docs/version-2-resources-and-operations-doc
- Pro WFM API reference: https://developer.ukg.com/wfm/reference
- Employment Term Assignments: https://developer.ukg.com/wfm/docs/employment-term-assignments-doc
- Configure access for a person: https://developer.ukg.com/wfm/docs/configure-access-for-a-person-doc
- WFM Webhook Events: https://developer.ukg.com/wfm/docs/wfm-webhook-events
- Developer Hub FAQ: https://developer.ukg.com/general/docs/ukg-developer-hub-faq
- Authentication and Authorization (HCM): https://developer.ukg.com/general/docs/authentication-and-authorization
- Web Service Account: https://developer.ukg.com/hcm/docs/web-service-account
- API and Developer Tools Overview: https://developer.ukg.com/general/docs/api-and-developer-tools-overview
- GenAI Search: https://developer.ukg.com/general/docs/genai-search
- Workforce Intelligence Hub: https://developer.ukg.com/proplatform/docs/welcome-to-workforce-intelligence-hub
- UKG Compose: https://developer.ukg.com/proplatform/docs/welcome-to-ukg-compose
- Artifex licensing: https://artifex.com/licensing
- PyMuPDF License and Copyright: https://pymupdf.readthedocs.io/en/latest/about.html
- Docling GitHub: https://github.com/docling-project/docling

**UKG legal (NOT readable; provisional)**
- MSA 2026-07-01: https://www.ukg.com/sites/default/files/2026-07/MSA-2026-07-01-US.EN_.pdf
- AUP 2026-07-01: https://www.ukg.com/sites/default/files/2026-07/AUP-English-2026-07-01.pdf
- API Call Packs SD / Exhibit A: https://www.ukg.com/sharepoint/view/01WMTN4D3XI35U4LFZ7BC37IPT6C37O3TV
- Terms of use: https://www.ukg.com/terms-of-use
- Bryte Assistive AI SD: https://ukg.com/sites/default/files/2026-02/UKG-Bryte-Assistive-AI-for-Pro-HCM-for-UKG-Pro-Pay-and-or-UKG-Pro-People-Center-2026.02.03-English.pdf

**UKG product and help (snippet level)**
- SDM Copy Setup Data: https://sso-hlp01.mykronos.com/help/en_US/Content/SDM/CopySetupData.htm
- SDM Export: https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/ExportSetupData.htm
- SDM supported data: https://hlp03.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/setup_data_manager_supported_data.html
- Using SDM: https://hlp03.gss.mykronos.com/help/HCM/administration/Setup_data_manager_SDM/using_setup_data_manager_368192.html
- SDM publish tool: https://sso-hlp02.gss-kcfn.mykronos.com/help/setup/Content/SDM/PublishTool.htm
- Pay rules reference: https://library.ukg.com/Prebuilt/newgen/WorkforceMgmt/Content/WFMPayRules-r_x52705.html
- Payroll to paycode mappings: https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/configure_payroll_to_paycode_mappings.html
- Accrual profiles: https://sso-hlp01.gss.mykronos.com/help/en_GB/Content/ApplicationSetup/Accruals/AccrualProfiles.htm
- Pro WFM 2024R2 release notes: https://hlp02.gss.mykronos.com/help/en_US/Content/Resources/ReleaseNotesPDFs/ProWFM_2024R2_ReleaseNotesRevT.pdf
- Non-production environments DS: https://www.ukg.com/sites/default/files/2023-09/DIY0365-USv2-UKG-Pro-WFM-non-Production-Environments-DS.pdf
- Data Hub configuration portal: https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/data_hub_configuration_portal_2.html
- Integration Hub profile: https://www.ukg.ca/sites/default/files/2023-09/DIY0262-v2-UKG-Pro-Integration-Hub-Product-Profile.pdf
- Pro WFM Standard SOW 2026-04-03: https://www.ukg.com/sites/default/files/2026-04/UKG-Pro-WFM-Standard-SOW-2026-04-03-English.pdf
- Launch project team guide: https://library.ukg.com/documents/Launch/UKG_Pro_Creating%20Your%20Project%20Team.pdf
- Performance testing DS: https://www.ukg.com/sites/default/files/2023-09/DIY0225-UKG-Dimenions-Performance-Testing.pdf
- Make Dimensions changes with confidence: https://www.ukg.com/blogs/ukg-blog-post/make-ukg-dimensions-changes-confidence
- Migration Assessment DS: https://www.ukg.com/sites/default/files/2023-09/SV0252-USv4-UKG%20Pro%20WFM-Migration-Assessment-ds.pdf
- WFC support policies: https://www.ukg.com/wfc-support-policies-and-services
- UKG in Claude press release: https://www.businesswire.com/news/home/20261020356990/en/UKG-in-Claude-Makes-AI-Work-Beyond-the-Chat
- Nucleus Aspire 2025: https://nucleusresearch.com/wp-content/uploads/2025/11/z192-UKG-Aspire-Global-Analyst-Day-2025-updates.pdf
- Nucleus Spring 2026: https://nucleusresearch.com/wp-content/uploads/2026/06/26107-UKG-Spring-Global-Analyst-Day-2026-updates.pdf

**WFC and migration**
- RSM: https://www.rsmus.com/insights/technology/ukg/ukg-workforce-central-support-is-ending-do-you-have-a-plan
- Healthcare IT Leaders, EOL: https://healthcareitleaders.com/blog/ukg-workforce-central-wfc-end-of-life
- Healthcare IT Leaders, migration: https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/
- Workaxle: https://www.workaxle.com/blog/kronos-workforce-central-end-of-life-migration
- UCSB: https://timekeeping.ucsb.edu/ucsb-timekeeping-refresh-project
- UCSD: https://rrsshr.ucsd.edu/timekeeping/index.html
- UC Berkeley: https://caltime.berkeley.edu/caltime-replacement-project
- WFC 8.1 DTK reference (unofficial): https://www.scribd.com/document/696889274/WFC81-IntegrationMgrDTKRef

**Documented problems**
- WUSF, Manatee: https://www.wusf.org/politics-issues/2026-06-27/manatee-county-underpaid-ems-workers-by-at-least-336-607-audit-finds
- EMS1, Manatee: https://www.ems1.com/labor-issues/audit-finds-fla-county-underpaid-ems-personnel-more-than-336k
- EMS1, Volusia: https://www.ems1.com/labor-issues/fla-emts-told-to-repay-overpayments-after-payroll-error
- Fayetteville audit: https://fayettevillenc.gov/home/showpublisheddocument/21178/637922792448230000
- Dallas A15-011: https://dallascityhall.com/departments/auditor/DCH%20Documents/Audit%20Reports%20FY%202015%20(3-20-2015%20to%2009-30-2015)/A15-011%20-%20Audit%20of%20City%20of%20Dallas'%20Civilian%20Timekeeping%20Internal%20Controls%20and%20Processes%2008-14-2015.pdf
- Albuquerque audit: https://www.cabq.gov/audit/documents/17-104-final-04252019-js.pdf/@@download/file/17-104%20Final%2004252019%20JS.pdf
- Springfield audit: https://www.springfield-ma.gov/audit/fileadmin/auditor/Internal_Audit_Reports/Fiscal_Year_2023/Payroll_Audit_Report.pdf
- HC Online, ALDI: https://www.hcamag.com/au/specialisation/employment-law/aldis-55m-class-action-settles-unpaid-shift-work-for-32000-staff/594780
- AHA H-ISAC, KPC outage: https://www.aha.org/h-isac-reports/2021-12-13-h-isac-tlp-white-kronos-private-cloud-kpc-ransomware-incident-causes
- HR Dive, Cargill settlement: https://www.hrdive.com/news/court-approves-cargill-settlement-kronos-ransomware-outage/702068/
- UKG/KPMG survey: https://www.businesswire.com/news/home/20260331209752/en/UKG-and-KPMG-Nearly-40-of-Employers-Suffer-Millions-of-Dollars-in-Preventable-Losses-Annually-Due-to-Global-Payroll-Errors
- Argano: https://argano.com/insights/articles/best-practices-for-optimizing-ukg-pro-wfm-after-golive.html
- Healthcare IT Leaders, 7 things: https://www.healthcareitleaders.com/blog/7-things-worth-getting-right-before-your-ukg-pro-wfm-implementation-kicks-off/
- Working Smarter Cafe podcast: https://working-smarter-cafe.buzzsprout.com/1629862/9630643
- Soon.works: https://soon.works/blog/what-a-ukg-implementation-actually-costs
- Outsail: https://www.outsail.co/post/how-much-does-ukg-cost-in-2026

**Competitors and analogues**
- Opkey for UKG: https://www.opkey.com/kronos
- TestAssure (TechIntelPro): https://techintelpro.com/news/hr/workforce-management/testassure-launches-wfm-regression-testing-to-cut-payroll-risk
- Tricentis UKG: https://tricentis.com/solutions/ukg-testing
- Tricentis LiveCompare: https://www.tricentis.com/products/impact-analysis-livecompare
- LiveCompare Smart Impact docs: https://docs.tricentis.com/livecompare-2026.1/content/smart_impact_learning_app.htm
- Worksoft UKG: https://www.worksoft.com/applications/ukg
- Panaya impact docs: https://success.panaya.com/docs/how-to-analyze-impact-and-risk.md
- Gearset: https://gearset.com/blog/salesforce-impact-analysis/
- Elements.cloud: https://elements.cloud/understand-salesforce-complexity
- Workday Tenant Compare: https://doc.workday.com/admin-guide/en-us/manage-workday/tenant-configuration/implementation-tools/customer-central/tenant-compare/compare-tenant-configuration-data.html
- Kainos Smart: https://www.kainos.com/workday/products/smart
- Boomi Universal Lineage: https://boomi.com/ja/blog/introducing-universal-lineage-in-boomi-meta-hub/
- ServiceNow impact analysis: https://www.servicenow.com/docs/r/q4dSP2Icgr1SFv5wanVXvQ/~p6mlH3iSpQH9FQYNZo24w
- Jama suspect links: https://www.jamasoftware.com/blog/5-ways-jama-connect-makes-traceability-easy/
- Polarion linking: https://docs.plm.automation.siemens.com/content/polarion/20/help/en_US/user_and_administration_help/administrators_guide/configure_work_items/configure_work_item_linking.html
- Surety Systems: https://www.suretysystems.com/consulting/kronos/
- PeopleTech workshop: https://resource.peopletech.com/workshops/ukg-wfc-migration-to-pro-wfmdimensions

**Data model, graph, impact, AI**
- W3C PROV overview: https://www.w3.org/TR/prov-overview/Overview.html
- DataHub file-based lineage: https://docs.datahub.com/docs/generated/ingestion/sources/file-based-lineage
- Salesforce MetadataComponentDependency: https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_metadatacomponentdependency.htm
- Apache AGE 1.8.0 (EDB): https://www.enterprisedb.com/docs/pg_extensions/apache_age/rel_notes/apache_age_1.8.0_rel_notes/
- Kuzu archived (The Register): https://www.theregister.com/2025/10/14/kuzudb_abandoned/
- SQL/PGQ commit: https://www.postgresql.org/message-id/E1w247I-0000Tk-2Y%40gemulon.postgresql.org
- Neo4j licensing: https://neo4j.com/licensing/?ref=blog
- Recursive CTE cycle detection: https://vb-consulting.github.io/blog/recursion-postgresql/part3-cycle-detection
- Postgres-as-graph benchmark: https://landing-page-3tt.pages.dev/blog/postgres-as-a-graph-database/
- Buffalo dynamic CIA study: https://researchconnect.buffalo.edu/en/publications/a-comprehensive-study-of-the-predictive-accuracy-of-dynamic-chang/
- Static CIA comparative study: https://www.bohrium.com/paper-details/static-change-impact-analysis-techniques-a-comparative-study/814604185264717824-2502
- DEPTH (arXiv 2508.14391): https://arxiv.org/pdf/2508.14391
- TraceLLM (arXiv 2602.01253): https://arxiv.org/pdf/2602.01253
- Citation fabrication (arXiv 2602.21059): https://arxiv.org/pdf/2602.21059
- Tensorlake parser benchmarks: https://docs.tensorlake.ai/document-ingestion/benchmarks
- Docling technical report: https://arxiv.org/html/2408.09869v5
- openpyxl formula issue: https://foss.heptapod.net/openpyxl/openpyxl/-/issues/1425
- OWASP File Upload: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- OWASP XXE: https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- React Flow performance issue summary: https://lightrun.com/answers/wbkd-react-flow-performance-drop-when-panning-or-zooming
- ParadeDB hybrid search: https://paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual
- Postgres as job queue (Microsoft): https://techcommunity.microsoft.com/blog/adforpostgresql/potential-consequences-of-using-postgres-as-a-job-queue/4514332
- RLS vs schema-per-tenant: https://dev.to/itsjayanth/multi-tenant-postgresql-row-level-security-vs-schema-per-tenant-when-to-use-which-3joe
- CX Today on ZDR: https://www.cxtoday.com/security-privacy-compliance/anthropic-zero-data-retention-enterprise-ai/

---

## Direct answers

**Is this a real problem worth solving?** Partly proven. Configuration that diverges from a changed contract does cost real money: Manatee County ($336,607 underpaid) and Volusia County show it, although both are known only through news summaries. And UKG explicitly puts release validation on the customer. But the specific pain the Workbench targets, manual cross-referencing of artefacts during delivery, has **no practitioner evidence and no measurement**. It is a credible hypothesis, not a validated problem. Treat interviews and real artefact samples as the next deliverable, alongside Milestone 1.

**Does the platform have a meaningful differentiator?** Yes, but narrower than the brief implies. Three things were found nowhere else for UKG: per-edge evidence and OBSERVED/INFERRED/CONFIRMED status with human-only confirmation; snapshot history, which matters because no public setup-change audit trail was found; and coverage that links requirements, UKG configuration, tests and defects across tools. Environment compare alone is not a differentiator, because SDM has one. AI diagnostics alone is not one either, because Bryte and UKG in Claude occupy that space.

**Which capabilities are genuinely defensible?** In order: (1) the provenance-preserving IR and evidence model; (2) deterministic, tiered change impact with explicit blind spots; (3) requirement/configuration/test coverage gaps across tool boundaries; (4) snapshot history with dependency-aware diff and orphan/dangling-reference detection. Each is defensible because UKG has no reason to model artefacts it does not hold, and test vendors do not appear to ingest configuration. None is defensible against UKG for long if it depends only on data UKG already exposes.

**What should we absolutely not build?** Avoid six things. **No chatbot over UKG data.** **No live tenant connector or in-tenant AI agent** until the MSA, AUP and Exhibit A have been read and reviewed by a lawyer and the Developer Policy conditions are met (registration, customer consent, UKG approval). The policy prohibits agentic UKG API use without MCP Gateway registration or authorisation. **No cross-customer benchmarks or pattern libraries** (cross-tenant aggregation ban). **No SDM file parser** without a specification. **No pay-impact or savings numbers**, so capability H is dropped. **No test execution, ticketing, integration monitoring or workflow automation.** And **no WFC "migration factory"** racing a support window that closes on 31 March 2027. Also avoid a graph database, pgvector and PyMuPDF until measured need, or a licence, justifies them.

**What is the smallest impressive product that proves the core idea?** Milestone 1 with the seven corrections in section 13. Two synthetic snapshots (before and after) plus one design PDF go in. The diff becomes the change set. Out comes a byte-reproducible impact report with established, possible and not-modelled tiers, coverage gaps including tests hard-coded to the old value, and every node and edge clickable back to its cell or page. It must pass hostile-input tests and mutation tests against a hand-authored oracle. That proves the engine. Whether anyone needs it is proven separately, by practitioners recognising their own problem in it.

**What evidence or access is needed before claiming production readiness?** Eight things:

- The MSA, AUP and API Call Packs Exhibit A, in full, reviewed by a lawyer, and written UKG authorisation if any API path is used.
- A UKG and TCS Legal interpretation of the Developer Policy's competitive-product and competitive-intelligence clauses, written UKG authorisation for every sub-processor, customer DPAs, and demonstrated compliance with its deletion, encryption, incident and audit requirements.
- Sanitised real artefacts from several projects (workbooks, test inventories, mapping specs, and Pro WFM setup JSON obtained with permission), to measure parse coverage and the OBSERVED/INFERRED ratio.
- Primary confirmation of the unverified configuration relationships (pay rule ↔ work rule, overtime rules, paycode ↔ payroll mapping) per product profile.
- SDM and Configuration Assistant documentation, to settle the redundancy risk.
- Validation of impact results against real regression or parallel-pay outcomes, measured as precision and recall.
- A security review covering authentication, tenancy isolation, upload handling and LLM data egress, with provider retention terms confirmed.
- Practitioner interviews that quantify reconciliation effort.
- A buyer with a named budget.

---

## Conclusion

This research mostly changes what the product is. The original framing was an eight-pillar intelligence platform. The evidence supports a much smaller thing: an **evidence engine** whose value is that it can say exactly why it believes each edge, what it could not see, and which tests nobody wrote. Those properties are what UKG, the test vendors and generic traceability tools leave alone, and they are also what makes the product safe to use in a payroll context. Everything that pulls the product toward live tenant access, conversational AI or migration labour runs into stronger incumbents, unread contracts or a closing calendar.

The second shift is in what counts as progress. The engineering risk is low and well understood. The open risks are about evidence: whether practitioners feel this pain enough to supply real artefacts, and whether those artefacts carry enough explicit structure for OBSERVED edges to dominate. Milestone 1 should be built to answer those two questions as much as to demonstrate a graph. A demo that a consultant recognises, and then backs by handing over a sanitised workbook, is worth more than any additional capability area.

---

*Not checked in this synthesis: no source was re-fetched. The report relies entirely on the notes, and inherits their snippet-level limits.*

*Revision 2 (18 Nov 2026) incorporated the UKG Developer Policy, the PDF parser decision, the relationship-model and impact-propagation proposals, and the revised Milestone 1 plan. Licences of PyMuPDF alternatives, checked against PyPI metadata: pypdf 7.1.0 is BSD-3-Clause; pdfplumber 0.11.10 is MIT, built on pdfminer.six (MIT); pypdfium2 5.15.2 is BSD-3-Clause/Apache-2.0, with bundled PDFium dependency licences that need their own review.*
