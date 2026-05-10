# OMI-Supabase install test

- Test host: omi-supabase-install-test
- Test started: 2026-05-10T23:04:50+00:00
- Repository: https://github.com/GeekTheGreyBeard/OMI-Supabase.git
- Branch: main

Cloning into '/home/gtgb/omi-supabase-retest-20260510/OMI-Supabase'...
- Commit: 3a94b8b Add Omi memory cockpit home page

## Static validation

workflow_exports_ok 6
package_validation_ok
- PASS: static package validation

## Install

Created /home/gtgb/omi-supabase-retest-20260510/OMI-Supabase/website/pocReviewUi/.env
Note: OMI_API_KEY is blank. Add it to /home/gtgb/omi-supabase-retest-20260510/OMI-Supabase/website/pocReviewUi/.env before using Omi API submit/retrieve features.
 Network omi-supabase_default  Creating
 Network omi-supabase_default  Created
 Container omi-supabase-test-db  Creating
 Container omi-supabase-test-db  Created
 Container omi-supabase-test-db  Starting
 Container omi-supabase-test-db  Started
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
time="2026-05-10T23:05:02Z" level=warning msg="Docker Compose is configured to build using Bake, but buildx isn't installed"
#0 building with "default" instance using docker driver

#1 [omi-supabase-web internal] load build definition from Dockerfile
#1 transferring dockerfile:
#1 transferring dockerfile: 344B done
#1 DONE 0.4s

#2 [omi-supabase-web internal] load metadata for docker.io/library/python:3.12-slim
#2 DONE 0.2s

#3 [omi-supabase-web internal] load .dockerignore
#3 transferring context: 2B done
#3 DONE 0.1s

#4 [omi-supabase-web internal] load build context
#4 transferring context: 67.30kB 0.0s done
#4 DONE 0.2s

#5 [omi-supabase-web 1/5] FROM docker.io/library/python:3.12-slim@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe
#5 resolve docker.io/library/python:3.12-slim@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe
#5 resolve docker.io/library/python:3.12-slim@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe 0.2s done
#5 DONE 0.3s

#6 [omi-supabase-web 4/5] RUN pip install --no-cache-dir -r /app/requirements.txt
#6 CACHED

#7 [omi-supabase-web 2/5] WORKDIR /app
#7 CACHED

#8 [omi-supabase-web 3/5] COPY requirements.txt /app/requirements.txt
#8 CACHED

#9 [omi-supabase-web 5/5] COPY app.py /app/app.py
#9 CACHED

#10 [omi-supabase-web] exporting to image
#10 exporting layers done
#10 exporting manifest sha256:58b536064364e31dc90754f85b34eb20fd1cdbe868cae04e0be794f09622919c 0.1s done
#10 exporting config sha256:e3d9552582750f8bc25f0d31aec1e40bb0daa8fa70cfc880cc87012787b8f4bf
#10 exporting config sha256:e3d9552582750f8bc25f0d31aec1e40bb0daa8fa70cfc880cc87012787b8f4bf 0.1s done
#10 exporting attestation manifest sha256:e684a0b961808ea1a508871522b25ac04a4e15cb3bf93cc30f700a6c70fb8407
#10 exporting attestation manifest sha256:e684a0b961808ea1a508871522b25ac04a4e15cb3bf93cc30f700a6c70fb8407 0.4s done
#10 exporting manifest list sha256:097141eb69643affedb0ae00081d27309e7576c4836522e38d065c4067c87731
#10 exporting manifest list sha256:097141eb69643affedb0ae00081d27309e7576c4836522e38d065c4067c87731 0.3s done
#10 naming to docker.io/library/omi-supabase-omi-supabase-web:latest
#10 naming to docker.io/library/omi-supabase-omi-supabase-web:latest 0.0s done
#10 unpacking to docker.io/library/omi-supabase-omi-supabase-web:latest
#10 unpacking to docker.io/library/omi-supabase-omi-supabase-web:latest 1.7s done
#10 DONE 2.9s

#11 [omi-supabase-web] resolving provenance for metadata file
#11 DONE 0.0s
 omi-supabase-web  Built
time="2026-05-10T23:05:09Z" level=warning msg="Found orphan containers ([omi-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-supabase-web  Creating
 Container omi-supabase-web  Created
 Container omi-supabase-web  Starting
 Container omi-supabase-web  Started
 Volume omi-supabase_n8n_data  Creating
 Volume omi-supabase_n8n_data  Created
time="2026-05-10T23:05:11Z" level=warning msg="Found orphan containers ([omi-supabase-web omi-supabase-test-db]) for this project. If you removed or renamed this service in your compose file, you can run this command with the --remove-orphans flag to clean it up."
 Container omi-supabase-n8n  Creating
 Container omi-supabase-n8n  Created
 Container omi-supabase-n8n  Starting
 Container omi-supabase-n8n  Started
Containers:
omi-supabase-n8n	Up 1 second	0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp
omi-supabase-web	Up 3 seconds	0.0.0.0:8097->8097/tcp, [::]:8097->8097/tcp
omi-supabase-test-db	Up 20 seconds (healthy)	0.0.0.0:55432->5432/tcp, [::]:55432->5432/tcp

Web UI: http://localhost:8097/review
n8n:    http://localhost:5678

Install complete.
- PASS: installer completed

## Page checks

- PASS: memory home route returns 200
- PASS: memory home contains cockpit heading
- PASS: review page contains home button
- PASS: review route returns 200
- PASS: primary memories route returns 200
- PASS: new memory route returns 200
- PASS: submissions route returns 200
- PASS: trash route returns 200
- PASS: n8n route reachable

## Uninstall

 Container omi-supabase-web  Stopping
 Container omi-supabase-web  Stopped
 Container omi-supabase-web  Removing
 Container omi-supabase-web  Removed
 Container omi-supabase-test-db  Stopping
 Container omi-supabase-n8n  Stopping
 Container omi-supabase-test-db  Stopped
 Container omi-supabase-test-db  Removing
 Container omi-supabase-test-db  Removed
 Container omi-supabase-n8n  Stopped
 Container omi-supabase-n8n  Removing
 Container omi-supabase-n8n  Removed
 Image omi-supabase-omi-supabase-web:latest  Removing
 Network omi-supabase_default  Removing
 Network omi-supabase_default  Removed
 Image omi-supabase-omi-supabase-web:latest  Removed
 Volume omi-supabase_n8n_data  Removing
 Volume omi-supabase_n8n_data  Removed
Uninstall complete. Only the pulled repository files should remain.
- PASS: uninstall completed
- PASS: no project containers remain
- PASS: no project volumes remain
- PASS: generated env removed

## Result

- Passed checks: 15
- Failed checks: 0
- Test completed: 2026-05-10T23:05:30+00:00

**Overall result: PASS**
