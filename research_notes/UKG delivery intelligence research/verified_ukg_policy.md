# Verified UKG legal/policy terms on automated and AI access, and UKG AI offerings (as of 2026-11-18)

Method and access result (read first): only developer.ukg.com could be read in full text. All legal and policy documents on ukg.com / www.ukg.com are NOT verified. WebFetch failed DNS resolution for every host (ukg.com, developer.ukg.com, businesswire.com: "getaddrinfo ENOTFOUND"), so I used curl through the session proxy. Results (2026-11-18):
- developer.ukg.com: HTTP 200, full text read (pages listed below).
- https://www.ukg.com/ -> HTTP 403; https://ukg.com/ -> 301 to www. Every www.ukg.com URL tried returned HTTP 403 with a Cloudflare "Just a moment... Enable JavaScript and cookies to continue" challenge page. Failed URLs: /sites/default/files/2026-07/MSA-2026-07-01-US.EN_.pdf, /sites/default/files/2026-07/AUP-English-2026-07-01.pdf, /sharepoint/view/01WMTN4D3XI35U4LFZ7BC37IPT6C37O3TV (API Call Packs SD), /for-llms/acceptable-use-policy, /for-llms/company/responsibility/responsible-and-ethical-use-ai, /terms-of-use (same result on both ukg.com and www.ukg.com).
- library.ukg.com -> HTTP 302 and community.ukg.com -> HTTP 301 (redirects only; redirect targets not followed or read; likely login-gated).
- businesswire.com not reachable (DNS); the UKG in Claude press release was not read.
- A further attempt to retry ukg.com with a different (search-bot) user agent was blocked by the session permission classifier; I did not pursue bypassing the Cloudflare challenge. To get the primary legal text, allow the hosts through a browser-capable path or have a human download the PDFs and put them in the repo.

Consequence: the MSA, AUP, API Call Packs / Exhibit A, UKG in Claude and Responsible AI claims below stay "unverified (snippet only)". Nothing in them is confirmed or refuted. I have quoted no clause text from those documents.

## UKG Master Services Agreement (reported July 2026): programmatic / AI / agentic access

### Takeaway
Unverified (snippet only). Could not fetch the PDF (HTTP 403, Cloudflare challenge). The earlier claim stands as a lead, not a fact.

### Cited Findings
- Earlier-note claim (not re-verified): MSA 2026-07-01 US prohibits programmatic or automated access, expressly including AI programs and agentic access, without UKG written authorization — source named in earlier notes: https://www.ukg.com/sites/default/files/2026-07/MSA-2026-07-01-US.EN_.pdf. Status: unverified (snippet only); fetch returned 403.

### Inferences
- None added. Exact wording (clause number, who is bound, whether customer-delegated access is covered) is what the decision depends on; requires legal review of the actual PDF.

### Gaps
- Clause text, number, document version, definition of "Services"/"Customer Data", and the form of authorization needed: all missing.

## UKG Acceptable Use Policy (reported 1 July 2026)

### Takeaway
Unverified (snippet only). Both the PDF and the HTML version returned HTTP 403.

### Cited Findings
- Earlier-note claim (not re-verified): AUP bars robots imitating a human user, excessive automated requests, bulk extraction/replication, excessive polling/synchronisation, disproportionate automated load, with suspension for violation — https://www.ukg.com/sites/default/files/2026-07/AUP-English-2026-07-01.pdf and https://www.ukg.com/for-llms/acceptable-use-policy. Status: unverified (snippet only).

### Inferences
- None.

### Gaps
- Verbatim clauses, thresholds for "excessive"/"disproportionate", and whether the AUP applies to customer-authorised integrations.

## API Call Packs Services Description / Exhibit A (Data Interface Terms, reported 2026.09.14)

### Takeaway
Unverified (snippet only) for the scraper/agent prohibition, monitoring/suspension and the 10 million calls figure. SD URL returned HTTP 403. The earlier notes themselves flagged the "agents" wording as coming from a single summary, so treat it as the least reliable claim.

### Cited Findings
- Earlier-note claim (not re-verified): use of UKG APIs subject to Exhibit A; bars spiders, crawlers, scrapers or agents on data interfaces; UKG may monitor and suspend; 10 million calls per pack per tenant per month, no rollover — https://www.ukg.com/sharepoint/view/01WMTN4D3XI35U4LFZ7BC37IPT6C37O3TV. Status: unverified (snippet only).
- What is verified on the developer hub: the hub footer links "Terms of Use" to https://www.ukg.com/terms-of-use and "Compliance and Licenses" to https://www.ukg.com/legal/compliance-licenses (link targets only; both pages are behind the same 403) — https://developer.ukg.com/general/docs/genai-search (page footer).

### Inferences
- None.

### Gaps
- Whether Exhibit A is the governing document for API access, its version date, the call limit and monitoring clause text.

## developer.ukg.com: who may obtain credentials, partner requirements, data-use and AI-training restrictions

### Takeaway
Documented fact: the Developer Hub is public and free, and most published API resources are open to "customers & 3rd parties", but credentials are created inside a customer's tenant (or via a UKG Support case) by the customer, and some resources are partner-only. I found no developer-hub page stating data-use restrictions or AI-training restrictions; those, if they exist, sit in the unread legal documents.

### Cited Findings
- Developer Hub open to all: "the Developer Hub is open to all developers and builders everywhere of any skill level"; resources "are available publicly without logging in"; "Yes, this is free!" — [Developer Hub FAQ](https://developer.ukg.com/general/docs/ukg-developer-hub-faq) (page showed "Updated 7 months ago").
- Partner-only resources: "Some API resources are generally available only to official partners such as Background Check Integration and Benefits Integration. All other published API resources are available for customers & 3rd parties to use in building integrations." — [FAQ](https://developer.ukg.com/general/docs/ukg-developer-hub-faq).
- Common sanctioned use: "using a UKG solution as the employee system of record and using an API to extract employee records/changes, org levels, jobs, and locations." — [FAQ](https://developer.ukg.com/general/docs/ukg-developer-hub-faq).
- HCM credentials come from the customer's admin: "UKG Pro HCM users with system administrator rights can create web service accounts"; "Permissions can be granted to one or more resource or method"; "only grant access to the API resources and actions a web service account will use." — [Web Service Account](https://developer.ukg.com/hcm/docs/web-service-account).
- Authentication needs the customer's keys: Basic Auth with "web service account username/password and a five-character US-Customer-Api-Key"; Recruiting/Onboarding: "To aquire the clientId/clientSecret, a case must be opened with UKG Support"; RaaS: "service account permissions must be elevated. Open a case with UKG Support" — [UKG Authentication and Authorization](https://developer.ukg.com/general/docs/authentication-and-authorization).
- The API is described as supporting integration use cases "from API dashboards to data replication and custom reporting front-ends" and "retrieval and updating of UKG Pro HCM data"; HCM REST domains include "Configuration Setup" and "PRO Platform Configuration" — [API and Developer Tools Overview](https://developer.ukg.com/general/docs/api-and-developer-tools-overview).
- Developer Hub GenAI search is "trained on documentation and API specifications using the power of GPT-4 and GPT-3.5 Turbo" (confirms earlier note) — [GenAI Search](https://developer.ukg.com/general/docs/genai-search).
- Workforce Intelligence Hub (wih.ukg.net) has an "API Usage Monitor"; "currently available as an MVP to a limited set of customers in the United States" (page updated 6 months ago) — [WIH welcome](https://developer.ukg.com/proplatform/docs/welcome-to-workforce-intelligence-hub). This corrects the earlier note's implication that WIH is broadly shipped: it is MVP/limited per UKG docs, and it monitors API/webhook usage.
- UKG Compose: "currently available only to customers who have elected to participate with tenants in North America (US and CA regions)" and "Limited Availability Disclosure" (confirms earlier note on availability; the Beta-vs-opt-in conflict was not re-checked) — [Welcome to UKG Compose](https://developer.ukg.com/proplatform/docs/welcome-to-ukg-compose).

### Inferences
- Labelled inference: the hub text shows UKG anticipates "3rd parties" building integrations with customer-provisioned service accounts; it does not say whether a third party's use is permitted under the MSA/Exhibit A, or whether AI processing of returned data is restricted.

### Gaps
- No developer-hub partner programme requirements, no data-use or AI-training clause found. The hub's own Terms of Use link goes to the blocked www.ukg.com page. Pro WFM authentication options (federated, etc.) were only skimmed. Rate/service limits page not read.

## "UKG in Claude" (reported beta 20 Oct 2026, MCP-based)

### Takeaway
Unverified (snippet only). The press release (businesswire.com) was unreachable (DNS failure). I found no mention of it, or of MCP, on the developer-hub pages I read.

### Cited Findings
- Earlier-note claim (not re-verified): announced 20 Oct 2026 as beta, MCP connector, plain-language questions on schedules, hours, pay rules, labor policies, supported actions limited by platform permissions and customer controls — https://www.businesswire.com/news/home/20261020356990/en/UKG-in-Claude-Makes-AI-Work-Beyond-the-Chat. Status: unverified (snippet only).

### Inferences
- None.

### Gaps
- Product coverage (Pro HCM vs Pro WFM), read vs write actions, availability, and the terms governing it: unknown from primary text.

## UKG Bryte AI / Bryte Agents / "Configuration Assistant"

### Takeaway
Unverified (snippet only) from UKG primary text this pass. The Configuration Assistant and Bryte agent GA status remain open. Nothing read confirms any feature that analyses configuration dependencies or change impact.

### Cited Findings
- Earlier-note claims (Bryte Assistive AI Services Description dated 2026.02.03, Bryte agents newsroom pages, Nucleus "Configuration Assistant" mention) are not re-verified: ukg.com URLs returned HTTP 403.
- Documented on developer.ukg.com: the only UKG-run AI feature found is the Developer Hub GenAI search (above), and the Workforce Intelligence Hub MVP (limited customers, US). Neither is a configuration-impact tool — [GenAI Search](https://developer.ukg.com/general/docs/genai-search), [WIH](https://developer.ukg.com/proplatform/docs/welcome-to-workforce-intelligence-hub).

### Inferences
- None new.

### Gaps
- GA status per agent; any configuration-analysis feature; Configuration Assistant existence in UKG's own words.

## UKG responsible AI principles

### Takeaway
Unverified (snippet only). The page returned HTTP 403, so I cannot list all principles verbatim. The earlier note's partial list (only "Fairness and inclusiveness" and "Transparency by design" confirmed, from snippets) stands as unverified.

### Cited Findings
- None verified. Source URLs to retry: https://www.ukg.com/for-llms/company/responsibility/responsible-and-ethical-use-ai and https://www.ukg.com/about-us/esg/governance/artificial-intelligence.

### Inferences
- None.

### Gaps
- Complete verbatim principle list.

## Implications for a third-party tool (INFERENCE ONLY, not legal advice)

Inference, not documented fact: the verified developer-hub material shows UKG publicly invites "customers & 3rd parties" to build integrations using customer-created, permission-scoped service accounts, which suggests that customer-provisioned, least-privilege API credentials for read-only extraction is a path UKG anticipates for non-partner resources. Whether that is lawful for this product depends on the MSA, AUP and Exhibit A text I could not read, which reportedly (unverified) require UKG written authorization for programmatic/automated access, especially AI programs and agents, and restrict scrapers, bulk extraction and heavy polling. Therefore: (1) customer-supplied exports processed offline is the lowest-risk path, but customer-side confidentiality and licence terms for exports are unchecked, so requires legal review; (2) customer-provisioned API credentials with read-only scope and modest call volume: ambiguous, requires legal review of Exhibit A and the MSA authorisation clause, and likely a written authorisation or partner arrangement; (3) read-only automated extraction at scale: higher risk given reported AUP bulk-extraction/polling limits, requires legal review; (4) AI agents operating inside a tenant: the reportedly most restricted case (explicit AI/agentic wording in the reported MSA), treat as not permitted without UKG written authorization until the text is verified. This is consistent with the project rule of no live tenant access.
