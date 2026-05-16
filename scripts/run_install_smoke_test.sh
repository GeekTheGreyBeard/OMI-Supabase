#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="omi-memory-supabase"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="${TMPDIR:-/tmp}/omi-memory-supabase-install-smoke-$STAMP"
LOG="${LOG:-$ROOT/installTest.md}"
REPO_URL="${REPO_URL:-$(git -C "$ROOT" config --get remote.origin.url 2>/dev/null || printf '%s' "$ROOT")}"
BRANCH="${BRANCH:-$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'unknown')}"
WITH_N8N="${WITH_N8N:-1}"
FAILED=0
PASSED=0

pass() { printf -- '- PASS: %s\n' "$1" | tee -a "$LOG"; PASSED=$((PASSED+1)); }
fail() { printf -- '- FAIL: %s\n' "$1" | tee -a "$LOG"; FAILED=$((FAILED+1)); }
section() { printf '\n## %s\n\n' "$1" | tee -a "$LOG"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

check_no_existing_stack() {
  local existing
  existing="$(docker ps -a --filter "name=omi-memory-supabase" --format '{{.Names}}' || true)"
  if [[ -n "$existing" ]]; then
    echo "Refusing to run: existing omi-memory-supabase containers are present:" >&2
    echo "$existing" >&2
    echo "Stop/remove the stack intentionally before running this smoke test." >&2
    exit 1
  fi
}

cleanup() {
  if [[ -d "$WORKDIR/OMI-Memory-Supabase" ]]; then
    (cd "$WORKDIR/OMI-Memory-Supabase" && ./install.sh uninstall --yes >/tmp/omi-memory-supabase-smoke-cleanup.log 2>&1) || true
  fi
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

wait_for_http() {
  local url="$1"
  local use_auth="${2:-0}"
  local auth_args=()
  if [[ "$use_auth" == "1" && -n "${UI_USER:-}" && -n "${UI_PASS:-}" ]]; then
    auth_args=(-u "$UI_USER:$UI_PASS")
  fi
  for _ in {1..60}; do
    if curl -fsS -L -o /dev/null "${auth_args[@]}" "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

fetch() {
  local url="$1"
  local expected="$2"
  local label="$3"
  local contains="${4:-}"
  local out code
  out="$(mktemp)"
  code="$(curl -sS -L -o "$out" -w '%{http_code}' -u "$UI_USER:$UI_PASS" "$url" || true)"
  if [[ "$code" == "$expected" ]]; then
    if [[ -n "$contains" ]] && ! grep -qi -- "$contains" "$out"; then
      fail "$label contains '$contains'"
    else
      pass "$label"
    fi
  else
    fail "$label returned HTTP $code, expected $expected"
  fi
  rm -f "$out"
}

require_cmd git
require_cmd docker
require_cmd curl
docker compose version >/dev/null
check_no_existing_stack

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
: > "$LOG"
cat >> "$LOG" <<EOF
# OMI-Memory-Supabase install smoke test

- Test host: $(hostname)
- Test started: $(date -u --iso-8601=seconds)
- Repository: $REPO_URL
- Branch: $BRANCH
- Source checkout: local working tree

EOF

section "Fresh package copy"
mkdir -p "$WORKDIR/OMI-Memory-Supabase"
tar --exclude='./.git' --exclude='./website/pocReviewUi/.env' -C "$ROOT" -cf - . | tar -C "$WORKDIR/OMI-Memory-Supabase" -xf -
cd "$WORKDIR/OMI-Memory-Supabase"
COMMIT="$(git -C "$ROOT" log -1 --oneline 2>/dev/null || printf 'unknown')"
DIRTY="$(git -C "$ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')"
printf -- '- Base commit: %s\n' "$COMMIT" | tee -a "$LOG"
printf -- '- Included working-tree changes: %s file(s)\n' "$DIRTY" | tee -a "$LOG"
pass "fresh package copy created"

section "Static validation"
if ./scripts/validate_package.sh 2>&1 | tee -a "$LOG"; then
  pass "static package validation"
else
  fail "static package validation"
fi

section "Install"
INSTALL_ARGS=(install --non-interactive)
if [[ "$WITH_N8N" == "1" ]]; then INSTALL_ARGS+=(--with-n8n); fi
if ./install.sh "${INSTALL_ARGS[@]}" 2>&1 | tee -a "$LOG"; then
  pass "installer completed"
else
  fail "installer completed"
fi

set -a
# shellcheck disable=SC1091
source website/pocReviewUi/.env
set +a
UI_USER="$PMH_UI_USER"
UI_PASS="$PMH_UI_PASSWORD"

section "Page checks"
if wait_for_http 'http://localhost:8097/health' 1; then
  pass "web UI became reachable"
else
  fail "web UI became reachable"
fi
fetch 'http://localhost:8097/health' 200 'health route returns 200' '"ok":true'
fetch 'http://localhost:8097/memory/home' 200 'memory home route returns 200' 'Memory Console'
fetch 'http://localhost:8097/review' 200 'review route returns 200' 'Review'
fetch 'http://localhost:8097/review' 200 'review page contains home button' 'Home'
fetch 'http://localhost:8097/memories' 200 'primary memories route returns 200' 'Primary'
fetch 'http://localhost:8097/memory/new' 200 'new memory route returns 200' 'Create new memory'
fetch 'http://localhost:8097/submissions' 200 'submissions route returns 200' 'Submission'
fetch 'http://localhost:8097/trash' 200 'trash route returns 200' 'Trash'
if [[ "$WITH_N8N" == "1" ]]; then
  if wait_for_http 'http://localhost:5678/'; then
    pass "n8n route became reachable"
  else
    fail "n8n route became reachable"
  fi
  code="$(curl -sS -L -o /tmp/omi-memory-supabase-n8n-smoke.out -w '%{http_code}' http://localhost:5678/ || true)"
  if [[ "$code" =~ ^(200|302)$ ]]; then pass "n8n route reachable"; else fail "n8n route returned HTTP $code"; fi
  rm -f /tmp/omi-memory-supabase-n8n-smoke.out
fi

section "Uninstall"
if ./install.sh uninstall --yes 2>&1 | tee -a "$LOG"; then
  pass "uninstall completed"
else
  fail "uninstall completed"
fi
if [[ -z "$(docker ps -a --filter "name=omi-memory-supabase" --format '{{.Names}}')" ]]; then pass "no project containers remain"; else fail "project containers remain"; fi
if [[ -z "$(docker volume ls -q --filter "name=${PROJECT_NAME}")" ]]; then pass "no project volumes remain"; else fail "project volumes remain"; fi
if [[ ! -f website/pocReviewUi/.env ]]; then pass "generated env removed"; else fail "generated env remains"; fi

section "Result"
printf -- '- Passed checks: %s\n- Failed checks: %s\n- Test completed: %s\n\n' "$PASSED" "$FAILED" "$(date -u --iso-8601=seconds)" | tee -a "$LOG"
if [[ "$FAILED" -eq 0 ]]; then
  printf '**Overall result: PASS**\n' | tee -a "$LOG"
else
  printf '**Overall result: FAIL**\n' | tee -a "$LOG"
  exit 1
fi
