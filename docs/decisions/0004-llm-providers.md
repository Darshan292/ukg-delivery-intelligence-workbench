# Decision 0004: LLM providers

Status: **approved by the owner, 2026-11-22.** Recorded now and built in Milestone 2. Milestone 1 uses no LLM.

## Context

Engineering rule 2: AI is for extraction, explanations and suggestions, never the authority for configuration relationships. Rule 10 and the UKG Developer Policy notes forbid sending real customer data to an LLM or host without written authorisation. The product must work fully without any LLM, and contributors must be able to test with no paid service.

## Decision

1. **One provider interface** over the OpenAI-compatible chat API. It uses the official **`openai` Python SDK** (Apache-2.0; checked on PyPI 2026-11-22, version 3.57.0) with a configurable `base_url`. **No LiteLLM.**
2. **Providers:**
   - `none`: the default. Every feature works without an LLM; LLM-only features say they are off.
   - `ollama`: local and offline, through Ollama's OpenAI-compatible endpoint.
   - `groq`: hosted with a free tier, for testing only.
3. **Configuration** (environment variables, typed settings):
   - `LLM_PROVIDER`: one of `none`, `ollama`, `groq`.
   - `LLM_BASE_URL`: the provider endpoint.
   - `LLM_MODEL`: the model name. It is never hard-coded.
   - `GROQ_API_KEY`: a secret (`SecretStr`), never logged, never echoed in errors, never committed.
   At startup the configured model is checked against the provider's `/models` list. If it is missing, startup fails with a clear message naming the provider and the model setting, never the key.
4. **Data guard (enforced in code, with a test):** the `groq` provider is refused unless **every** `Document` in the project has `product_profile == "synthetic"`. The check runs before every request, not only at startup, so adding a non-synthetic document later blocks the next call. `ollama` stays local; real-data use of any provider still waits for gate G-REAL and sub-processor authorisation (D2, D9).
5. **Output validation:** every response is parsed and validated against our Pydantic schema. Strict structured output (JSON schema with strict mode) is used where the provider and model support it. Otherwise JSON mode is used, with the same validation; which models support strict mode is checked when this is built. Invalid output is dropped and logged without the content.
6. **Authority:** LLM output enters only as claims with basis `llm_suggestion` and review state `unreviewed`, carrying model name, prompt version and confidence. It is never accepted automatically; only a human can accept or reject (D3, enforced in the database from Slice 5).
7. **Tests never call Groq.** Unit and integration tests use a recorded fake: a stub transport replaying stored responses. An optional smoke test is triggered manually (`workflow_dispatch`) and runs against Groq only when `GROQ_API_KEY` is set as a repository secret, on synthetic data only.

## Consequences

- One new runtime dependency in Milestone 2: `openai` (Apache-2.0, passes the licence gate). Its transitive dependencies are checked by the gate when it is added.
- Swapping providers is configuration, not code. Any other OpenAI-compatible endpoint can be added as a new provider name with its own data guard.
- The `groq` refusal is the only path to a hosted model in Milestone 2, and it is synthetic-only by construction.

## Tests to add (Milestone 2)

1. `LLM_PROVIDER=none`: every feature works and no network call is made.
2. Model not in the provider's `/models` list: startup fails with the clear message, and the key is not in the output.
3. `groq` with one non-synthetic document: the request is refused before any network call. With all documents synthetic, it is allowed (against the fake).
4. A malformed or schema-violating response is rejected and creates no claim.
5. A valid response creates only `llm_suggestion` claims in state `unreviewed`. An attempt to accept one through a service actor fails.
6. `GROQ_API_KEY` never appears in logs, errors or `repr` (captured-log test).
