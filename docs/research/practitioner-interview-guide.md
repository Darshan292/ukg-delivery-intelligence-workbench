# Practitioner Interview Guide

Status: draft for user approval. Thresholds in section 9 are proposed, not agreed.
Source: `docs/research/research-report.md` (sections 2, 12, 13, "Direct answers").

## 1. Purpose

The research found no practitioner evidence that engineers spend meaningful time cross-referencing artefacts by hand on UKG projects. "Reconciliation must happen somewhere" is an inference, not a finding. These interviews test that claim and can disprove it. Practitioner validation is P0, in parallel with Milestone 1.

We are not selling, demoing or collecting opinions about a product. We are collecting accounts of what people actually did.

## 2. Hypotheses: what supports and what refutes

| # | Hypothesis | Supported by | Refuted by |
|---|---|---|---|
| H1 | Manual cross-artefact reconciliation (requirements, workbooks, exports, mappings, tests, defects) is frequent and costly | Described recent episodes with concrete steps; hours or days they can justify ("two days before UAT, comparing X to Y"); repeated across projects | They cannot recall an episode; reconciliation is a small, quick part of the job; existing tools or habits make it trivial; effort is spent on other work (config, testing, stakeholder time) |
| H2 | Configuration-change errors with downstream consequences happen, and trace to missing links between artefacts | A specific incident where a change broke something elsewhere (pay, integration, report, test), found late, and the cause was an unknown dependency or unlinked requirement | Incidents are rare, or caused by something else (unwritten rules, bad requirements, UKG defects, data entry), or caught early by existing process |
| H3 | Current alternatives are inadequate | Workarounds that are fragile, personal or late (private spreadsheets, memory); named tools (Setup Data Manager compare, Opkey, TestAssure, ServiceNow, Jira) that were tried and fell short for a stated reason | Current alternatives work well enough; they are satisfied; no one is asking for better |
| H4 | Practitioners can and will share sanitised artefacts | Someone says what they could share, who approves it, and goes on to start that approval; a contract path exists | Consistent refusal, no clear approver, MSA or customer terms forbid it, sanitising costs more than they will spend |
| H5 | Someone has buying authority and budget | A named role that decides; a budget line or precedent for tools; a described past purchase; willingness to introduce us to that person | Nobody owns the problem; tools cannot be bought on their project model; any purchase would need a long procurement path with no sponsor |

Unwritten rules matter. The report notes that a traceability tool cannot trace a requirement that was never written down (Fayetteville audit example). Probe for this under H2 and record it as evidence against the core value if it dominates.

## 3. Sample plan

Target 8 to 12 interviews. Stop at 12 unless a segment is still ambiguous. Minimum 2 per segment.

| Segment | Min | Aim for |
|---|---|---|
| UKG implementation consultants | 2 | Partner/SI and UKG-employed; fixed-fee and T&M projects |
| WFM support engineers | 2 | Managed-service and in-house; release validation owners |
| UKG administrators (customer side) | 2 | Different industries and sizes; owners of change control |
| Migration and integration consultants | 2 | WFC to Pro WFM migrations; integration mapping work |

Spread across: partner/SI and customer side (at least 3 of each overall); Pro WFM and Workforce Central experience (treat as separate profiles, record which; at least 2 with WFC experience); seniority (at least 2 senior/lead and 2 hands-on practitioners).

Note WFC support ends 31 March 2027 per the report, so WFC and migration voices may be hard to get later.

### Recruitment channels
- Personal and professional networks (second-degree introductions).
- LinkedIn outreach and UKG user-group or community events, using a neutral request ("research on how teams manage UKG configuration changes").
- Referrals from earlier interviewees (ask at the end; this is also a signal, see section 7).
- Do not use customer lists or any data obtained through client work.

### Screening questions
1. In the last 12 months, did you work directly on UKG Pro WFM or Workforce Central configuration, testing, integrations or migration? Which?
2. Which role: consultant (partner/UKG), support engineer, customer administrator, migration/integration?
3. How many go-lives, releases or migrations have you been part of in that time?
4. Employer type: partner/SI, UKG, or customer? Roughly how large?
5. Are you free to talk about your own work in general terms, without customer names or data?
Exclude anyone who cannot recall recent hands-on work.

### Conflicts of interest
- Colleagues at the same firm as the team, or current clients: answers will be softened or inflated. Exclude them, or flag and count them separately. At most 2 such interviews.
- UKG employees: may be bound by confidentiality; do not ask for UKG internal information.
- Friends and people who want to help: expect politeness. Weight only behaviour.
- Anyone who may later be a customer or employer: record the relationship in the notes.
- Offering payment or gifts changes answers; keep any thank-you token small, identical across interviewees, and disclosed.

## 4. Method

- Length 45 to 60 minutes. Video call. One interviewer and one note-taker if possible.
- Anchor in the past: "Tell me about the last time you...". Ask for the specific episode, the people, the artefacts, the steps and the elapsed time.
- Do not describe the product, a solution or a feature until the optional final section. Do not name the product category in the invitation.
- No leading questions. Not "Wouldn't it help to...?" but "How did you do that?"
- No hypotheticals ("would you", "if we built"). If the interviewee offers a hypothetical, bring it back: "When did that last happen?"
- Ask "how do you know?" for every number. Ask "who else was involved?" and "what happened next?"
- Silence is fine. Do not fill it with suggestions.
- Pitching and fishing for compliments are the main risks. If you catch yourself pitching, stop.

### Consent script (read before starting)
> Thanks for your time. This is research into how teams manage UKG configuration changes and testing. I am not selling anything.
> I would like to record the call and take notes, for my own analysis only. Is that OK? You can ask me to stop recording at any time, or skip any question.
> Please do not share any customer-confidential information, customer names, employee data, pay data or configuration values. Talk in general terms ("a retail customer", "a pay rule"). If you start to say something sensitive, I will stop you.
> Your name and employer will not appear in any write-up. I will use a code such as P07 and a role description. Quotes will be edited to remove identifying details. You can withdraw your answers within [X] days of today.
> Do you agree to take part and to the recording?

Record the verbal consent. If they decline recording, take notes only. Store recordings and notes in a restricted location; delete recordings after transcription or notes are complete, on a date set before the first interview.

## 5. Interview flow and question bank

Timings are guides. Sections A to E are core. F to H are shorter. I is optional.

### A. Role context (5 min)
1. What is your role, and which UKG products and versions have you worked on?
2. What did you work on in the last month? Walk me through a typical week.
3. How many projects or customers at once? Fixed-fee, T&M or in-house?

### B. Actual workflows (15 min; pick the 2 or 3 most relevant to the role)
- Last configuration change: "Tell me about the last configuration change you made after go-live (or during build). What triggered it? How did you decide what it affected? What did you check? How long did that take? Who signed it off?"
- Last release validation: "Tell me about the last UKG release you had to validate. How did you decide what to test? Where did the list come from? What did you miss, or nearly miss?"
- Last integration mapping issue: "Tell me about the last time an integration (payroll, HR, ERP) produced wrong or missing data. How did you find the cause? Which documents did you open?"
- Last migration validation: "Tell me about the last time you checked that something configured in the old system was correctly rebuilt in the new one. How did you decide it matched?"

### C. Current alternatives (8 min)
1. What do you use today for that? Walk me through the tools open on your screen.
2. Have you used Setup Data Manager compare, Configuration Assistant, Opkey, TestAssure, ServiceNow, Jira, Excel macros or scripts? What did you use each for? Where did it stop?
3. What happens when the one person who knows the dependencies is away?
4. Have you tried to improve this before? What did you try, and what happened? (Past effort is a stronger signal than complaint.)

### D. Time spent (6 min)
1. For the episode you described, how much time went on finding out what was affected, comparing documents, and updating them to match?
2. How do you know? Timesheet, ticket, memory, a guess?
3. How often does this happen? When did it last happen before that?
4. What did that time displace?

### E. Error consequences (6 min)
1. Tell me about the last incident where a configuration change had a downstream effect nobody expected.
2. How was it found, and how long after the change? Who found it?
3. Who was affected (employees, payroll, managers, a customer)? What was the cost: rework, hours, money, penalty, trust? How do you know?
4. What was the root cause? Missing documentation, unwritten rule, no test, not understood dependency, UKG behaviour?
5. What changed afterwards?

### F. Artefacts (5 min)
1. What documents or exports exist on a project: requirements, design workbooks, configuration exports, mapping specs, test scripts, defect logs?
2. What format and where are they kept? Who maintains them? Are they current?
3. Do items carry explicit IDs and cross-references (requirement ID in a test, ID in a mapping row), or are links by name, position or memory?
4. Show me, in words, how one requirement is traced to its configuration and its test. (Do not ask for the file.)

### G. Willingness and ability to share sanitised artefacts (4 min)
Ask only about the process, never request files in the interview.
1. Have you ever shared a project document with someone outside the customer or firm? What was the process?
2. Who would need to approve it? How long would that take?
3. What do your customer agreements or UKG terms say about sharing configuration or exports? Do you know, or would someone else?
4. What would need to be removed or changed before you would be comfortable? Who would do that?
5. Is there a template or training artefact that is not customer-specific?

### H. Buying authority (5 min)
1. When your team last bought or adopted a tool, who decided? Who paid? Which budget line?
2. On fixed-fee projects, how do tool costs fit? On T&M, can a tool that saves hours be bought, or does it reduce billable work?
3. What would make you or your organisation pay for something here? What have you refused to pay for?
4. Who else would need to agree? Would you be willing to introduce me to them?

### I. Optional concept reaction (5 min, only if time remains and sections A to H are complete)
Briefly describe the idea in two sentences, neutral wording. Ask: "What is wrong with it? What would stop you using it? What would you need to see before you could trust it?" Record separately as opinion only; it does not count toward any threshold.

### Segment variants
- Implementation consultants: ask about design-to-build handover, UAT preparation, who writes the traceability matrix, fixed-fee margin effect.
- Support engineers: ask about change requests, post-release regression, ticket-to-configuration linkage, on-call "what does this touch" questions.
- Customer administrators: ask about change control, audit and compliance evidence, who validates after UKG releases, reliance on the partner.
- Migration and integration consultants: ask about mapping specs, rebuilt integrations, parallel testing, how "done" is proven, and the March 2027 deadline's effect.

## 6. Evidence rules

Positive opinions ("that would be useful", "I'd use that", "great idea") are not evidence of demand. Record them, mark them as opinion, and do not count them toward any hypothesis.

Count only past behaviour and commitments.

| Level | Signal | Example |
|---|---|---|
| 0 | Nothing, or contradicts the hypothesis | "That does not really happen to us" |
| 1 | Opinion | "That sounds useful" |
| 2 | Described past episode | Specific recent event with steps and people |
| 3 | Quantified episode | Hours, frequency or cost, with a stated basis |
| 4 | Artefact shared or offered via the approval gate | Sanitised sample, or a named person who can approve it |
| 5 | Introduction to a buyer or budget holder | Actual introduction made |
| 6 | Paid pilot or signed LOI | Money or written commitment |

Level 4 or above for artefacts only counts if it goes through the gate in section 10. Rate each hypothesis per interview at its highest level reached, and always record the level 0 cases.

## 7. Notes template (one per interview)

```
Interview ID: P__   Date:   Interviewer:   Note-taker:
Segment:   Employer type (partner/SI, UKG, customer):   Seniority:
Pro WFM / WFC experience:   Project model (fixed-fee / T&M / in-house):
Relationship to us (conflict flag):   Consent given (record/notes):

Episodes described (one block each):
  Type (config change / release / integration / migration):
  When:   What triggered it:   Steps and artefacts used:
  Time taken (and basis):   People involved:
  Outcome / error / consequence:   Cost (and basis):
  Verbatim quote:

Alternatives used (tools, spreadsheets, tribal knowledge) and gaps stated:
Artefacts that exist (type, format, IDs/cross-refs yes/no/partial):
Sharing: approver / contractual barrier / sanitisation needed:
Buying: decision maker / budget line / purchase model:
Commitments made (intros, files, follow-ups, with dates):
Opinions (flagged as opinion only):

Signal level per hypothesis (0-6):  H1 _  H2 _  H3 _  H4 _  H5 _
Disconfirming evidence (required, write "none heard" only if probed):
Surprises / things I did not expect:
Interviewer bias check (did I lead, pitch or fill silences?):
```

## 8. Synthesis method

1. Complete notes within 24 hours of each interview. A second person reviews the signal levels for at least the first 3 interviews.
2. Build a table: one row per interview, one column per hypothesis, cell is the highest signal level, with a pointer to the episode.
3. Tally per hypothesis: number of interviews at level 2 or above, level 3 or above, level 4 or above, level 5 or above. Report counts per segment as well as in total. Do not average across levels.
4. Pull quotes only with their episode (what happened, when, role). A quote without an episode is an opinion.
5. The disconfirming evidence section is mandatory. For each hypothesis list every interview that refuted or weakened it, in equal prominence to the support. Also list alternative explanations (unwritten rules, existing tools, UKG-side fixes).
6. Look for patterns by segment, product (Pro WFM vs WFC), employer side and project model. With 8 to 12 interviews these are directional only; state sample sizes, give no percentages beyond the raw counts, and make no claims about the market.
7. Record what would change our mind and what we still do not know.

## 9. Decision criteria (proposed thresholds, for the user to approve)

These are proposed judgement thresholds, not evidence-derived. The report's own criterion (acceptance criterion 10) is that fewer than 3 of 5 practitioners recognising the problem means revisit the thesis. For 8 to 12 interviews the same ratio is applied, and "recognise" means a described past episode (level 2 or above), not agreement with a description.

Interim check after the first 5 interviews: if fewer than 3 gave a level 2 or above H1 episode, pause and revisit the thesis and sampling before continuing.

After the full round (N = completed interviews):

| Outcome | Proposed condition |
|---|---|
| Proceed | At least 60% of interviews (e.g. 5 of 8, 6 of 10, 7 of 12) gave an H1 episode at level 2 or above, AND at least 3 interviews gave level 3 or above on H1 or H2, AND H2 is seen in at least 2 segments, AND at least 2 interviewees reached level 4 on H4 through the approval gate, or one reached level 5 on H5 |
| Pivot or narrow | The problem is recognised (above 40% at level 2 or above) but one of the conditions above fails. Examples: only one segment recognises it; pain is real but the main cause is unwritten rules, not missing links; no one can share artefacts; no buyer. Refine the thesis to that segment or cause and run a smaller second round |
| Stop or park | Below 40% at level 2 or above; or most episodes show existing tools or habits work; or no buyer or sharer in any segment. Keep Milestone 1 as a technical demo, do not extend scope, and report that the hypothesis was not supported |

An unfavourable result is a valid result. Do not recruit additional interviewees only to reach the proceed threshold.

## 10. Ethics, compliance and approval gates

- Do not request or accept real employee data, pay data or customer configuration during interviews. If offered, decline, and do not record it. If something sensitive slips into notes or a recording, delete it.
- Do not ask interviewees to breach their customer agreements or employer policy. Do not ask for UKG-confidential material.
- Interviewees are not asked to share files. Any later artefact sharing is a separate step after the interview and goes through an approval gate.
- Milestone 1 is synthetic data only. No real artefact enters the repository or any tool.
- A future real-artefact gate requires all of: the customer's written consent; sanitisation agreed and checked; the sharer's employer approval where relevant; and legal clarification of the UKG Developer Policy and the customer MSA. Open policy questions are in `docs/research/notes/verified_ukg_developer_policy.md`. They include whether configuration exports are Customer Data, how "Developer" and "Competitive Product or Service" apply, the cross-tenant aggregation clause, and the ban on using Customer Data to evaluate AI models without written consent. That note is not legal advice and does not settle the offline-file case.
- Store interview material separately from the code repository. Keep identifying details out of synthesis documents.
- Do not use Workday, Boomi, ServiceNow or UKG tenant access to prepare for or follow up on interviews.

## 11. Before the first interview

- User approves this guide, the thresholds in section 9, and the consent wording (add withdrawal window, retention date and storage location).
- Decide who interviews. Prefer someone who has no sales stake in the outcome.
- Pilot the guide once on a friendly contact, outside the sample, and cut questions that lead or confuse.
