# OMI-Memory-Supabase install smoke test

- Test host: greydesk
- Test started: 2026-05-16T13:53:35+00:00
- Repository: https://github.com/GeekTheGreyBeard/OMI-Memory-Supabase.git
- Branch: main
- Source checkout: local working tree


## Fresh package copy

- Base commit: 8977bf0 Update install evidence from Proxmox VM
- Included working-tree changes: 19 file(s)
- PASS: fresh package copy created

## Static validation

workflow_exports_ok 6
private_reference_scan_ok
omi_source_system_id_seed_ok b56c1844-4a3c-48dd-ba39-eedf33fdeb7f 5
package_validation_ok
- PASS: static package validation

## Install

Created /tmp/omi-memory-supabase-install-smoke-20260516T135335Z/OMI-Memory-Supabase/website/pocReviewUi/.env
Note: OMI_API_KEY is blank. Add it to /tmp/omi-memory-supabase-install-smoke-20260516T135335Z/OMI-Memory-Supabase/website/pocReviewUi/.env before using Omi API submit/retrieve features.
 Network omi-memory-supabase_default Creating
 Network omi-memory-supabase_default Created
 Container omi-memory-supabase-test-db Creating
 Container omi-memory-supabase-test-db Created
 Container omi-memory-supabase-test-db Starting
 Container omi-memory-supabase-test-db Started
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
 Image omi-memory-supabase-omi-memory-supabase-web Building
#1 [internal] load local bake definitions
#1 reading from stdin 734B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 344B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.12-slim
#3 DONE 0.9s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 64B done
#5 DONE 0.0s

#6 [1/5] FROM docker.io/library/python:3.12-slim@sha256:401f6e1a67dad31a1bd78e9ad22d0ee0a3b52154e6bd30e90be696bb6a3d7461
#6 resolve docker.io/library/python:3.12-slim@sha256:401f6e1a67dad31a1bd78e9ad22d0ee0a3b52154e6bd30e90be696bb6a3d7461 0.0s done
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
#11 exporting manifest sha256:9cf62dcbf213fb96fd140327480b1ef77ccfe11d6d6d36bfb502e0c10e280d40 0.0s done
#11 exporting config sha256:585ac7f19c9023a8d7373eeae812c116284407973b6fce7e7c4bde8d00cb2a24 0.0s done
#11 exporting attestation manifest sha256:0ceb63b40052a4dc45054f51db94dba12526c89971d6c21d6b881dfdb0a29d32 0.0s done
#11 exporting manifest list sha256:155548a7b0a94a6e268612cfb89bfc988480ca9c3b4ada3b7afe591a669a1fd6 done
#11 naming to docker.io/library/omi-memory-supabase-omi-memory-supabase-web:latest done
#11 unpacking to docker.io/library/omi-memory-supabase-omi-memory-supabase-web:latest 0.0s done
#11 DONE 0.1s

#12 resolving provenance for metadata file
#12 DONE 0.0s
 Image omi-memory-supabase-omi-memory-supabase-web Built
time="2026-05-16T07:53:39-06:00" level=warning msg="Found orphan containers ([omi-memory-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-memory-supabase-web Creating
 Container omi-memory-supabase-web Created
 Container omi-memory-supabase-web Starting
 Container omi-memory-supabase-web Started
 Volume omi-memory-supabase_n8n_data Creating
 Volume omi-memory-supabase_n8n_data Created
time="2026-05-16T07:53:39-06:00" level=warning msg="Found orphan containers ([omi-memory-supabase-web omi-memory-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-memory-supabase-n8n Creating
 Container omi-memory-supabase-n8n Created
 Container omi-memory-supabase-n8n Starting
 Container omi-memory-supabase-n8n Started
Containers:
omi-memory-supabase-n8n	Up Less than a second	0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp
omi-memory-supabase-web	Up Less than a second	0.0.0.0:8097->8097/tcp, [::]:8097->8097/tcp
omi-memory-supabase-test-db	Up 4 seconds (health: starting)	0.0.0.0:55432->5432/tcp, [::]:55432->5432/tcp

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

 Container omi-memory-supabase-web Stopping
 Container omi-memory-supabase-web Stopped
 Container omi-memory-supabase-web Removing
 Container omi-memory-supabase-web Removed
 Container omi-memory-supabase-test-db Stopping
 Container omi-memory-supabase-n8n Stopping
 Container omi-memory-supabase-test-db Stopped
 Container omi-memory-supabase-test-db Removing
 Container omi-memory-supabase-test-db Removed
 Container omi-memory-supabase-n8n Stopped
 Container omi-memory-supabase-n8n Removing
 Container omi-memory-supabase-n8n Removed
 Image omi-memory-supabase-omi-memory-supabase-web:latest Removing
 Network omi-memory-supabase_default Removing
 Image omi-memory-supabase-omi-memory-supabase-web:latest Removed
 Network omi-memory-supabase_default Removed
 Volume omi-memory-supabase_n8n_data Removing
 Volume omi-memory-supabase_n8n_data Removed
Uninstall complete. Only the pulled repository files should remain.
- PASS: uninstall completed
- PASS: no project containers remain
- PASS: no project volumes remain
- PASS: generated env removed

## Result

- Passed checks: 18
- Failed checks: 0
- Test completed: 2026-05-16T13:53:46+00:00

**Overall result: PASS**
