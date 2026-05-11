# OMI-Supabase install smoke test

- Test host: greydesk
- Test started: 2026-05-11T16:06:35+00:00
- Repository: https://github.com/GeekTheGreyBeard/OMI-Supabase.git
- Branch: main
- Source checkout: local working tree


## Fresh package copy

- Base commit: a1d4293 Add reproducible install smoke test
- Included working-tree changes: 1 file(s)
- PASS: fresh package copy created

## Static validation

workflow_exports_ok 6
private_reference_scan_ok
omi_source_system_id_seed_ok b56c1844-4a3c-48dd-ba39-eedf33fdeb7f 5
package_validation_ok
- PASS: static package validation

## Install

Created /tmp/omi-supabase-install-smoke-20260511T160635Z/OMI-Supabase/website/pocReviewUi/.env
Note: OMI_API_KEY is blank. Add it to /tmp/omi-supabase-install-smoke-20260511T160635Z/OMI-Supabase/website/pocReviewUi/.env before using Omi API submit/retrieve features.
 Network omi-supabase_default Creating 
 Network omi-supabase_default Created 
 Container omi-supabase-test-db Creating 
 Container omi-supabase-test-db Created 
 Container omi-supabase-test-db Starting 
 Container omi-supabase-test-db Started 
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
NOTICE:  constraint "approved_memories_omi_visibility_check" of relation "approved_memories" does not exist, skipping
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
 Image omi-supabase-omi-supabase-web Building 
#1 [internal] load local bake definitions
#1 reading from stdin 664B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 344B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.12-slim
#3 DONE 0.5s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 64B done
#5 DONE 0.0s

#6 [1/5] FROM docker.io/library/python:3.12-slim@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe
#6 resolve docker.io/library/python:3.12-slim@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe 0.0s done
#6 DONE 0.0s

#7 [4/5] RUN pip install --no-cache-dir -r /app/requirements.txt
#7 CACHED

#8 [2/5] WORKDIR /app
#8 CACHED

#9 [3/5] COPY requirements.txt /app/requirements.txt
#9 CACHED

#10 [5/5] COPY app.py /app/app.py
#10 CACHED

#11 exporting to image
#11 exporting layers done
#11 exporting manifest sha256:fd2c4541540dcff1f04329367d3b43d5e9fce5f582c353cf5ac8a4f937d1e0ce done
#11 exporting config sha256:e120380968b658a44b95d7d2eba5a1c8e8604cde2e3624dc0caf309a3cc78f8b done
#11 exporting attestation manifest sha256:9700f5b5980c8c45cc8b7705024ed32ea2ca55e0c2e0ec24b957fb83a2e50e7e
#11 exporting attestation manifest sha256:9700f5b5980c8c45cc8b7705024ed32ea2ca55e0c2e0ec24b957fb83a2e50e7e 0.0s done
#11 exporting manifest list sha256:b59b995550a31f3303c00b1d740ebdb4f06bf8694bb2ea9364665d24641e3dc9 0.0s done
#11 naming to docker.io/library/omi-supabase-omi-supabase-web:latest done
#11 unpacking to docker.io/library/omi-supabase-omi-supabase-web:latest 0.0s done
#11 DONE 0.2s

#12 resolving provenance for metadata file
#12 DONE 0.0s
 Image omi-supabase-omi-supabase-web Built 
time="2026-05-11T10:06:39-06:00" level=warning msg="Found orphan containers ([omi-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-supabase-web Creating 
 Container omi-supabase-web Created 
 Container omi-supabase-web Starting 
 Container omi-supabase-web Started 
 Volume omi-supabase_n8n_data Creating 
 Volume omi-supabase_n8n_data Created 
time="2026-05-11T10:06:39-06:00" level=warning msg="Found orphan containers ([omi-supabase-web omi-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-supabase-n8n Creating 
 Container omi-supabase-n8n Created 
 Container omi-supabase-n8n Starting 
 Container omi-supabase-n8n Started 
Containers:
omi-supabase-n8n	Up Less than a second	0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp
omi-supabase-web	Up Less than a second	0.0.0.0:8097->8097/tcp, [::]:8097->8097/tcp
omi-supabase-test-db	Up 4 seconds (health: starting)	0.0.0.0:55432->5432/tcp, [::]:55432->5432/tcp

Web UI: http://localhost:8097/review
n8n:    http://localhost:5678

Install complete.
- PASS: installer completed

## Page checks

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

## Uninstall

 Container omi-supabase-web Stopping 
 Container omi-supabase-web Stopped 
 Container omi-supabase-web Removing 
 Container omi-supabase-web Removed 
 Container omi-supabase-test-db Stopping 
 Container omi-supabase-n8n Stopping 
 Container omi-supabase-test-db Stopped 
 Container omi-supabase-test-db Removing 
 Container omi-supabase-test-db Removed 
 Container omi-supabase-n8n Stopped 
 Container omi-supabase-n8n Removing 
 Container omi-supabase-n8n Removed 
 Image omi-supabase-omi-supabase-web:latest Removing 
 Network omi-supabase_default Removing 
 Network omi-supabase_default Removed 
 Image omi-supabase-omi-supabase-web:latest Removed 
 Volume omi-supabase_n8n_data Removing 
 Volume omi-supabase_n8n_data Removed 
Uninstall complete. Only the pulled repository files should remain.
- PASS: uninstall completed
- PASS: no project containers remain
- PASS: no project volumes remain
- PASS: generated env removed

## Result

- Passed checks: 18
- Failed checks: 0
- Test completed: 2026-05-11T16:06:44+00:00

**Overall result: PASS**
