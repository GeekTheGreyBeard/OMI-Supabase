# OMI-Memory-Supabase Test Notes

## Fresh install smoke test

The strongest local release gate is the repository smoke-test runner:

```bash
./scripts/run_install_smoke_test.sh
```

It creates a disposable copy of the current working tree, runs static package validation, performs a non-interactive install with local Postgres and n8n, checks the main authenticated web routes plus n8n reachability, uninstalls the stack, and verifies generated containers, volumes, and `.env` are removed. The script refuses to start if existing `omi-memory-supabase` containers are present, to avoid disturbing a live local stack.

By default it refreshes `installTest.md` with the latest evidence. Set `LOG=/path/to/file` to write elsewhere, or `WITH_N8N=0` to skip the n8n container check.

## Disposable database validation

Command pattern used:

```bash
cd n8n/OMI-Memory-Supabase/website
docker compose -f docker-compose.test-postgres.yml up -d
docker exec -i omi-memory-supabase-test-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 < ../supabase/sql/001_omi_memory_supabase_complete_setup.sql
```

Result:

```text
sources=5
tables=14
```

## Website validation

Built the package-local website image and ran it against the disposable Postgres database with dummy UI credentials and no real Omi key.

Smoke-tested:

- `GET /health` returned `{"ok": true}`.
- `GET /review` with Basic Auth rendered the review queue.
- `GET /memory/new` with Basic Auth rendered the scratch-memory form.

## Workflow export validation

`scripts/validate_package.sh` verifies:

- `website/pocReviewUi/app.py` compiles.
- Every `workflows/*.workflow.json` parses as JSON.
- Every workflow export contains nodes.
- Every workflow export is inactive to prevent accidental webhook collisions.

Result:

```text
workflow_exports_ok 6
package_validation_ok
```

## Cleanup

Test containers were removed after validation:

```bash
docker rm -f omi-memory-supabase-web-test
docker compose -f docker-compose.test-postgres.yml down -v
```
