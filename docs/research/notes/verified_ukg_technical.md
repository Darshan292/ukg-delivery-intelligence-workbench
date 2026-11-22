# Verified UKG technical facts: Pro WFM config access, SDM, WFC end of life, PyMuPDF licensing (checked 2026-11-18)

**Access method and limits (read first).** WebFetch could not resolve any of the target hosts (ENOTFOUND). `curl` through the proxy did work, so I read these pages in full: developer.ukg.com (several pages), artifex.com/licensing, pymupdf.readthedocs.io. Blocked: www.ukg.com (Cloudflare "Just a moment..." challenge, HTTP 403, for /wfc-support-policies-and-services and /for-llms/wfc-support-policies-and-services); every *.mykronos.com help host (proxy CONNECT 403, so none of the SDM help pages were readable); preview.web.ukg.com emails (same). library.ukg.com/a/196247 returned a PDF that turned out to be the UKG Pro (HCM) Import Tool guide, not SDM, so I discarded it. library.ukg.com Prebuilt/newgen SDM URL returned 404. Labels: [PRIMARY-READ] = full page read by me; [SNIPPET] = search snippet only; [3P] = third party; [INFER] = my inference. Quotes are verbatim from the page text.

## 1. developer.ukg.com Pro WFM API: auth, provisioning, limits, config endpoints, webhooks, bulk

### Takeaway
CONFIRMED and strengthened. Pro WFM has three documented auth flows, including a non-interactive Client Credentials flow, with credentials provisioned by a customer admin. Config/setup objects are readable by documented REST operations (pay codes, pay rules, work rules, accrual profiles/codes, employment terms, labor categories, locations, function/data access profiles). No numeric request-rate limit is published (throttling is 429; limits are per-request size caps). Webhooks exist but their event catalogue was not readable. No documented bulk export of configuration.

### Cited Findings
- [PRIMARY-READ] Three flows: "There are three application flows (methods) that can be leveraged to obtain an access token using UKG Authentication". Authorization Code is "the preferred method for new clients"; ROPC "is the default method for current clients"; Client Credentials "is tailored for system-to-system communications where impersonation of a named Pro WFM user is not necessary... appropriate for use cases such as executing scheduled integrations. Each client will be associated with a FAP that defines the level of access the client ID is allowed." — [UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc)
- [PRIMARY-READ] Provisioning in the product UI: "Administration > Application Setup > Common Setup > Client Management". "Client Credentials are tenant specific, therefore credentials created on a non-production cannot be used to get a token for a production tenant." "Once a client has been created, the client secret cannot be recovered". Recommends "one set of client credentials for each application". Token endpoint shown: `https://welcome-us.ukg.net/oauth/token`; audience fixed `https://wfm.ukg.net/api`. — same page
- [PRIMARY-READ] Limitation: "User-specific audits or user-specific context is not supported for Client Credential". "Only use ROPC if you need to access specific endpoints that are not available using the client credentials method." ROPC for batch is "not supported for high-volume or batch integrations". "Requests to whitelist IP ranges or relax authentication protections are not supported". Token lifetimes: "Access tokens expire after 30 minutes and refresh tokens expire after 8 hours. These time limits are subject to change without notice." — same page
- [PRIMARY-READ] Developer Console: "The Developer Console is only available in UKG Authentication environments." Admins can "Create and manage machine-to-machine API credentials", "Assign and control access using existing role-based permissions", "Revoke or rotate credentials". Pro WFM path: "Menu > Administration > Developer Console"; for Super Access users the FAP route is "Application Setup > Access Profile > Functional Access Profile > Super Access > APIs > Developer Console". "replaces manual or ticket-based provisioning processes". — [Developer Console Quick Start](https://developer.ukg.com/proplatform/docs/developer-console-quick-start) (page marked "Updated 7 months ago")
- [PRIMARY-READ] Rate limits: no requests-per-second/minute number published on the Limits page. It says "The HTTP status code for throttling is 429" and service limits (HTTP 413) "constrain the number of employees and the time range" per request. Documented numbers: Business Structure "Number of Jobs cannot exceed 5,000"; Hyperfind days <= 365, employees <= 10,000, locations <= 10,000, response count <= 50,000 (default 3,500 for Execute Hyperfind Query); Information Access days <= 365, employees <= 500, locations <= 300. Auth page: "Expect HTTP 429 ... Honor Retry-After headers; Implement exponential backoff". — [Limits](https://developer.ukg.com/wfm/docs/limits-doc); [UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc)
- [PRIMARY-READ] Documented v2 setup/config read paths (from the v1-to-v2 replacement table, which lists each as "GET /v2/... replaces GET /v1/..."): `/v2/timekeeping/setup/pay_codes`, `/v2/timekeeping/setup/accrual_codes`, `/v2/timekeeping/setup/accrual_profiles` (+`/{id}`), `/v2/timekeeping/setup/payrules` (GET and POST), `/v2/timekeeping/setup/work_rules` (+`/{id}`), `/v2/timekeeping/setup/employee_work_rules`, `/v2/timekeeping/setup/employee_pay_codes`, `/v2/timekeeping/setup/pay_code_symbolic_values`, `/v2/timekeeping/setup/employment_terms` (+`/{id}`), `/v2/timekeeping/setup/deduct_rules`, `/v2/scheduling/setup/schedule_groups`, `/v2/commons/labor_categories`, `/v2/commons/labor_entries`, `/v2/commons/cost_centers`, `/v2/commons/hours_operation`, `/v2/commons/location_sets/multi_read`, `/v2/commons/persons/paycode_value_profiles`, `/v2/commons/persons/schedule_rule_overrides`. "We recommend you update your implementations to utilize version 2 operations". — [Version 2 resources and operations](https://developer.ukg.com/wfm/docs/version-2-resources-and-operations-doc)
- [PRIMARY-READ] Other documented paths: `GET /v1/timekeeping/setup/employment_terms`; `/v1/commons/persons/employment_terms`; `GET /v1/commons/function_access_profiles`; `POST /v1/commons/hyperfind/execute`; `/v1/timekeeping/setup/break_rules/{id}`. — [Employment Term Assignments](https://developer.ukg.com/wfm/docs/employment-term-assignments-doc); [Configure access for a person](https://developer.ukg.com/wfm/docs/configure-access-for-a-person-doc); [Limits](https://developer.ukg.com/wfm/docs/limits-doc); [API reference](https://developer.ukg.com/wfm/reference)
- [PRIMARY-READ, titles only] The API reference page lists operation titles (full paths are not in the static HTML except as above). Resource groups visible include: "Timekeeping Pay Rules" (Retrieve All / Create / Update / Delete, plus multi-read), "Overtime Rules", "Work Rules" (Retrieve All Work Rules, Create/Update/Delete), "Accrual Policies", "Accrual Profiles" (Retrieve All Accrual Profiles; Create or Update Accrual Profiles), "Combination Rules", "Combined Paycodes for Timekeeping", "Employment Terms" (Retrieve/Create/Update Versions/Delete), "Paycode Distributions", "Pay Code Tags", "Function Access Profiles" (CRUD), "Generic Data Access Profiles", "Paycode Data Access Profiles", "Work Rule Data Access Profiles", "Labor Category Lists/Profiles/Entries", "Location Types", "Locations" (Retrieve Location by Path, Create Location Node, Copy/Move Location), "Location Sets", "Zone Categories", "Schedule Zone Sets", "Payroll Job Maps", "Employment Status to Labor Type Maps", "Dynamic Event Notification Mappings", "Domain Events", "Batch Events". Many have "Create/Update/Delete" siblings, i.e. the API is read-and-write for setup objects. — [API reference](https://developer.ukg.com/wfm/reference)
- [PRIMARY-READ, titles only] Person-assignment guides list assignment resources: Employment Term Assignments, Cascade Profile Assignments, Leave Profile Assignments, Process Profile Assignments, Schedule Rule Set Assignments, Paycode Value Profile Assignments, plus "Aggregated" variants. — [Limits page navigation](https://developer.ukg.com/wfm/docs/limits-doc)
- [PRIMARY-READ] Webhooks: "UKG Webhooks allows users to subscribe to the events described in the following specification. ... The payload sent by each event to the designated endpoint URL resembles the examples provided". The event list lives in a separate specification (https://developer.ukg.com/wfm/reference/wfm-webhook-events) which I did not read; the "UKG Webhooks User Guide" is referenced but not read. — [Welcome to WFM Webhook Events](https://developer.ukg.com/wfm/docs/wfm-webhook-events)
- [PRIMARY-READ, titles only] Bulk-type operations exist, but for transactions, not config export: "Bulk Import Paycode Edits", "Bulk Import Punches", "Bulk Accrual Payout/Reset", "Bulk Timecard Approvals", "Export Payroll Asynchronously", and a "Bulk Downloads" retrieval ("Retrieve Download Request Summary"). I found no config-wide export/bulk-download API; unverified whether "Bulk Downloads" covers setup data. — [API reference](https://developer.ukg.com/wfm/reference)

### Inferences
- [INFER] A third-party tool can read most Timekeeping setup objects with a Client Credentials client whose FAP grants the needed read access, but the customer admin must create it per tenant (credentials are tenant-specific). "Only use ROPC" for endpoints Client Credentials lacks implies some endpoints are ROPC-only (unknown which).
- [INFER] Whether GET responses return every attribute needed to reconstruct relationships (e.g., work-rule building blocks, pay-rule internals) is not shown by what I read; sample employment-term responses do return nested `payRule`, `accrualProfile`, `holidayProfile`, `workHours.payCode` references with id/name.

### Gaps
- Full path list and response schemas: reference page is JS-rendered; only titles and the paths above were visible. Do not cite paths beyond those listed.
- Webhook event catalogue (does it include setup-object change events?): not read. Earlier claim: unverified.
- Developer-portal sign-up, partner/Marketplace terms, "UKG Developer Policy" restrictions on data use: not read. The prior "Supergood" claim (no self-serve developer path) stays [3P], unverified.
- A numeric request-rate limit: none published on pages read.

## 2. Setup Data Manager (SDM) and "Compare setup items"

### Takeaway
UNVERIFIED beyond snippet level. All SDM help pages sit on *.mykronos.com or library.ukg.com paths that were blocked or 404 from this environment. The only new evidence is a search-result summary of the SDM page. Export file format remains undocumented in anything I could read.

### Cited Findings
- [SNIPPET, search-result summary of UKG help] The SDM page has a step to "Compare setup items and highlight a row to compare setup items on your source and target servers"; "When you open SDM, the Target is the tenant where you are logged in"; "SDM uses the system's REST APIs to copy setup data"; some data types are unsupported with a link to a supported-data list. — [Copy Setup Data (Tenant to Tenant)](https://sso-hlp01.mykronos.com/help/en_US/Content/SDM/CopySetupData.htm) and [AU mirror](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/CopySetupData.htm) (fetch failed: proxy CONNECT 403)
- [SNIPPET, carried from earlier notes] Export Setup Data (tenant to file), Supported Data page, SDM needs Function Access Profile and Generic Data Access Profile permissions — [Export](https://hlp03.gss.mykronos.com/help/en_AU/Content/SDM/ExportSetupData.htm), [Supported data](https://sso-hlp01.mykronos.com/help/en_US/Content/SDM/SetupDataManagerSupportedData.htm). Still unverified (fetch failed).

### Inferences
- [INFER] "SDM uses REST APIs" suggests the setup objects SDM copies are reachable by the same public setup APIs, but that is not stated by UKG for the public API.

### Gaps
- Exactly what Compare outputs (field-level diff? item-level?), export file format, exclusions, version constraints, required access: NOT verified. Earlier-note claims (same-version requirement, GUID validation, no Delegate Profiles/Unpublished Reports) came from a customer-hosted WFC-era copy and remain "unverified (snippet only)" and possibly WFC-specific.
- To close: allow `*.mykronos.com` (sso-hlp01, hlp03.gss, dcus11-hlp01.gss, hlp02.gss) in the session network, or supply a library.ukg.com SDM URL that returns HTML.

## 3. Configuration audit trail / change history for setup items

### Takeaway
No documented who-changed-which-setup-item audit trail found. Evidence suggests none is exposed via the public API; this stays unverified for UI/reports.

### Cited Findings
- [PRIMARY-READ] Client Credentials has no user context: "User-specific audits or user-specific context is not supported for Client Credential" — [UKG Authentication](https://developer.ukg.com/talk/docs/ukg-authentication-doc). (Concerns API actions made by a client, not setup edit history.)
- [PRIMARY-READ, titles only] Audit-type operations in the reference are for operational data: "Attendance Audit Records", "Leave Audit Records", "Schedule Audits", "Forecasting Audits", "Activity Move Quantity Transaction Audits"; none named for pay rules/work rules/paycodes setup. — [API reference](https://developer.ukg.com/wfm/reference)
- [SNIPPET] Release note: global property `global.payrule.single.entry.history.enabled` retains the previous pay-rule assignment in history when assigned via API; this is assignment history for a person, not rule-edit history. I could not locate the text in the release-notes page text I downloaded. — [Release notes](https://developer.ukg.com/wfm/docs/release-notes-doc) (search summary only)

### Inferences
- [INFER] Setup change history, if it exists, is likely UI/report-level (not read). A product relying on history must snapshot configuration over time itself.

### Gaps
- UI-level "setup audit" or report in Pro WFM: not found; library.ukg.com search returned nothing relevant.

## 4. Documented configuration relationships

### Takeaway
PARTLY CONFIRMED with a primary quote. UKG documents employment term as the grouping that references pay rule, accrual profile, cascading profile, holiday profile, time-off rule and work-hour pay codes, and it documents FAP/GDAP assignment to people. Pay rule to work rule, work rule to paycode/overtime/zones, and paycode to payroll mapping were not re-verified here (earlier snippets only).

### Cited Findings
- [PRIMARY-READ] "Employment terms are used to group employees who share a number of pay policies, including pay rule, accrual profile, cascading profile, holiday profile, and timeoff rule. The group can also use the same work hour definition, pay codes, and minimum wage." — [Employment Term Assignments](https://developer.ukg.com/wfm/docs/employment-term-assignments-doc)
- [PRIMARY-READ] Sample `GET /v1/timekeeping/setup/employment_terms` response shows each `employmentTermVersion` with nested `accrualProfile`, `holidayProfile`, `payRule` (each with id, qualifier, name), `startDate`/`endDate`, and `workHours.workHourDef[].payCode`. Versions are effective-dated. — same page
- [PRIMARY-READ] Access: "Function Access Profiles (FAPs) contain permissions to points in the hierarchy of functions, known as access control points (ACPs)". Person fields include `gdapAssignments > gdapName`: "Generic Data Access Profiles — (Managers) Divides configured pay rules and accruals data among different business units or locations within your organization." Also person-level "Process Profile" and "Delegate Profile". Persons also carry licenses. — [Configure access for a person](https://developer.ukg.com/wfm/docs/configure-access-for-a-person-doc)
- [PRIMARY-READ] Resource groups "Work Rule Data Access Profiles" and "Paycode Data Access Profiles" (e.g. "Add Paycodes to or Remove Paycodes from Paycode Data Access Profiles", "Add Paycodes to or Remove Paycodes from Combined Paycodes") show GDAP-type objects reference paycodes/work rules. — [API reference](https://developer.ukg.com/wfm/reference)
- [SNIPPET, earlier notes] Work rules combine building blocks applying pay rules; paycodes map to payroll via Payroll Code Mapping — still snippet-level; see earlier note [ukg_pro_wfm_architecture.md](ukg_pro_wfm_architecture.md).

### Inferences
- [INFER] The earlier "employment terms → (pay rule, work rule profile, accrual profile)" chain is corrected: the primary quote lists pay rule, accrual profile, cascading, holiday and time-off rule on the employment term; "work rule profile" appears in the earlier help snippet under the employee Timekeeping template, not on the employment term per the page above.

### Gaps
- Pay rule to work rule, work rule to overtime/zones, paycode to payroll mapping, dependency of paycodes on pay rules: not verified from a primary page here.

## 5. Workforce Central end of life

### Takeaway
UNVERIFIED from UKG primary pages (www.ukg.com is behind a Cloudflare challenge, 403). Dates in earlier notes remain consistent across several secondary and search-summary sources, so keep them labelled "partner/secondary".

### Cited Findings
- [FAIL] https://www.ukg.com/wfc-support-policies-and-services and https://www.ukg.com/for-llms/wfc-support-policies-and-services both returned HTTP 403, body "Just a moment... Enable JavaScript and cookies to continue".
- [SNIPPET of UKG-site search result, not read] Search summary: "WFC customers on the Kronos Private Cloud (KPC) will have support until December 31, 2025"; "WFC customers that host on-premises will have support through March 31, 2027"; RSM lists on-premise end of engineering 12/31/25. Announcement October 20, 2022; named path UKG Pro WFM (formerly Dimensions). UKG customer emails (preview.web.ukg.com) confirm KPC end of life December 2025 and an HRMS end of life of April 30, 2024 (not read). — [UKG support policies](https://www.ukg.com/wfc-support-policies-and-services); [RSM](https://technologyblog.rsmus.com/uncategorized/ukg-workforce-central-support-is-ending-do-you-have-a-plan); [Healthcare IT Leaders](https://healthcareitleaders.com/blog/ukg-workforce-central-wfc-end-of-life)
- [3P/UKG datasheet, not read] "UKG Pro WFM Migration Assessment" datasheet exists — [PDF](https://www.ukg.com/sites/default/files/2023-09/SV0252-USv4-UKG%20Pro%20WFM-Migration-Assessment-ds.pdf). Not fetched this round (www.ukg.com blocked).

### Inferences
- [INFER] As of 2026-11-18, KPC support has ended (2025-12-31) and on-prem support ends 2027-03-31, about 4.5 months out, assuming no UKG extension (none found).

### Gaps
- Official UKG wording of dates, any extension, and the named migration tool/offering beyond the Migration Assessment datasheet: unverified. Needs www.ukg.com access (browser-like fetch) or a customer-supplied copy.

## 6. PyMuPDF licensing

### Takeaway
CONFIRMED from primary sources. PyMuPDF is dual-licensed AGPL v3 or Artifex commercial; Artifex states server-based use requires AGPL source disclosure or a commercial licence. Pricing is not published ("Contact Sales").

### Cited Findings
- [PRIMARY-READ] "Most of our products are dual-licensed under open source with the GNU AGPLv3 license ... or with commercial license agreements." — [Artifex licensing](https://artifex.com/licensing)
- [PRIMARY-READ] "You cannot deploy our open-source as part of a server-based application or service, without disclosing your own application's full source code under AGPL to any users interacting with it." Also: "Usage of our open-source Community Edition must be limited to AGPL-compliant environments" and "Any modifications to our open-source must be disclosed under the AGPL, including sharing the modified code with any users interacting with it." — same page
- [PRIMARY-READ] "Can't Comply with AGPLv3? If you can't meet the requirements of the GNU AGPLv3 above, a commercial license is required." "Our commercial license offers flexible options, whether you're deploying our product as a SaaS, integrating it as OEM software, or using it in-house with full technical support." — same page
- [PRIMARY-READ] Models: AGPL "Free License ... Full source code disclosure (including your app code)"; OEM Distribution and Subscription licences: "Per-copy cost with a quarterly minimum fee", "Annual reporting on volume of distribution (No report needed for internal usage)"; "Each Artifex commercial license is crafted based on your individual use case." No price figures; "Contact Sales". — same page
- [PRIMARY-READ] "PyMuPDF and MuPDF are now available under both, open-source AGPL and commercial license agreements ... If you determine you cannot meet the requirements of the AGPL, please contact Artifex ... Artifex is the exclusive commercial licensing agent for MuPDF." — [PyMuPDF docs, License and Copyright](https://pymupdf.readthedocs.io/en/latest/about.html)

### Inferences
- [INFER] A closed-source network-served product using PyMuPDF needs a commercial licence (or AGPL compliance incl. publishing app source to users). Internal-only use is not addressed beyond the "internal usage" reporting remark; this is not legal advice.

### Gaps
- Price figures: not published on pages read.

## Summary: earlier claims vs verified

- Auth flows incl. Client Credentials, Developer Console, 429 guidance: CONFIRMED with correction that client creation is in Administration > Application Setup > Common Setup > Client Management (Pro WFM) and Developer Console where UKG Authentication is enabled.
- "Config endpoints not verified": REFUTED as a gap. Documented v2/v1 setup GET paths exist (section 1).
- Numeric rate limits: still none published; per-request caps exist.
- SDM file format / compare output / constraints: still unverified.
- Setup audit trail: no documentation found.
- WFC dates: still secondary only.
- PyMuPDF: CONFIRMED primary; pricing not public.
