#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="omi-supabase"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBSITE_DIR="$ROOT_DIR/website"
APP_ENV="$WEBSITE_DIR/pocReviewUi/.env"
SQL_FILE="$ROOT_DIR/supabase/sql/001_omi_supabase_complete_setup.sql"
COMPOSE_DB=(docker compose -p "$PROJECT_NAME" -f "$WEBSITE_DIR/docker-compose.test-postgres.yml")
COMPOSE_WEB=(docker compose -p "$PROJECT_NAME" -f "$WEBSITE_DIR/docker-compose.website.yml")
COMPOSE_N8N=(docker compose -p "$PROJECT_NAME" -f "$WEBSITE_DIR/docker-compose.n8n.yml")

usage() {
  cat <<'EOF'
OMI-Supabase installer

Usage:
  ./install.sh install [--with-n8n] [--non-interactive]
  ./install.sh start [--with-n8n]
  ./install.sh stop [--with-n8n]
  ./install.sh status
  ./install.sh uninstall [--yes] [--keep-env]
  ./install.sh help

Commands:
  install      Create .env if needed, start Postgres, apply schema, start web UI, optionally start n8n.
  start        Start existing stack without reapplying schema.
  stop         Stop containers without deleting volumes/data.
  status       Show stack containers and access URLs.
  uninstall    Remove OMI-Supabase containers, volumes, networks, locally-built images, and generated .env.

Options:
  --with-n8n          Include local n8n container on port 5678.
  --non-interactive   Do not prompt; generate local defaults. You should edit .env afterward.
  --yes              Required for uninstall without confirmation prompt.
  --keep-env          During uninstall, keep website/pocReviewUi/.env.

Default local URLs:
  Web UI: http://localhost:8097/review
  n8n:    http://localhost:5678

EOF
}

has_arg() {
  local needle="$1"; shift
  for arg in "$@"; do [[ "$arg" == "$needle" ]] && return 0; done
  return 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

check_prereqs() {
  need_cmd docker
  docker compose version >/dev/null 2>&1 || {
    echo "Docker Compose plugin is required. Install Docker Engine with the compose plugin." >&2
    exit 1
  }
}

random_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 30 | tr -d '\n'
  else
    python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(30))
PY
  fi
}

write_env() {
  local non_interactive="$1"
  if [[ -f "$APP_ENV" ]]; then
    echo "Using existing $APP_ENV"
    return
  fi
  mkdir -p "$(dirname "$APP_ENV")"
  local ui_user="admin"
  local ui_pass="$(random_password)"
  local omi_key=""
  if [[ "$non_interactive" != "true" ]]; then
    read -r -p "Web UI username [admin]: " input_user || true
    ui_user="${input_user:-admin}"
    read -r -s -p "Web UI password [generated]: " input_pass || true
    echo
    ui_pass="${input_pass:-$ui_pass}"
    read -r -s -p "Omi Developer API key [leave blank for later]: " input_omi || true
    echo
    omi_key="${input_omi:-}"
  fi
  cat > "$APP_ENV" <<EOF
DATABASE_URL=postgresql://postgres:postgres@omi-supabase-test-db:5432/postgres
PMH_UI_USER=$ui_user
PMH_UI_PASSWORD=$ui_pass
OMI_API_BASE=https://api.omi.me
OMI_API_KEY=$omi_key
EOF
  chmod 600 "$APP_ENV"
  echo "Created $APP_ENV"
  if [[ -z "$omi_key" ]]; then
    echo "Note: OMI_API_KEY is blank. Add it to $APP_ENV before using Omi API submit/retrieve features."
  fi
}

wait_for_db() {
  echo "Waiting for Postgres..."
  for _ in {1..60}; do
    if docker exec omi-supabase-test-db pg_isready -U postgres -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "Postgres did not become ready in time." >&2
  exit 1
}

apply_schema() {
  echo "Applying database schema..."
  docker exec -i omi-supabase-test-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 < "$SQL_FILE"
}

start_db() {
  "${COMPOSE_DB[@]}" up -d
  wait_for_db
}

start_web() {
  # Keep compose fragments independent: the DB and optional n8n services are
  # started from separate compose files under the same project name. Do not use
  # --remove-orphans here, or Docker Compose will remove those sibling services.
  "${COMPOSE_WEB[@]}" up -d --build
}

start_n8n() {
  "${COMPOSE_N8N[@]}" up -d
}

install_stack() {
  local with_n8n="$1"
  local non_interactive="$2"
  check_prereqs
  write_env "$non_interactive"
  start_db
  apply_schema
  start_web
  if [[ "$with_n8n" == "true" ]]; then start_n8n; fi
  status_stack
  echo
  echo "Install complete."
}

start_stack() {
  local with_n8n="$1"
  check_prereqs
  start_db
  start_web
  if [[ "$with_n8n" == "true" ]]; then start_n8n; fi
  status_stack
}

stop_stack() {
  local with_n8n="$1"
  check_prereqs
  "${COMPOSE_WEB[@]}" stop || true
  "${COMPOSE_DB[@]}" stop || true
  if [[ "$with_n8n" == "true" ]]; then "${COMPOSE_N8N[@]}" stop || true; fi
}

status_stack() {
  check_prereqs
  echo "Containers:"
  docker ps -a --filter "name=omi-supabase" --format '  {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
  echo
  echo "Web UI: http://localhost:8097/review"
  echo "n8n:    http://localhost:5678"
}

uninstall_stack() {
  local yes="$1"
  local keep_env="$2"
  check_prereqs
  if [[ "$yes" != "true" ]]; then
    echo "This will remove OMI-Supabase containers, volumes, networks, and locally-built images."
    echo "It will also remove $APP_ENV unless --keep-env is used."
    read -r -p "Type 'delete omi-supabase' to continue: " confirm
    [[ "$confirm" == "delete omi-supabase" ]] || { echo "Cancelled."; exit 1; }
  fi
  "${COMPOSE_WEB[@]}" down -v --rmi local --remove-orphans || true
  "${COMPOSE_N8N[@]}" down -v --rmi local --remove-orphans || true
  "${COMPOSE_DB[@]}" down -v --rmi local --remove-orphans || true
  docker rm -f omi-supabase-web omi-supabase-web-test omi-supabase-web-screenshot omi-supabase-test-db omi-supabase-n8n >/dev/null 2>&1 || true
  docker volume ls -q --filter name="${PROJECT_NAME}" | xargs -r docker volume rm >/dev/null 2>&1 || true
  docker network ls --format '{{.Name}}' | grep -E "^${PROJECT_NAME}(_|$)|^website_default$" | xargs -r docker network rm >/dev/null 2>&1 || true
  if [[ "$keep_env" != "true" ]]; then
    rm -f "$APP_ENV"
  fi
  echo "Uninstall complete. Only the pulled repository files should remain."
}

cmd="${1:-help}"; shift || true
with_n8n=false
non_interactive=false
yes=false
keep_env=false
for arg in "$@"; do
  case "$arg" in
    --with-n8n) with_n8n=true ;;
    --non-interactive) non_interactive=true ;;
    --yes) yes=true ;;
    --keep-env) keep_env=true ;;
    -h|--help) cmd=help ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

case "$cmd" in
  install) install_stack "$with_n8n" "$non_interactive" ;;
  start) start_stack "$with_n8n" ;;
  stop) stop_stack "$with_n8n" ;;
  status) status_stack ;;
  uninstall|cleanup|clean) uninstall_stack "$yes" "$keep_env" ;;
  help|-h|--help) usage ;;
  *) echo "Unknown command: $cmd" >&2; usage; exit 2 ;;
esac
