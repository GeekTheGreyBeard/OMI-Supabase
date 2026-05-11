# OMI-Supabase install smoke test

- Test host: Proxmox VM `9903` / `omi-releasegate-vm-20260511-1114`
- Test VM IP: `10.0.250.91`
- Proxmox node: `pm3`
- Source template: `9501` / `Ubuntu-resolute-NFS`
- Test started: 2026-05-11T17:30:22Z
- Test completed: 2026-05-11T17:35:17Z
- Repository: https://github.com/GeekTheGreyBeard/OMI-Supabase.git
- Branch: `main`
- Source checkout: GitHub HEAD cloned inside the test VM
- Source commit: `382946600c4ab7d845682b9a7578e98a6dfd22fb`
- Test command: `./scripts/run_install_smoke_test.sh`

## Scope

Fresh release-gate validation was run in a disposable full Proxmox VM, not on greydesk. The test cloned GitHub HEAD inside the VM, ran static package validation, installed Postgres + Memory Console web UI + n8n, exercised routes, then uninstalled and verified cleanup.

The VM initially exposed a broken distro Docker/snapshotter state (`parent snapshot ... does not exist`). Because the VM is disposable release-gate infrastructure, the distro Docker packages were replaced with Docker CE from Docker's official installer before the passing run.

## Static validation

```text
workflow_exports_ok 6
private_reference_scan_ok
omi_source_system_id_seed_ok b56c1844-4a3c-48dd-ba39-eedf33fdeb7f 5
package_validation_ok
- PASS: static package validation
```

## Install

```text
Created /tmp/omi-supabase-install-smoke-20260511T173022Z/OMI-Supabase/website/pocReviewUi/.env
Note: OMI_API_KEY is blank. Add it to .../website/pocReviewUi/.env before using Omi API submit/retrieve features.
Waiting for Postgres...
Applying database schema...
CREATE EXTENSION
CREATE SCHEMA
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
INSERT 0 5
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE TABLE
CREATE TABLE
CREATE VIEW
CREATE VIEW
CREATE FUNCTION
CREATE INDEX
CREATE INDEX
CREATE INDEX
ALTER TABLE
ALTER TABLE
CREATE TABLE
INSERT 0 0
ALTER TABLE
NOTICE: constraint "approved_memories_omi_visibility_check" of relation "approved_memories" does not exist, skipping
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
Image omi-supabase-omi-supabase-web Built
omi-supabase-web Started
omi-supabase-n8n Started
Install complete.
- PASS: installer completed
```

## Page checks

```text
- PASS: web UI became reachable
- PASS: health route returns 200
- PASS: memory home route returns 200
- PASS: review route returns 200
- PASS: review page contains home button
- PASS: primary memories route returns 200
- PASS: new memory route returns 200
- PASS: submissions route returns 200
- PASS: trash route returns 200
- PASS: n8n route became reachable
- PASS: n8n route reachable
```

## Uninstall

```text
Uninstall complete. Only the pulled repository files should remain.
- PASS: uninstall completed
- PASS: no project containers remain
- PASS: no project volumes remain
- PASS: generated env removed
```

## Result

```text
- Passed checks: 18
- Failed checks: 0
- Test completed: 2026-05-11T17:35:17+00:00

**Overall result: PASS**
```
