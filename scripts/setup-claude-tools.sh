#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
# Installs the CLI tooling Claude Code uses on this repo: uv, Graphify, Playwright CLI,
# Pyright and the TypeScript language server. Idempotent: tools already at the pinned
# version are left alone. Contains no credentials and needs none.
#
#   scripts/setup-claude-tools.sh           install what is missing, then verify
#   scripts/setup-claude-tools.sh --check   verify only, install nothing (exit 1 if anything is missing)
#
# Versions are pinned to what was verified working; override with env vars, e.g.
# PLAYWRIGHT_CLI_VERSION=latest. "latest" installs only when the tool is missing.
set -euo pipefail

GRAPHIFY_VERSION="${GRAPHIFY_VERSION:-0.9.112}"
PLAYWRIGHT_CLI_VERSION="${PLAYWRIGHT_CLI_VERSION:-0.1.24}"
PYRIGHT_VERSION="${PYRIGHT_VERSION:-1.1.414}"
TSLS_VERSION="${TSLS_VERSION:-6.1.0}"
# TypeScript 7 ships no tsserver.js, which typescript-language-server needs. Stay on 6.x.
TYPESCRIPT_VERSION="${TYPESCRIPT_VERSION:-6.0.3}"
MIN_NODE_MAJOR=20
MIN_PYTHON="3.11"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
FAILED=0

log()  { printf '[setup-claude-tools] %s\n' "$*"; }
fail() { printf '[setup-claude-tools] ERROR: %s\n' "$*" >&2; exit 1; }
miss() { printf '[setup-claude-tools] MISSING: %s\n' "$*" >&2; FAILED=1; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- prerequisites (provided by the environment image, not installed here) ---
have node || fail "node not found; this script does not install Node (need >= $MIN_NODE_MAJOR)"
have npm  || fail "npm not found"
have python3 || fail "python3 not found; this script does not install Python (need >= $MIN_PYTHON)"
node_major="$(node -p 'process.versions.node.split(".")[0]')"
(( node_major >= MIN_NODE_MAJOR )) || fail "node $(node --version) is older than $MIN_NODE_MAJOR"
python3 -c "import sys; sys.exit(0 if sys.version_info >= tuple(map(int, '$MIN_PYTHON'.split('.'))) else 1)" \
  || fail "python $(python3 --version) is older than $MIN_PYTHON"
log "node $(node --version), npm $(npm --version), $(python3 --version)"

net_checked=0
require_network() {
  (( net_checked )) && return 0
  for url in https://registry.npmjs.org/ https://pypi.org/simple/; do
    curl -fsS --max-time 15 -o /dev/null "$url" \
      || fail "cannot reach $url; check the environment's network access (package managers must be allowed)"
  done
  net_checked=1
}

# --- uv ---
if ! have uv; then
  if (( CHECK_ONLY )); then miss "uv"; else
    require_network
    log "installing uv"
    python3 -m pip install --user --quiet uv 2>/dev/null \
      || python3 -m pip install --user --quiet --break-system-packages uv \
      || fail "could not install uv with pip (permissions or network)"
  fi
fi
have uv && log "uv $(uv --version | awk '{print $2}')"

# --- graphify (PyPI package name is graphifyy) ---
graphify_ok() { have graphify && { [[ "$GRAPHIFY_VERSION" == latest ]] || [[ "$(graphify --version 2>/dev/null | awk '{print $2}')" == "$GRAPHIFY_VERSION" ]]; }; }
if ! graphify_ok; then
  if (( CHECK_ONLY )); then miss "graphify $GRAPHIFY_VERSION"; else
    have uv || fail "uv is required to install graphify"
    require_network
    spec="graphifyy"; [[ "$GRAPHIFY_VERSION" != latest ]] && spec="graphifyy==$GRAPHIFY_VERSION"
    log "installing $spec"
    uv tool install --force "$spec" || fail "uv tool install $spec failed"
  fi
fi

# --- npm globals ---
npm_version() { npm ls -g --depth=0 --json 2>/dev/null | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const d=JSON.parse(s||"{}").dependencies||{};process.stdout.write((d[process.argv[1]]||{}).version||"")})' "$1"; }
to_install=()
for pair in "@playwright/cli:$PLAYWRIGHT_CLI_VERSION" "pyright:$PYRIGHT_VERSION" \
            "typescript-language-server:$TSLS_VERSION" "typescript:$TYPESCRIPT_VERSION"; do
  pkg="${pair%:*}"; want="${pair##*:}"; got="$(npm_version "$pkg")"
  if [[ -z "$got" ]] || { [[ "$want" != latest ]] && [[ "$got" != "$want" ]]; }; then
    if (( CHECK_ONLY )); then miss "$pkg@$want (found: ${got:-none})"; else to_install+=("$pkg@$want"); fi
  fi
done
if (( ${#to_install[@]} )); then
  require_network
  log "npm install -g ${to_install[*]}"
  npm install -g --no-fund --no-audit "${to_install[@]}" \
    || fail "npm install -g failed (permissions on $(npm config get prefix), or network)"
fi

# --- browser for playwright-cli: reuse the image's Chromium, never download a second one here ---
if [[ ! -d /opt/pw-browsers ]] && ! ls "$HOME"/.cache/ms-playwright/chromium-* >/dev/null 2>&1; then
  log "WARNING: no Chromium found; run 'playwright-cli install-browser' if browser checks are needed"
fi

# --- project skills are committed; do not regenerate them here (graphify install rewrites settings hooks) ---
for skill in graphify playwright-cli; do
  [[ -f "$ROOT/.claude/skills/$skill/SKILL.md" ]] || miss "skill .claude/skills/$skill/SKILL.md (regenerate deliberately and review the diff)"
done

# --- verify ---
for bin in uv graphify playwright-cli pyright pyright-langserver typescript-language-server tsc; do
  have "$bin" || miss "$bin not on PATH"
done
if (( FAILED == 0 )); then
  log "graphify $(graphify --version | awk '{print $2}') | playwright-cli $(playwright-cli --version) | $(pyright --version) | typescript-language-server $(typescript-language-server --version) | tsc $(tsc --version | awk '{print $2}')"
  log "OK"
else
  fail "verification failed (see MISSING lines above)"
fi
