# WFC architecture, configuration model, and WFC to Pro WFM migration (as of 2026-11-18)

**Research limits (read first).** WebFetch was blocked in this session (hosts www.ukg.com, rsmus.com, healthcareitleaders.com, workaxle.com failed DNS/allowlist). All findings below come from WebSearch result summaries, not full-page reads. No UKG primary page was read in full. Every claim is therefore secondary unless stated. Claim classes: [DOC] documented (vendor/primary or customer-institution page), [PARTNER] vendor/partner claim, [USER] user/customer report, [INF] my inference.

## 1. WFC architecture (on-prem/hosted, versions, DB, XML API, WIM)

### Takeaway
Only thin evidence found. WFC exposes a Developer's Toolkit XML API and Integration Manager (WIM) interfaces, and ran on Oracle or SQL Server. No official architecture document was read.

### Cited Findings
- [DOC, old/unofficial copy] A Workforce Integration Manager User's Guide (Kronos Workforce Central Suite Version 6, rev A, Jan 2009) describes an interface as a file (.KNI) containing steps for a data transfer — [Scribd copy](https://www.scribd.com/document/50779743/Users-Guide-Integration-Manager) (dated; unofficial upload)
- [DOC, unofficial copy] A "WFC 8.1 Integration Manager Developer's Toolkit" reference says it defines the XML API, covering timekeeping, scheduling, attendance, data integration, device manager, leave, budgeting — [Scribd](https://www.scribd.com/document/696889274/WFC81-IntegrationMgrDTKRef)
- [PARTNER/third party] A third-party integration doc says the API is the Developer's Toolkit XML gateway, a single endpoint (/wfc/XmlService) accepting XML request envelopes — [Serval docs](https://docs.serval.com/sections/integrations/kronos) (treat as example, not vendor spec)
- [DOC title only] Kronos published a Database Tables Reference Guide and a Database Administrator's Guide covering Oracle and SQL Server 2000 for Workforce Timekeeper; contents not seen — [Scribd Database Reference Guide](https://www.scribd.com/document/58090725/Kronos-Database-Reference-Guide) (dated, unverified)
- [USER/third party] An interface table INF_CV_WORKRULES holds Work Rules Interface File data — [NEOGOV wiki](https://ccare.neogov.com/Wiki/Wiki.jsp?page=IVDWR) (interface table, not core schema)

### Inferences
- [INF] Oracle and SQL Server are the supported DBs for WFC; version-specific support matrices (6.x vs 8.x) were not retrieved.

### Gaps
- Official on-prem vs UKG-hosted architecture description, 6.x/8.x version list, application server (not found), Workforce Connect details: not verified.

## 2. Core WFC configuration entities and labor levels vs Pro WFM business structure

### Takeaway
No source read that documents field-level entity models. Evidence only confirms that the business structure must be redesigned rather than copied, and that custom WIM-based rules do not map natively.

### Cited Findings
- [DOC, secondary] Setup Data Manager copies non-historical setup data between databases, including access profiles, work rules, pay codes and labor level entries — [Kronos help search result](https://hlp03.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/uber_incentives.html) (result was a loosely related page; verify)
- [USER] A Vancity user said business structure is the "backbone of Dimensions", must be settled before configuration, and took four iterations plus an outside consultant — [Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/)
- [PARTNER] Business structure, custom rules and integrations "all have to be rebuilt"; custom overtime/bonus/premium logic in WIM does not carry natively — [Workaxle](https://www.workaxle.com/blog/kronos-workforce-central-end-of-life-migration) (competing vendor, advocacy)
- [DOC, customer] UCSB: the Reports To field on each assignment replaced ACN and TMAA for manager visibility/approval — [UCSB timekeeping](https://timekeeping.ucsb.edu/ucsb-timekeeping-refresh-project) (a concrete documented model difference, access/approval)

### Inferences
- [INF] Labor levels (WFC, fixed-depth hierarchy) vs business structure (Pro WFM) are structurally different; this is consistent with the "not interchangeable" premise, but no source read states the technical difference.

### Gaps
- Official definitions of pay rule, work rule, combined pay code, accrual, schedule group, labor account, FAP vs Pro WFM equivalents: not found. Not verified.

## 3. WFC export/transfer mechanisms

### Takeaway
Known mechanisms: Setup Data Manager (setup copy), Integration Manager/WIM interfaces, XML API, DB tables. Formats beyond .KNI interface files not verified.

### Cited Findings
- See section 1 and: Setup Data Manager uses the system REST APIs to copy setup data — [Kronos help](https://hlp03.gss.mykronos.com/help/HCM/oxy_ex-2/_shared/common_topics/uber_incentives.html) (version applicability unclear)
- [DOC title only] Record Manager and Import guides exist — [Scribd RecordManager](https://www.scribd.com/document/270074858/RecordManager-User-Guide), [Scribd Import guide](https://www.scribd.com/doc/56949741/KronosImportGuide)

### Gaps
- Export formats (XML schema, CSV layouts), reports-based exports, whether SDM output is portable to Pro WFM: not found.

## 4. End-of-life and official messaging

### Takeaway
Consistent across secondary sources: announced 2022-10-20; cloud (Kronos Private Cloud) EOL 2025-12-31; on-prem end of engineering 2025-12-31 and EOL 2027-03-31. UKG's named path is UKG Pro WFM (formerly Dimensions). UKG primary page was not read.

### Cited Findings
- [PARTNER] Retirement announced Oct 20, 2022; extension "extremely unlikely" — [Healthcare IT Leaders](https://healthcareitleaders.com/blog/ukg-workforce-central-wfc-end-of-life)
- [PARTNER] RSM lists EOL 12/31/25 (private cloud), on-prem end of engineering 12/31/25, on-prem EOL 3/31/27 — [RSM](https://www.rsmus.com/insights/technology/ukg/ukg-workforce-central-support-is-ending-do-you-have-a-plan)
- [DOC, unread] UKG policy page exists — [UKG WFC Support Policies](https://www.ukg.com/wfc-support-policies-and-services); only partly visible, dates not confirmed from it
- [DOC, customer] UCSB notice says unsupported after December 2025 (cloud-version date) — [UCSB IT](https://it.ucsb.edu/news/announcing-ucsbs-new-timekeeping-system-launching-may-2025)
- [PARTNER] Kronos 4500 clocks retired; InTouch DX required — [Cloudapper-related sources via search](https://ukg.cloudapper.ai/time-capture/elevating-workforce-management-cloudapper-ai-timeclock-for-ukg-wfc/); contradicted in part by UCSB, which says its clocks needed only a software upgrade — [UCSB](https://it.ucsb.edu/news/timekeeping-refresh-update-training-resources-and-transition-information) (model-dependent)

### Inferences
- [INF] As of 2026-11-18, cloud support has ended and on-prem hard stop is ~4.5 months away (2027-03-31). Sources differ (some say 2025 vs 2027) because of the cloud/on-prem split.

### Gaps
- Read and confirm UKG primary notice; no newer UKG notice changing dates found.

## 5. How migrations are done in practice

### Takeaway
Partners describe a rebuild-heavy migration with some UKG tooling for configuration. The tool is not named in any source I saw.

### Cited Findings
- [PARTNER] UKG offers tools to migrate much of the configuration; Advanced Scheduling needs extra effort; straight vs optimized migration options — [Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/)
- [PARTNER] Timecard and schedule history does not transfer; archive the WFC database — same source
- [PARTNER] WIM-based integrations do not carry to Pro WFM's Boomi-based framework; custom WIM rules not natively supported — [Workaxle](https://www.workaxle.com/blog/kronos-workforce-central-end-of-life-migration) (competitor)
- [PARTNER] 6-9 months before testing/training; ~15 months end to end for full enterprise — same; partner estimate only
- [DOC] UKG publishes a "Pro WFM Migration Assessment" datasheet — [UKG PDF](https://www.ukg.com/sites/default/files/2023-09/SV0252-USv4-UKG%20Pro%20WFM-Migration-Assessment-ds.pdf) (not read)
- [DOC, customer] UCSB went live May 11, 2025; pay history visible in WFC only through period ending 4/26/2025, with reconciliation requested before cutoff — [UCSB](https://timekeeping.ucsb.edu/news/important-update-timecard-reconciliation-ukg-pro-wfm-transition)
- [DOC, customer] UC Berkeley phased only complex 24-hour-shift groups (May 2026); UC San Diego moved Feb 1, 2026 — [Berkeley](https://caltime.berkeley.edu/caltime-replacement-project), [UCSD](https://rrsshr.ucsd.edu/timekeeping/index.html)

### Inferences
- [INF] Real documented problems: integrations rebuild, history not migrated, business structure redesign (user report). Rule redesign is partner-claimed; not independently documented.

### Gaps
- Name/documentation of UKG's configuration migration tool, what exactly converts automatically, UKG Professional Services methodology: not verified (likely login-walled or unread).

## 6. Validation approaches and comparison tools

### Takeaway
No WFC-vs-Pro-WFM-specific comparison tool or UKG validation method found. Generic parallel-pay practice exists.

### Cited Findings
- [Generic, other vendors] Parallel test: same pay period, same time data, document variances; at least three iterations suggested — [HCM TradeSeal](https://hcmtradesealsupport.zendesk.com/hc/en-us/articles/38981387999771), [Wipro](https://www.wipro.com/blogs/sunil-kumar/making-payroll-migration-painless-flawless-and-timely/)
- [Generic] Dayforce Payroll Comparison wizard uploads legacy payroll for comparison — [Dayforce help](https://help.dayforce.com/r/documents/Activate-User-s-Guide/Payroll-Comparison) (different vendor; pattern only)
- [Vendor claim, unseen] Datavail "PayMatch" appeared in results for payroll comparison — [Datavail](https://www.datavail.com/technologies/paymatch/); relevance to UKG not verified

### Inferences
- [INF] This suggests a gap for an assurance product, but no evidence of demand or absence of tools beyond one search; do not state as fact.

### Gaps
- UKG-provided or partner WFC to Pro WFM reconciliation tooling: not found.

## 7. Documented non-interchangeability

### Takeaway
Documented differences found: history not migrated; WIM vs Boomi integrations; business structure redesign; Reports To vs ACN/TMAA; hardware. Schema-level differences not verified.

### Cited Findings
- All from sections 2 and 5: [Healthcare IT Leaders](https://www.healthcareitleaders.com/blog/ukg-dimensions-migration-what-customers-should-know/), [UCSB](https://timekeeping.ucsb.edu/ukg-pro-wfm-enhancement-function-access-profile-fap-changes), [Workaxle](https://www.workaxle.com/blog/kronos-workforce-central-end-of-life-migration)

### Gaps
- Field/object-level mapping documentation; Pro WFM API/export formats (out of scope here); Reddit/forum user reports not searched.
