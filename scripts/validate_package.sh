#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m py_compile "$ROOT/website/pocReviewUi/app.py"
python3 - <<PY
import json, pathlib
root=pathlib.Path('$ROOT')
files=list((root/'workflows').glob('*.workflow.json'))
assert files, 'no workflow exports found'
for f in files:
    data=json.load(open(f))
    assert data.get('nodes'), f'{f} has no nodes'
    assert data.get('active') is False, f'{f} must be inactive for safe import'
print('workflow_exports_ok', len(files))
PY
if command -v psql >/dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$ROOT/supabase/sql/001_omi_supabase_complete_setup.sql"
fi
echo 'package_validation_ok'
