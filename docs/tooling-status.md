# Plugin and tool status

Verified 2026-11-18 in a cloud session on the `ukg-delivery-intelligence-workbench` environment, after a container restart. Re-verify in each new environment: `bash scripts/setup-claude-tools.sh --check` covers the CLI rows; `claude plugin list` covers the plugin rows.

Columns: **Configured** = declared in `.claude/settings.json` or the claude.ai account. **Installed** = present on this machine. **Loaded** = active in the session. **Available** = shown to work by an actual test.

## Claude Code plugins

| Capability | Configured | Installed | Loaded | Available | Evidence and notes |
|---|---|---|---|---|---|
| ponytail 5.3.3 | Project (pinned `v5.3.3`) | Yes | Yes | **Yes** | Its SessionStart hook prints `PONYTAIL MODE ACTIVE` |
| superpowers | Project **and** account | **Project copy: no.** Account copy 7.0.2: yes | Account copy only | **Yes** | The project entry points at an external GitHub repo (reachable) and was not auto-installed; the account copy loads once. Skills (brainstorming and others) invoked successfully |
| frontend-design 1.1.1 | Project and account | Project copy | Project copy; account copy skipped ("same name … takes precedence") | Loaded, not yet exercised | Will be used in slice 7 |
| security-guidance 2.0.20 | Project and account | Project copy | Project copy; account copy (2.0.17) skipped | **Yes** | Hook invoked on a test file: flagged `pickle.loads` and `subprocess(..., shell=True)` with remediation. It also runs an LLM security review on `git commit`/`git push` (asynchronous) |
| skill-creator | Project | Project copy | Yes | **Yes** | Its `quick_validate.py` validates project skills. A built-in `anthropic-skills:skill-creator` is also listed: a duplicate skill, not a duplicate hook. Use the plugin copy |
| pyright-lsp 1.0.0 | Project and account | Project copy | Project copy | Server verified; in-session diagnostics not yet observed | `pyright-langserver` returned a real type diagnostic over LSP. The editor feedback path appears only once `.py` files are edited |
| typescript-lsp 1.0.0 | Project and account | Project copy | Project copy | Server verified; in-session diagnostics not yet observed | `typescript-language-server` answered hover over LSP (needs TypeScript 6.x; 7.x has no tsserver) |
| **context7** | Project and account | Project copy | MCP server configured | **NO: unavailable** | The network block is fixed (`mcp.context7.com` and `clerk.context7.com` allowed). The server now **requires an OAuth sign-in**, which this cloud session cannot complete. **Stays unavailable until OAuth succeeds.** Fallback: official docs, recording the version checked |

**Duplicate check:** no plugin and no hook loads twice. Claude Code skips every account copy whose name matches a project-installed plugin. The only duplicate is the Skill Creator skill (plugin and built-in), which is harmless.

## Project hooks (`.claude/settings.json`)

| Hook | Trigger | Available | Notes |
|---|---|---|---|
| graphify `hook-guard search` / `read` | PreToolUse on Bash, Grep, Read, Glob | **Yes** | Advisory only (exit 0); guarded so it does nothing when graphify is missing |
| graphify `hook-guard compact` | SessionStart (compact) | Configured | Not yet triggered |

## CLI tools

| Tool | Version | Available | Evidence and limits |
|---|---|---|---|
| uv | 0.11.32 | **Yes** | setup `--check` |
| graphify (`graphifyy`) | 0.9.112 | **Partly** | Builds a repo graph with no API key (667 nodes, 638 edges). Indexes code symbols and Markdown section headings only: it **misses body text and cross-document references** (no path from the Milestone 1 plan to `impact-propagation.md` although the plan cites it; a `same_as` query returned unrelated Playwright docs). Its semantic pass needs a Gemini or Google key, **deliberately not added**. Use it for a section-level map, and grep for exhaustive search |
| playwright-cli | 0.1.24 | **Yes** | Opened a localhost page, clicked, read the DOM. `file://` is blocked by design. Uses the image's Chromium; nothing extra downloaded |
| pyright | 1.1.414 | **Yes** | Type diagnostics verified |
| typescript-language-server / tsc | 6.1.0 / 6.0.3 | **Yes** | Hover verified |
| PostgreSQL | 16 server binaries (`initdb`) | Installed, not yet exercised | Docker daemon **unavailable**, so tests use a local `initdb` cluster |
| Node / npm / Python | 22.23.5 / 10.9.9 / 3.13.18 | **Yes** | |

## Agents (`.claude/agents/`)

| Agent | Model | Loaded | Used |
|---|---|---|---|
| scout | haiku | Yes | Not yet |
| implementer | sonnet | Yes | Yes: wrote the interview guide |
| architect | opus | Yes | Yes: D3/D4 revision 2 |

## Other

| Capability | Status |
|---|---|
| GitHub MCP tools | Available (repo-scoped) |
| Network | Limited: package registries plus an allowlist (UKG documentation, W3C, Artifex, PyMuPDF docs, React Flow docs, Context7) |
| Framework docs without Context7 | Hosts like nextjs.org, fastapi.tiangolo.com and docs.pydantic.dev are **not** allowlisted yet. They will be requested when Phase 3 needs them |
