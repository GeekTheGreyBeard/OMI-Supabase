#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m py_compile "$ROOT/website/pocReviewUi/app.py"
python3 - <<PY
import json, os, pathlib, re, sys
root=pathlib.Path('$ROOT')
files=list((root/'workflows').glob('*.workflow.json'))
assert files, 'no workflow exports found'
for f in files:
    data=json.load(open(f))
    assert data.get('nodes'), f'{f} has no nodes'
    assert data.get('active') is False, f'{f} must be inactive for safe import'
print('workflow_exports_ok', len(files))

scan_exts={'.md','.py','.sh','.sql','.json','.yml','.yaml'}
private_patterns=[
    (re.compile(r'/home/(?!node\b|app\b|runner\b)[^/\s]+\b'), 'local user home path'),
    (re.compile(r'/run/media/[^/\s]+\b'), 'local removable-media mount path'),
    (re.compile(r'\b(?:[a-z0-9-]+\.)+(?:lan|local|internal)\b', re.I), 'private/internal domain'),
]
extra_patterns = [p for p in os.environ.get('PRIVATE_REFERENCE_PATTERNS', '').splitlines() if p.strip()]
for pattern in extra_patterns:
    private_patterns.append((re.compile(pattern, re.I), 'custom private reference'))
violations=[]
for path in root.rglob('*'):
    if '.git' in path.parts or path.is_dir() or path.suffix not in scan_exts or path.name == 'validate_package.sh':
        continue
    text=path.read_text(errors='ignore')
    for rx,label in private_patterns:
        for m in rx.finditer(text):
            line=text.count('\n', 0, m.start())+1
            violations.append(f'{path.relative_to(root)}:{line}: {label}: {m.group(0)}')
if violations:
    raise AssertionError('private/internal references found:\n' + '\n'.join(violations))
print('private_reference_scan_ok')

sql=(root/'supabase/sql/001_omi_memory_supabase_complete_setup.sql').read_text()
seed=re.search(r"\('([0-9a-f-]{36})'::uuid,\s*'omi'", sql, re.I)
assert seed, 'omi source_systems seed must use deterministic source_system_id uuid'
omi_source_id=seed.group(1).lower()
workflow_ids=[]
for f in files:
    text=f.read_text()
    for m in re.finditer(r"source_system_id:\s*'([0-9a-f-]{36})'", text, re.I):
        workflow_ids.append((f.relative_to(root), m.group(1).lower()))
for f, value in workflow_ids:
    assert value == omi_source_id, f'{f} hardcoded source_system_id {value} does not match SQL omi seed {omi_source_id}'
assert workflow_ids, 'expected workflows to declare omi source_system_id or use an explicit lookup path'
print('omi_source_system_id_seed_ok', omi_source_id, len(workflow_ids))
PY
if command -v psql >/dev/null && [[ -n "${DATABASE_URL:-}" ]]; then
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$ROOT/supabase/sql/001_omi_memory_supabase_complete_setup.sql"
fi
echo 'package_validation_ok'
