# OMI-Supabase Installer Test

## Result

**Overall result: PASS**

- Fresh full-VM validation completed: 2026-05-10.
- Public repo commit tested: `f048dd8` (`Keep installer compose services during web startup`).
- Test mode: cloned the public GitHub repository, installed the local stack, exercised memory-management workflows with disposable/mock Omi data, uninstalled the stack, and verified cleanup.
- Check summary: **38 passed, 0 failed**.
- Secrets: generated UI credentials and mock API key were not recorded.

## Environment Summary

- Full VM, not LXC.
- Test user: `gtgb`.
- OS family: Ubuntu Linux.
- Runtime prerequisites installed before the repo test:
  - `git`
  - Docker Engine
  - Docker Compose plugin
- Docker was verified usable by `gtgb` without `sudo`.

## Important Finding During Initial Diagnostic Pass

An initial same-VM diagnostic attempt exposed an installer issue: the web startup command used Docker Compose `--remove-orphans` while the database, web UI, and optional n8n services are intentionally split across compose files under the same project name. That caused the web compose step to remove sibling services such as Postgres/n8n.

Fix committed before the comprehensive pass:

- Commit: `f048dd8 Keep installer compose services during web startup`
- Change: `install.sh` no longer uses `--remove-orphans` during normal web startup.
- Cleanup still uses explicit `down -v --rmi local --remove-orphans` paths during uninstall.

The successful comprehensive test below was run from a fresh clone of the fixed public repository.

## Step-by-Step Test Summary

### 1. Baseline VM and Prerequisites

Validated:

- VM booted cleanly.
- Root filesystem had sufficient free space.
- Memory was sufficient for Postgres, FastAPI UI, n8n, and mock Omi API.
- Docker and Compose were available.
- `docker ps` worked as the `gtgb` user.

Result: **PASS**

### 2. Repository Sync

Command flow tested:

```bash
git clone https://github.com/GeekTheGreyBeard/OMI-Supabase.git OMI-Supabase
cd OMI-Supabase
git rev-parse --short HEAD
git status --short
```

Validated:

- Public repository cloned successfully.
- Tested commit was `f048dd8`.
- Working tree was clean immediately after clone.

Result: **PASS**

### 3. Static Package Validation

Command tested:

```bash
./scripts/validate_package.sh
```

Observed:

```text
workflow_exports_ok 6
package_validation_ok
```

Validated:

- Six n8n workflow exports were present and parseable.
- Package validation passed.

Result: **PASS**

### 4. Installer Install With Local n8n

Command tested:

```bash
./install.sh install --non-interactive --with-n8n
```

Validated:

- Installer created repo-local `website/pocReviewUi/.env`.
- Postgres container started and became healthy.
- SQL schema applied successfully.
- FastAPI review UI image built and container started.
- n8n container started on the local n8n port.
- Postgres remained running after web startup, confirming the compose-orphan fix.

Health/UI checks:

- `/health` returned `{"ok": true}`.
- Authenticated `/review` loaded.
- Authenticated `/memory/new` loaded.
- n8n HTTP endpoint became reachable.

Database checks:

- `pmh` schema objects existed.
- Five `pmh.source_systems` seed rows existed.
- `pmh.review_queue` view existed.

Result: **PASS**

### 5. Mock Omi API Setup

A disposable local mock Omi API container was attached to the same Docker network. It implemented the Omi memory endpoints needed for this test:

- `GET /v1/dev/user/memories`
- `POST /v1/dev/user/memories`
- `DELETE /v1/dev/user/memories/{id}`
- `GET /mock/state` for verification only

The UI `.env` was adjusted to point at the mock API, then the web container was rebuilt/restarted.

Validated:

- Web health returned OK after restart.
- Mock Omi API was reachable from the web container.
- Postgres still remained running after web restart.

Result: **PASS**

### 6. Omi Pull and Candidate Review Lifecycle

Tested flow:

1. Pulled two mock Omi memories through the UI pull endpoint.
2. Confirmed two `pmh.memory_candidates` rows were created.
3. Confirmed the review page displayed pulled mock memory content.
4. Selected a candidate.
5. Submitted `correct_and_approve` review action with edited title/content, category, sensitivity, visibility, recall flag, tag, and notes.
6. Confirmed the approved memory appeared in primary memory.
7. Confirmed review action history was recorded.

Validated objects:

- `pmh.raw_events`
- `pmh.memory_candidates`
- `pmh.external_refs`
- `pmh.approved_memories`
- `pmh.review_actions`

Result: **PASS**

### 7. Approved Memory Edit, Omi Replace Sync, Trash, and Restore

Tested flow:

1. Edited an approved memory through the UI.
2. Confirmed edit set confidence to `1.000`.
3. Submitted the edited memory to Omi.
4. Confirmed replacement sync job succeeded.
5. Confirmed the original mock Omi ID was marked `deleted_remote`.
6. Confirmed the mock Omi API received a delete for the superseded memory.
7. Moved the approved memory to trash.
8. Confirmed lifecycle became `deleted` and recall was disabled.
9. Confirmed trash page displayed the deleted memory.
10. Restored the trashed memory.
11. Confirmed lifecycle returned to `active`.
12. Confirmed restore queued a new create sync job.

Validated behavior:

- PMH treats Omi as a source of candidate evidence, not truth.
- Durable memory requires approval before entering primary memory.
- Edits preserve PMH as the reviewed source of truth.
- Omi replace behavior creates a new mock memory and deletes the superseded original.
- Trash disables recall eligibility.
- Restore does not resurrect old Omi IDs; it queues a fresh create.

Result: **PASS**

### 8. Scratch Memory and Submission Queue

Tested flow:

1. Created a new memory from scratch using `/memory/new`.
2. Confirmed approved memory row was created.
3. Confirmed a queued create sync job was created.
4. Confirmed submission queue displayed the scratch memory.
5. Submitted the scratch memory to mock Omi.
6. Confirmed create sync succeeded.

Result: **PASS**

### 9. Pre-Uninstall State Summary

Before uninstall, the stack contained expected test data:

- PMH tables: `14`
- Candidates: `2`
- Approved memories: `2`
- Review actions: `6`
- Sync jobs: `5`

Mock Omi API observed:

- Two created memories:
  - edited approved memory replacement
  - scratch memory submission
- Two deleted IDs:
  - original pulled Omi memory superseded by replacement
  - replacement memory deleted during trash flow

Result: **PASS**

### 10. Full Uninstall and Cleanup Verification

Command tested:

```bash
./install.sh uninstall --yes
```

Validated cleanup:

- OMI-Supabase containers removed.
- OMI-Supabase Docker volumes removed.
- OMI-Supabase Docker networks removed.
- Locally built OMI-Supabase web image removed.
- Generated `website/pocReviewUi/.env` removed.
- Pulled repository files remained.
- Git working tree remained clean after uninstall.

Result: **PASS**

## Final Verification Matrix

| Area | Result |
| --- | --- |
| Fresh public clone | PASS |
| Package/workflow validation | PASS |
| Installer install | PASS |
| Postgres schema setup | PASS |
| FastAPI review UI | PASS |
| Optional local n8n startup | PASS |
| Mock Omi API connectivity | PASS |
| Omi pull to candidate queue | PASS |
| Candidate correction/approval | PASS |
| Approved memory edit | PASS |
| Omi replace sync | PASS |
| Trash lifecycle | PASS |
| Restore lifecycle | PASS |
| Scratch memory creation | PASS |
| Submission queue | PASS |
| Mock Omi create/delete behavior | PASS |
| Full uninstall | PASS |
| Runtime trace cleanup | PASS |

## Conclusion

The standalone public OMI-Supabase POC installer passed comprehensive fresh-VM validation after the compose-orphan fix. The install flow, review/approval memory-management flow, Omi pull/replace/create/delete behavior against a mock Omi API, trash/restore lifecycle, submission queue, and uninstall cleanup all behaved as expected.
