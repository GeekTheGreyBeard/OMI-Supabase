# OMI-Supabase Test Notes

## Disposable database validation

Command pattern used:

```bash
cd n8n/OMI-Supabase/website
docker compose -f docker-compose.test-postgres.yml up -d
docker exec -i omi-supabase-test-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 < ../supabase/sql/001_omi_supabase_complete_setup.sql
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
docker rm -f omi-supabase-web-test
docker compose -f docker-compose.test-postgres.yml down -v
```
