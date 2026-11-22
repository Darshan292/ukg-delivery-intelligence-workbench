# Native UKG capabilities overlapping the Delivery Intelligence Workbench, and UKG AI/agent/API policies (as of 2026-11-18)

Method note: WebFetch was blocked in this session (ukg.com, developer.ukg.com, nucleusresearch.com, briefglance.com did not resolve; they would need allowing in the session network settings). Everything below comes from WebSearch result summaries of those pages. The policy clauses in particular were NOT read in full text. Verify against the primary documents before relying on them. Claim classes: [FACT] documented in vendor docs/legal text as summarised by search; [MKTG] vendor marketing/press; [USER] third-party/user report; [INF] inference.

## 1. UKG Bryte AI, Bryte agents, Workforce Intelligence Hub, Data Hub, "Workforce Operating Platform"

### Takeaway
Bryte, Bryte agents, the Workforce Intelligence Hub and Workforce Operating Platform all exist and are UKG-branded, but the evidence found points them at end users, HR/payroll/frontline managers and workforce analytics, not at implementation/configuration engineering traceability, drift or change-impact. The one closely relevant item is a UKG "Configuration Assistant" for implementation, reported only by an analyst note and not verified in UKG docs.

### Cited Findings
- Bryte is described as the intelligence layer behind UKG's assistive and agentic AI; assistants give role-specific recommendations, Bryte Agents handle more complex multi-step work; People Fabric is the data foundation. [MKTG/analyst] — [Nucleus Spring 2026 Analyst Day](https://nucleusresearch.com/wp-content/uploads/2026/06/26107-UKG-Spring-Global-Analyst-Day-2026-updates.pdf) (via search summary)
- UKG's 27 Aug 2026 quarterly release added Bryte Voice, AI-powered high-volume recruiting and "Agentic Pay" for payroll accuracy. [MKTG; GA status not confirmed] — [Business Wire, 27 Aug 2026](https://secure.businesswire.com/news/home/20260827017367/en/UKG-Deepens-Workforce-Operating-Platform-with-AI-Built-to-Help-CHROs-Improve-Frontline-Work)
- Bryte agents and payroll agents announced for the Pro HCM suite: [HCM agents](https://www.ukg.com/company/newsroom/ukg-unveils-bryte-ai-agents-and-capabilities-transform-employee-experiences-ukg-pro-hcm-suite), [payroll agents](https://www.ukg.com/company/newsroom/ukg-launches-next-generation-payroll-ai-agents-unlock-productivity-efficiency-and-elevated-employee-engagement). [MKTG; which are GA not verified]
- Nucleus says Bryte Agents in Pro WFM support live scheduling, coverage, labor planning and frontline decision-making. [analyst summary of UKG briefing] — [Nucleus Spring 2026](https://nucleusresearch.com/wp-content/uploads/2026/06/26107-UKG-Spring-Global-Analyst-Day-2026-updates.pdf)
- Bryte Assistive AI has a formal Services Description (Feb 2026) stating Output may be inaccurate and that UKG may monitor use of Bryte AI under the DPA. [FACT, from search summary] — [UKG Bryte Assistive AI SD 2026.02.03](https://ukg.com/sites/default/files/2026-02/UKG-Bryte-Assistive-AI-for-Pro-HCM-for-UKG-Pro-Pay-and-or-UKG-Pro-People-Center-2026.02.03-English.pdf) — i.e. Bryte is GA at least for Pro HCM (Pro Pay/People Center).
- Workforce Intelligence Hub: announced at Aspire, Nov 2025; unifies workforce data (demographics, scheduling, time, hiring, performance, pay) into one view; availability stated as early/H1 2026 for enterprise customers; June 2026 release added an agentic orchestration layer through the Hub and a "Dynamic Workforce Operations" product. [MKTG; shipped-vs-roadmap unclear] — [Business Wire Nov 2025](https://www.businesswire.com/news/home/20251104624682/en/UKG-Launches-Workforce-Intelligence-Hub-Redefining-Workforce-Operations-and-Unlocking-Unmatched-Labor-Insights); developer docs page exists: [Welcome to Workforce Intelligence Hub](https://developer.ukg.com/proplatform/docs/welcome-to-workforce-intelligence-hub) (existence of docs suggests some shipped surface [INF]).
- Pro WFM "Data Hub" is a separate, older WFM-embedded data-pipeline/reporting component with a Configuration Portal showing pipeline/wrapper job history and audit history. [FACT] — [Data Hub Configuration Portal help](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/data_hub_configuration_portal_2.html). It moves operational/time data to analytics; nothing found indicating it models configuration dependencies.
- Nucleus reports UKG built an AI-powered "Configuration Assistant" to help customers during implementation and "significantly reduce build time". [analyst report of UKG claim = MKTG] — [Nucleus Aspire 2025](https://nucleusresearch.com/wp-content/uploads/2025/11/z192-UKG-Aspire-Global-Analyst-Day-2025-updates.pdf). A targeted search found no UKG documentation using this name for Pro WFM; scope/GA unverified.
- ServiceNow partnership connects Bryte agents to ServiceNow AI Agent Fabric. [MKTG] — reported in search summary of Bryte coverage; source not individually fetched.

### Inferences
- [INF] Bryte/Hub target operators and managers (why did overtime rise, payroll accuracy) rather than building requirement-to-config-to-test graphs. No UKG source found claiming dependency graphs, orphan detection, drift or requirement traceability.
- [INF] The Configuration Assistant is the nearest overlap risk: if it exposes explanations or validation of configuration, it could erode "diagnostics" value. Unknown until UKG docs are obtained.

### Gaps
- Exact current GA status of each Bryte agent, and whether any Bryte agent is available to Pro WFM admins/implementers for configuration tasks: unverified.
- Configuration Assistant: only an analyst mention; no UKG primary doc found.
- Workforce Intelligence Hub pricing and precise GA date not found.

## 2. "UKG Compose"

### Takeaway
UKG Compose exists and is a real UKG product, but it is a low-code workflow automation tool on the UKG Pro platform, not an implementation or configuration-analysis tool. Do not confuse it with Decusoft Compose (third-party compensation planning).

### Cited Findings
- Developer docs describe UKG Compose as a way to build, run and manage custom business processes (workflow automation); currently only for customers who elected to participate with tenants in US/CA regions; Pro-first experience, standalone WFM docs still to come. [FACT] — [Welcome to UKG Compose](https://developer.ukg.com/proplatform/docs/welcome-to-ukg-compose)
- Built on the n8n editor (trigger, logic, actions). Has Admin Guide, User Guide, connectors/connections and "build workflows" docs. [FACT] — [UKG Compose User Guide](https://developer.ukg.com/proplatform/docs/ukg-compose-user-guide), [Admin Guide](https://developer.ukg.com/proplatform/docs/ukg-compose-admin-guide)
- SKUs: Compose Base, Compose Premium, additional workflow and premium concurrent workflow. [FACT] — [UKG legal doc](https://www.ukg.com/legal-doc/ukg-compose-base-ukg-compose-premium-ukg-compose-additional-workflow-and-ukg-compose-premium-concurrent-workflow)
- Conflict: Welcome page says available to opted-in customers; User Guide says Beta only. [FACT, conflicting] — same two developer.ukg.com pages.
- Decusoft Compose is a different, third-party compensation product integrating with UKG Pro. [FACT] — [Decusoft](https://www.decusoft.com/?p=18824)

### Inferences
- [INF] Compose could in principle be used by customers to automate checks via API, so it is a build-it-yourself alternative for narrow rules, but nothing indicates it offers a configuration graph or traceability.

### Gaps
- GA vs beta status unresolved; pricing not found.

## 3. Pro WFM native configuration-management tooling

### Takeaway
UKG provides Setup Data Manager (publish setup data between tenants, with audit logging of applied changes) and non-production tenants. Search found no documented native configuration diff/compare, dependency graph, orphan detection or requirement/test traceability. Absence in search results is not proof of absence.

### Cited Findings
- Setup Data Manager (SDM) copies setup data between tenants via REST APIs, all or selected items, adds/updates by item name. [FACT] — [Using Setup Data Manager](https://hlp03.gss.mykronos.com/help/HCM/administration/Setup_data_manager_SDM/using_setup_data_manager_368192.html)
- Changes applied by SDM are logged in the server audit trail as if entered manually. [FACT] — same page.
- SDM exclusions include Delegate Profiles and Unpublished Reports; requires Function Access Profile and Generic Data Access Profile permissions. [FACT] — [SDM related topics](https://hlp02.gss.mykronos.com/help/HCM/administration/Setup_data_manager_SDM/related_topics_368547.html), [supported data](https://hlp03.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/setup_data_manager_supported_data.html)
- UKG recommends change in non-production first, test, then migrate to production. [FACT] — SDM help above.
- Environments: one production and one partial-copy non-production tenant by default, more purchasable; non-prod refresh from production up to weekly (per cloud guidelines, requested via a Community case). [FACT; dated] — [Non-production environments DS (2023)](https://www.ukg.com/sites/default/files/2023-09/DIY0365-USv2-UKG-Pro-WFM-non-Production-Environments-DS.pdf), [Cloud guidelines](https://www.ukg.com/for-llms/ukg-pro-workforce-management/agreement/cloud-guidelines)
- Monitoring: People Sync Monitoring dashboard (sync status, employee sync history); Data Hub job/audit history; Pro platform Integrations Dashboard (run, monitor, status). [FACT] — [People Sync dashboard](https://hlp02.gss.mykronos.com/help/HCM/maintenance/People_sync/people_sync_monitoringsynchronization_dashboard_517293.html), [Integrations Dashboard](https://developer.ukg.com/hcm/docs/integrations-dashboard-overview)
- UKG offers a paid Pro WFM Migration Assessment service sheet (SV0252). [FACT, exists; content not read] — [SV0252](https://www.ukg.com/sites/default/files/2023-09/SV0252-USv4-UKG%20Pro%20WFM-Migration-Assessment-ds.pdf)
- WFC end of support: cloud-hosted ended 31 Dec 2025; on-prem runs to 31 Mar 2027. [USER/partner blogs, not UKG primary] — [RSM](https://www.rsmus.com/insights/technology/ukg/ukg-workforce-central-support-is-ending-do-you-have-a-plan), [HealthcareITLeaders](https://healthcareitleaders.com/blog/ukg-workforce-central-wfc-end-of-life). Partners describe WFC to Pro WFM as a rebuild; WFC WIM integrations don't carry over to Pro WFM's Boomi-based framework. [USER/partner]
- Developer Hub has a GenAI search over docs/API specs (GPT-4/3.5 Turbo based). [FACT] — [Developer Hub GenAI Search](https://developer.ukg.com/general/docs/genai-search). Not configuration analysis.

### Inferences
- [INF] SDM is a transport mechanism with audit logging, not a comparison or assurance tool; drift detection between snapshots, orphan/invalid config checks, WFC to Pro WFM migration assurance and requirement-test traceability appear unserved natively. Confidence moderate: only help-page search summaries were available.
- [INF] Highest redundancy risk: environment compare (UKG could add a diff to SDM with modest effort, since it already reads items by name via REST). Lowest: requirement/test/defect traceability (those artefacts live outside UKG product, in Jira/ALM/spreadsheets).
- [INF] WFC to Pro WFM migration assurance: UKG has an assessment service and partners do the work; no native automated WFC-to-Pro conversion tooling found.

### Gaps
- Whether a native "compare" or configuration-report feature exists in current Pro WFM releases (2025-2026 release notes not read).
- Pro WFM "Integration Hub" run-history screen not confirmed.
- UKG-internal implementation tooling (accelerators/templates, "rapid deployment") not found beyond the Configuration Assistant mention.

## 4. Third-party relevance: UKG acquisitions, MCP, partnerships

### Takeaway
UKG has shipped a beta MCP-based "UKG in Claude" and has Google Cloud and ServiceNow agent partnerships, all aimed at customers' business users. No acquisition relevant to implementation engineering was found.

### Cited Findings
- 20 Oct 2026: UKG announced beta "UKG in Claude" (connector via MCP; plain-language questions on schedules, hours, pay rules, labor policies; can take supported actions limited to what UKG's platform permits under the customer's controls); described as the foundation of next-generation Bryte. [MKTG, beta] — [Business Wire](https://www.businesswire.com/news/home/20261020356990/en/UKG-in-Claude-Makes-AI-Work-Beyond-the-Chat), [MarketScreener](https://www.marketscreener.com/news/ukg-inc-announces-beta-availability-of-ukg-in-claude-with-anthropic-ce785cd8d08df02c), [HRTechEdge](https://hrtechedge.com/ai-in-hr/ukg-brings-workforce-data-and-ai-into-claude/)
- UKG engineering blog describes a single MCP gateway with progressive disclosure ("headless AI"). [vendor engineering blog; shipped extent unknown] — [UKG Engineering blog](https://www.ukg.com/for-llms/company/newsroom/engineering-blog/start-anywhere-ground-and-execute-ukg-engineering-behind-our-headless-ai)
- Google Cloud partnership (Oct 2025): Bryte agents built with Gemini/BigQuery; agents to support A2A protocol. [MKTG] — [Business Wire](https://www.businesswire.com/news/home/20251009579798/en/UKG-and-Google-Cloud-Partner-to-Transform-Work-with-Agentic-AI-for-Tens-of-Millions-of-Users)
- ServiceNow AI Agent Fabric connection for Bryte agents. [MKTG] — see Section 1.
- No UKG-Microsoft Copilot partnership found; Copilot Studio access to UKG Pro HCM exists only via third-party CData. [USER/3rd party] — [CData](https://www.cdata.com/kb/tech/ukgprohcm-cloud-copilot.rst). Merge, Apideck, StackOne, Knit, Vinkius sell third-party MCP servers for UKG Pro; Merge states UKG offers no MCP server purpose-built for Pro WFM (possibly outdated). [3rd party] — [Merge](https://www.merge.dev/connectors/ukg-pro-wfm)
- Acquisition: UKG agreed (Dec 2025) to buy Inova Payroll (SMB payroll/Ready reseller); not relevant to configuration engineering. [FACT] — [UKG newsroom](https://www.ukg.com/company/newsroom/ukg-agrees-acquire-inova-payroll). Argano (not UKG) acquired UKG partner Ascend (implementation services), May 2026. [3rd party] — [Pulse 2.0](https://pulse2.com/argano-acquires-ukg-services-partner-ascend-to-expand-workforce-management-and-hcm-capabilities/amp/)

### Inferences
- [INF] The MCP direction means UKG may expose a governed agent interface to its own data; a third-party tool using it would sit inside UKG's rules (next section). It does not by itself replicate offline artefact ingestion.

### Gaps
- Whether UKG in Claude covers Pro WFM configuration objects or admin use cases: not stated in the retrieved summaries.
- Agent marketplace listings (Google/other): not verified.

## 5. UKG policies on AI agents, automated access, API terms, data use

### Takeaway
Contract documents (as summarised) prohibit automated and agentic access to UKG services/data without UKG's written authorization, and bar scrapers/agents on Data Interfaces. A third-party tool should work from customer-exported files and synthetic data, or use UKG-sanctioned API/partner routes. Primary text was not read; legal review needed.

### Cited Findings
- MSA (July 2026 version) prohibits programmatic or automated access to services or data, expressly including AI programs and agentic access, unless UKG gives written authorization; requires compliance with the AUP. [FACT, per search summary of excerpt] — [MSA 2026-07-01 US](https://www.ukg.com/sites/default/files/2026-07/MSA-2026-07-01-US.EN_.pdf)
- AUP (1 July 2026) bars tools imitating a human user (robots), excessive automated requests, bulk extraction/replication, excessive polling/synchronisation, disproportionate automated load; violation can lead to suspension. [FACT, per summary] — [AUP 2026-07-01](https://www.ukg.com/sites/default/files/2026-07/AUP-English-2026-07-01.pdf), [HTML](https://www.ukg.com/for-llms/acceptable-use-policy)
- API Call Packs Services Description: use of UKG APIs subject to Exhibit A (UKG Data Interface Terms, version dated 2026.09.14); licence conditioned on compliance with those terms and Developer Documentation; bars spiders, crawlers, scrapers or agents on the data interfaces; UKG may monitor use and suspend for circumvention; 10 million calls per pack per tenant per month, no rollover. [FACT, per summary; the "agents" wording is from a single summary] — [API Call Packs SD](https://www.ukg.com/sharepoint/view/01WMTN4D3XI35U4LFZ7BC37IPT6C37O3TV)
- Website terms bar robots/spiders/scrapers. [FACT] — [UKG site terms](https://www.ukg.com/terms-of-use)
- Bryte AI: UKG may monitor use; outputs may be inaccurate; "Input"/"Output" defined in the Services Description. [FACT] — [Bryte SD](https://ukg.com/sites/default/files/2026-02/UKG-Bryte-Assistive-AI-for-Pro-HCM-for-UKG-Pro-Pay-and-or-UKG-Pro-People-Center-2026.02.03-English.pdf). Whether UKG trains on customer data was not established.
- Responsible AI: UKG states four core principles (only "Fairness and inclusiveness" and "Transparency by design" confirmed in retrieved text), safety/reliability, governance checks, and data/models in isolated private-cloud environments. [MKTG/policy statement] — [Responsible and ethical use of AI](https://www.ukg.com/for-llms/company/responsibility/responsible-and-ethical-use-ai), [ESG page](https://www.ukg.com/about-us/esg/governance/artificial-intelligence)
- Privacy/trust: [Privacy and data protection](https://www.ukg.com/for-llms/company/responsibility/privacy-and-data-protection); not read in detail.

### Inferences
- [INF] Any feature where our product's AI or automation logs into or calls a customer's UKG tenant would need UKG written authorisation and customer API entitlement; consistent with the project rule of no live tenant access. Ingesting customer-exported files avoids the automated-access clause but customer contract confidentiality terms for exports remain unchecked.
- [INF] Partner certification, data residency and any developer-portal-specific terms were not located.

### Gaps
- Full text of MSA clauses, Exhibit A, AUP: not read (fetch blocked). Quote from primary source before legal reliance.
- Partner/marketplace certification requirements, data-residency commitments, AI training-on-customer-data terms: not found.
- developer.ukg.com standalone "Terms of Use" page content: not retrieved.

## 6. Assessment per overlap (worth building? redundancy risk)

### Takeaway
Judgements below are inferences from limited evidence, not documented facts.

### Cited Findings
(see sections 1 to 5 for sources)

### Inferences
- Environment snapshot compare/drift: native overlap partial (SDM transports and audits but no diff found). Worth building: yes, with a note that UKG could add it. Redundancy ease: medium-high.
- Orphan/invalid configuration detection and dependency graph: no native equivalent found; Configuration Assistant unverified. Worth building: yes. Redundancy: medium (UKG has the internal schema; Bryte could explain config).
- Deterministic change-impact analysis: no native equivalent found. Worth building: yes. Redundancy: medium-low in near term.
- Requirement/test/defect traceability: artefacts live outside UKG; native overlap unlikely. Redundancy: low.
- Evidence-backed diagnostics: overlaps Bryte assistants, Developer Hub GenAI search and "UKG in Claude" for explanation. Redundancy: high for generic Q&A; low for artefact-grounded provenance.
- WFC to Pro WFM migration assurance: UKG offers assessment services; partners dominate; no native tool found. WFC support window closing (on-prem 31 Mar 2027 per partner sources) shrinks the market over time. Redundancy: low-medium; demand window is time-limited [INF].
- Implementation governance: no native product found.

### Gaps
- All ratings are untested against UKG's non-public roadmap and customer-only Community documentation, which the search could not reach.
