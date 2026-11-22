# UKG Pro WFM architecture, configuration model, export and API access (as of 2026-11-18)

**Method caveat (read first):** WebFetch could not resolve developer.ukg.com, library.ukg.com, ukg.com or mykronos.com help hosts (sandbox network allowlist). Every finding below comes from WebSearch result summaries only, not from reading the full pages. Treat all as "snippet-level, not page-verified". Labels: [DOC] official UKG source, [PARTNER/3P] third-party, [INFER] my inference. Many help URLs are customer-hosted or mykronos.com mirrors of UKG help, possibly older (Dimensions/WFC-era) versions.

## 1. Platform architecture, release cadence, tenants/environments

### Takeaway
Pro WFM is a UKG-hosted SaaS on Google's public cloud, versioned as year.R1/R2 releases plus numbered Express Upgrades, with separate production and non-production tenants. Multi-tenancy, exact cadence and partner-vs-customer tenant distinctions were NOT verified.

### Cited Findings
- [DOC, snippet] Pro WFM environments run on the UKG Platform and are hosted in Google's public cloud. UKG announced (Oct 2025) Pro WFM on Google Cloud Marketplace and BigQuery/agent integrations expected in 2026 — [UKG release notes landing](https://sso-hlp01.mykronos.com/help/en_US/Content/ReleaseNotesLanding.htm); [UKG/Google press release, 2025-10-09](https://www.businesswire.com/news/home/20251009579798/en)
- [DOC, snippet] Release notes are organised by year and release (e.g. 2024R1, 2024R2) with Express Upgrades listed within a release or in an Update Summary; 2024.R1 notes list Express Upgrades up to ~11. Upgrade confirmation for Pro WFM customers comes via the UKG Trust Site — [2024R1 release notes](https://sso-hlp01.gss.mykronos.com/help/setup/Content/Resources/ReleaseNotesPDFs/ProWFM_2024R1_ReleaseNotesRevK.pdf); [release notes landing](https://dcus11-hlp01.gss.mykronos.com/help/HCM/branding_dimensionsrelease_notes/WFM_Release_Notes_Landing_Page.html)
- [DOC, title only] A UKG datasheet "UKG Pro WFM non-Production Environments" exists (2023); content not read — [PDF](https://www.ukg.com/sites/default/files/2023-09/DIY0365-USv2-UKG-Pro-WFM-non-Production-Environments-DS.pdf)
- [DOC, snippet] Best practice: configure in a non-production tenant, test, then migrate to production via SDM — [SDM help](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/CopySetupData.htm)

### Inferences
- [INFER] "Dev/test/prod" exist as separate tenants because SDM publishes tenant-to-tenant. Number/types of non-prod tenants are contract-dependent (unverified).

### Gaps
- Whether the architecture is formally "multi-tenant" on GCP, and the release cadence (releases per year, dates for 2026 R1/R2): not found. Community release-information page not accessible.
- Partner tenants vs customer tenants: nothing found.

## 2. Configuration entities and relationships

### Takeaway
UKG help documents the entities and several relationships (work rule uses pay rules/building blocks; accrual profile = collection of accrual policies assigned via employment terms; paycodes map to payroll via Payroll Code Mapping). The full chain employee→pay rule→work rule→paycode is not confirmed as documented in what I could read.

### Cited Findings
- [DOC, snippet] Work rules are combinations of work rule building blocks that apply specific pay rules to shifts; building blocks are reusable across work rules. Pay rule building blocks are constant within payroll policies, not shift-dependent — [Pay rules reference](https://library.ukg.com/Prebuilt/newgen/WorkforceMgmt/Content/WFMPayRules-r_x52705.html); [Pay rule groups](https://library.ukg.com/Prebuilt/newgen/WorkforceMgmt/Content/WorkforceManagementPayRuleGroups-t_x37749.html)
- [DOC, snippet] Paycodes organise earned time/money; they map to payroll via Payroll Code Mapping (Administration > Time application setup > Integrations Setup > Payroll) — [Paycodes](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/paycodes.html); [Payroll to Paycode Mappings](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/configure_payroll_to_paycode_mappings.html)
- [DOC, snippet] An accrual profile is a collection of accrual policies determining accrual balances; profiles have effective dates, assignments cannot overlap; profiles can be assigned directly on employment terms and multiple employment terms may differ — [Accrual profiles](https://sso-hlp01.gss.mykronos.com/help/en_GB/Content/ApplicationSetup/Accruals/AccrualProfiles.htm)
- [DOC, snippet] Employee assignment templates: the Timekeeping template covers employment terms, pay rules, transfer sets, device groups, work rule profiles; the Accruals template covers accrual profiles, cascade profiles, full-time equivalency — [Add Pro WFM settings for a new employee](https://library.ukg.com/a/182170)
- [DOC, snippet] Accrual day boundary ("day divide") is defined in a pay rule — [Accruals setup reference](https://dcus11-hlp01.gss.mykronos.com/help/HCM/administration/Time_Application_Setup/Accruals/accruals_setup_reference/accruals_setup_reference_98714.html)
- [DOC, title only] Pages exist for holiday credit rules building blocks and Create an Accrual Code — [Holiday credit rules](https://hlp02.gss.mykronos.com/help/HCM/administration/Application_Setup/Pay_policies/holiday_credit_rules_building_blocks_320647.html); [Create accrual code](https://library.ukg.com/Prebuilt/newgen/WorkforceMgmt/Content/WFMTOACreateAccrualCode-t_x120669.html)
- [DOC, snippet] Access to SDM requires Function Access Profile and Generic Data Access Profile permissions, confirming those security entities exist — [SDM help](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/CopySetupData.htm)

### Inferences
- [INFER] Plausible chain: person → employment terms → (pay rule, work rule profile, accrual profile) → work rule → paycodes. Only the employment-terms→accrual profile and employment-terms/timekeeping-template contents are supported above. Treat the rest as unverified.

### Gaps
- Not verified at all (no snippet evidence): combination rules, pay code distributions, overtime/zone rules, shift/pattern templates, schedule rule sets, org map/location types/labor categories, primary job, display profiles, employee groups, manager roles, GDAP internals. Exact UKG entity names for these need the library.ukg.com pages.
- Workforce Central (WFC) vs Pro WFM naming differences not checked; some results are from Classic/older help.

## 3. Export / migration mechanisms

### Takeaway
SDM is the documented config transfer tool (tenant-to-tenant publish and tenant-to-file export/import). File format and schema were not found in public docs I could see. Reports, Dataviews and Boomi-based Integration Hub are the other routes.

### Cited Findings
- [DOC, snippet] SDM supports Copy Setup Data (tenant to tenant) and Export Setup Data (tenant to file), plus import from file then Publish — [Copy](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/CopySetupData.htm); [Export](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/ExportSetupData.htm); [Supported data](https://sso-hlp01.mykronos.com/help/en_US/Content/SDM/SetupDataManagerSupportedData.htm)
- [DOC/customer-hosted copy, older, snippet] Source and destination must be the same application version; back up before import; SDM does not support Delegate Profiles and Unpublished Reports; v7.3 added gray-number validation using GUIDs on export/import (Kronos/WFC-era wording) — [customer-hosted help](https://emstelestaff.albertahealthservices.ca/help/Content/Access/Components/IM_c.htm)
- [DOC, snippet] Pro WFM Integration Hub is built on Boomi; Boomi Empowerment service offers starter import/export templates; extensions exist such as Transfer Report to SFTP; Report Library holds completed reports — [Integration Hub profile](https://www.ukg.ca/sites/default/files/2023-09/DIY0262-v2-UKG-Pro-Integration-Hub-Product-Profile.pdf); [Boomi DS](https://www.ukg.in/sites/default/files/2023-09/IN-EN-sv0331-usv5_boomi%20empowerment%20DS_IN.pdf); [Transfer Report to SFTP](https://dcus11-hlp01.gss.mykronos.com/help/HCM/administration/Extensions/Transfer_Report_to_SFTP/transfer_report_to_sftp.html)
- [DOC, title only] Dataviews and Reports help section exists — [Dataviews/reports](https://hlp02.gss.mykronos.com/help/HCM/dataviews_and_reports/dataviewsreports_50549.html)
- [3P] CData and Celigo offer connectors for UKG Pro WFM — [CData](https://www.cdata.com/apidriver/profiles/ukgprowfm/); [Celigo](https://docs.celigo.com/hc/en-us/articles/18706534695707)

### Inferences
- [INFER] Because SDM requires identical versions and GUID validation, SDM files are likely a tool-internal, version-coupled format; we should not plan to parse them without a UKG-provided spec.

### Gaps
- SDM file format (XML/JSON/CSV), schema, and whether it is publicly documented: NOT found. Do not assume.
- A "configuration as data" export API or Dataview covering config: not found.

## 4. Official APIs, auth, webhooks, bulk

### Takeaway
UKG publishes a Pro WFM API reference on developer.ukg.com with UKG Authentication (client credentials among supported flows; credentials made in Administration > Developer Console). Specific configuration endpoints, webhooks and bulk APIs were not verified.

### Cited Findings
- [DOC, snippet] Pro WFM supports UKG Authentication with three application flows for obtaining access tokens, including Client Credentials for system-to-system; requires app key, client ID, client secret — [UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc); [WFM reference](https://developer.ukg.com/wfm/reference)
- [DOC, snippet] Credentials are managed in Administration > Developer Console (revoke/rotate; metadata with creation and usage timestamps) — [Developer Console Quick Start](https://developer.ukg.com/proplatform/docs/developer-console-quick-start)
- [DOC, snippet] Docs advise handling HTTP 429, honouring Retry-After, exponential backoff; a WFM "limits" page exists but no numeric limits seen — [WFM limits](https://developer.ukg.com/wfm/docs/limits-doc); [Auth doc](https://developer.ukg.com/talk/docs/ukg-authentication-doc)
- [3P] Nango documents both ROPC and client-credentials variants for Pro WFM with tenant-specific base URL — [Nango CC](https://nango.dev/docs/api-integrations/ukg-pro-wfm-cc/connect); [Nango ROPC](https://nango.dev/docs/api-integrations/ukg-pro-wfm-ropc/connect)
- UKG Pro HCM core REST APIs use Basic auth with a web service account; separate product from WFM — [UKG Pro API](https://developer.ukg.com/hcm)

### Inferences
- [INFER] A read-only API client for config endpoints would need customer-admin-issued credentials per tenant.

### Gaps
- Actual endpoint paths for config objects (paycodes, work rules, etc.), pagination, webhooks/event notifications, bulk export APIs: not verified. Do not cite any path from this note.
- Numeric rate limits: unpublished in sources seen. Ignore forum.sggu.com results (different platform).

## 5. Access constraints, partners, terms, sandbox

### Takeaway
Credentials appear to be customer-admin provisioned per tenant; partner/Marketplace route and developer-portal sign-up terms are unverified.

### Cited Findings
- [DOC, snippet] Developer Console access is role-based (Super Access role / Access Profile grants) — [Developer Console Quick Start](https://developer.ukg.com/proplatform/docs/developer-console-quick-start)
- [DOC] UKG Partner Marketplace lists 245+ technology, carrier and services partners — [UKG blog](https://www.ukg.com/blog/life-ukg/power-platform-extension-through-technology-partners)
- [3P opinion, July 2026] API report card claims no self-serve developer path, customer admin must provision a service account, and Marketplace approval/fees often needed — [Supergood](https://supergood.ai/api-report-card/ukg)

### Inferences
- [INFER] For this product, access realistically means customer-granted credentials on a customer non-prod tenant, or file-based ingestion of customer-supplied exports.

### Gaps
- Partner application steps, fees, terms-of-use restrictions on data, sandbox availability for developers: not found.

## 6. Pro WFM vs UKG Pro (HCM) vs UKG Ready

### Takeaway
Pro WFM and UKG Pro HCM have separate API families and auth; Ready is a separate product with its own docs.

### Cited Findings
- [DOC] UKG Pro HCM APIs live under developer.ukg.com/hcm with Basic auth via web service account; Pro WFM under /wfm with UKG Authentication — [HCM](https://developer.ukg.com/hcm); [WFM](https://developer.ukg.com/wfm/reference)
- [DOC, snippet] Pro WFM has a UKG Pro paycode payroll mapping option, i.e. integration with UKG Pro payroll — [Paycode mappings](https://dcus11-hlp01.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/configure_payroll_to_paycode_mappings.html)
- [3P] Rollout lists Pro WFM, Pro and Ready as distinct integration guides — [Rollout Pro WFM](https://rollout.com/integration-guides/ukg-pro-workforce-management/api-essentials)

### Inferences
- [INFER] "Pro WFM" scope = the former Dimensions product (and name per UKG release notes "Pro Workforce Management / Pro WFM"). Ready and WFC are out of scope.

### Gaps
- Formal UKG statement of product lineup/renaming dates not retrieved.

## What could NOT be verified (summary)
All pages were read via search snippets only (fetch blocked). Unverified: SDM format, config API endpoints, webhooks, rate-limit numbers, partner requirements, release cadence, multi-tenant claim, entities in scheduling/org/security, full relationship chains. To close gaps, allow developer.ukg.com, library.ukg.com, *.mykronos.com and www.ukg.com in the session network settings, or get a customer-supplied login export.
