# Decision 0006: What the database proves about who reviewed

Status: **accepted by the owner for Milestone 1, 2026-11-22 (4); session-bound reviewers are a G-REAL requirement.** Residual risk recorded during Slice 5. No code change is made now.

## Context

Slice 5 makes the database refuse any accept, reject, supersede or reinstate event, and any lineage declaration, whose actor is not a human (for review events, a human with the `reviewer` role). Three layers enforce it: role privileges, constraint triggers, and the API, which takes the actor from a server-side credential and never from a request body.

## Residual risk

The database enforces "the event is attributed to a human reviewer". It does **not** enforce "this database session belongs to that human". Any login that is a member of `wb_review` can insert an event naming **any** human reviewer actor as `actor_id`. The API closes this for requests that come through it (the actor comes from the configured credential), but a holder of a `wb_review` database login, or a bug that lets a request choose the actor, is not stopped by the database.

This is weaker than the relationship model's wording ("authenticated human session; no service tokens") in one respect: the milestone 1 reviewer identity is a static bearer token mapped to one configured actor (owner question S5-Q2, still pending). A token held by a script can act as that human. The database cannot tell.

## Decision (proposed)

1. Accept this limit for Milestone 1: synthetic data only, one local reviewer, `wb_review` logins held by the developer and the API process only.
2. Treat these as the upgrade, to be done **before gate G-REAL** (real data):
   - one database login per human reviewer, and a trigger that requires `actor.login = session_user` for review events and lineage declarations (the `actor` table gains an immutable `login` column);
   - no shared `wb_review` credential; the API connects as a role that cannot insert review events and calls a narrow function that binds the actor to the authenticated session;
   - an audit of who holds `wb_review` membership.
3. Until then, never describe the review trail as proof that a particular person pressed the button. It proves the named actor is a human reviewer, and that no service actor or ingestion path can write a verdict.

## Consequences

Cheap to build later: actors are immutable rows, so a `login` column is a new column on a new actor row, and the existing triggers already run on every insert.
