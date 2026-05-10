# OMI-Supabase

> **Proof of Concept:** This project is an open-source POC made available to the world as a working starting point for Omi + n8n + Supabase/Postgres memory management. It is not a polished product, security-audited service, or turnkey SaaS. Review the code, secure your deployment, and treat personal memory data with care.

OMI-Supabase is a self-hosted memory management system for [Omi](https://www.omi.me/) memories and webhook events.

It combines:

- **Postgres / Supabase-style database schema** for raw Omi events, review candidates, approved memories, sync jobs, audit records, and trash/restore lifecycle.
- **n8n workflow exports** for Omi webhook intake and candidate extraction.
- **FastAPI review UI** for reviewing memories, editing tags/visibility/sensitivity, submitting corrected memories back to Omi, trashing/restoring memories, and creating new memories from scratch.

The project is designed so Omi captures are treated as *evidence*, not automatic truth. Memories are reviewed before they become durable local memory or get synced back to Omi.

---

## Screenshots

### Review queue

![OMI-Supabase review queue](docs/assets/screenshots/review-queue.png)

### Create a new memory

![OMI-Supabase new memory form](docs/assets/screenshots/new-memory.png)

---

## Architecture

```mermaid
flowchart LR
  Omi[Omi pendant / Omi API] -->|webhooks| N8N[n8n workflows]
  Omi -->|Developer API pull| UI[FastAPI review UI]
  N8N -->|raw events| DB[(Postgres / Supabase schema)]
  DB -->|unreviewed candidates| UI
  UI -->|approve / edit / trash / restore| DB
  UI -->|create replacement memory| Omi
  UI -->|delete superseded or trashed memory| Omi

  subgraph PMH[Personal Memory Hub schema]
    DB --> Raw[pmh.raw_events]
    DB --> Candidates[pmh.memory_candidates]
    DB --> Approved[pmh.approved_memories]
    DB --> Sync[pmh.sync_jobs]
    DB --> Audit[pmh.review_actions / audit]
  end
```

---

## What this system does

### Ingest Omi data

Included n8n workflows receive Omi webhook payloads and insert raw events into Postgres:

- Raw Omi intake
- Conversation events
- Real-time transcript events
- Day summaries
- Audio byte metadata

### Create review candidates

A candidate extractor workflow turns raw Omi events into memory candidates for review.

### Review and manage memories

The web UI supports:

- Review queue for candidate memories
- Approve / correct / reject workflows
- Primary approved memory browser
- Tag registry with checkbox tag editing
- Local sensitivity labels: `low`, `normal`, `sensitive`, `restricted`
- Omi visibility labels: `private`, `public`
- Retrieve more unsynced Omi memories from the Omi Developer API
- Create new memories from scratch
- Submission queue for memories waiting to be sent to Omi
- Trash bin with restore

### Sync back to Omi safely

When submitting an edited memory back to Omi, the app uses a safe replacement pattern:

1. Create a new Omi memory using POST-supported fields.
2. Store the new Omi memory ID locally.
3. Delete the superseded Omi memory only after the new one is created.
4. Preserve an audit trail.

When a memory is moved to trash, the app deletes the active Omi memory if its Omi ID is known. If restored, it queues a brand-new Omi memory creation instead of reusing the deleted ID.

---

## Repository layout

```text
.
├── docs/
│   ├── importGuide.md
│   └── testing.md
├── scripts/
│   └── validate_package.sh
├── supabase/
│   └── sql/
│       └── 001_omi_supabase_complete_setup.sql
├── website/
│   ├── docker-compose.test-postgres.yml
│   ├── docker-compose.website.yml
│   └── pocReviewUi/
│       ├── .env.example
│       ├── Dockerfile
│       ├── app.py
│       └── requirements.txt
├── workflows/
│   ├── omi-supabase-pmh-candidate-extractor-poc.workflow.json
│   ├── omi-supabase-pmh-omi-audio-bytes.workflow.json
│   ├── omi-supabase-pmh-omi-conversation-events.workflow.json
│   ├── omi-supabase-pmh-omi-day-summary.workflow.json
│   ├── omi-supabase-pmh-omi-raw-intake.workflow.json
│   └── omi-supabase-pmh-omi-real-time-transcript.workflow.json
└── workflow-manifest.json
```

---

## Prerequisites

A clean Linux server or VM is enough. The examples below assume Ubuntu 24.04 or Debian 12.

You need:

- Docker Engine
- Docker Compose plugin
- Git
- An Omi Developer API key
- A DNS name or server IP for accessing the web UI and n8n

Optional but recommended:

- A reverse proxy with TLS, such as Caddy, Nginx Proxy Manager, Traefik, or Nginx
- A real Supabase project instead of plain Postgres, if you want Supabase Studio/API features

---


## Installer

The repo includes a simple installer for local/self-hosted deployments.

```bash
./install.sh install
```

The installer will:

1. Check for Docker and Docker Compose.
2. Create `website/pocReviewUi/.env` if it does not exist.
3. Start the local Postgres database.
4. Apply the complete PMH schema SQL.
5. Build and start the web UI on port `8097`.

Open:

```text
http://SERVER_IP:8097/review
```

### Non-interactive install

For scripts or quick evaluation:

```bash
./install.sh install --non-interactive
```

This generates a local UI password and leaves `OMI_API_KEY` blank. Edit `website/pocReviewUi/.env` afterward before using Omi API retrieve/submit features.

### Include local n8n

To also start a local n8n container on port `5678`:

```bash
./install.sh install --with-n8n
```

Open n8n at:

```text
http://SERVER_IP:5678
```

Then import the workflow JSON files from `workflows/`.

### Start, stop, and status

```bash
./install.sh status
./install.sh stop --with-n8n
./install.sh start --with-n8n
```

`stop` keeps containers/data available for later restart.

### Cleanup / uninstall

If you decide to remove the installed stack:

```bash
./install.sh uninstall
```

For non-interactive cleanup:

```bash
./install.sh uninstall --yes
```

The cleanup removes OMI-Supabase containers, Docker volumes, Docker networks, locally-built images, and the generated `website/pocReviewUi/.env` file. The pulled repository remains, but the installed runtime stack and local database data are removed.

If you want to keep your `.env` file:

```bash
./install.sh uninstall --yes --keep-env
```

---

## Quick start on a clean Linux install

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git ufw
```

### 2. Install Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$VERSION_CODENAME" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in, or run:

```bash
newgrp docker
```

Verify:

```bash
docker --version
docker compose version
```

### 3. Clone this repository

```bash
git clone https://github.com/GeekTheGreyBeard/OMI-Supabase.git
cd OMI-Supabase
```

### 4. Start a local Postgres database

For a simple self-hosted setup, start the included Postgres test database. Despite the filename, it is suitable for local evaluation and small private deployments if you add persistent backups.

```bash
cd website
docker compose -f docker-compose.test-postgres.yml up -d
```

Wait until Postgres is healthy:

```bash
docker exec omi-supabase-test-db pg_isready -U postgres -d postgres
```

### 5. Apply the database schema

```bash
docker exec -i omi-supabase-test-db \
  psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  < ../supabase/sql/001_omi_supabase_complete_setup.sql
```

Verify basic setup:

```bash
docker exec omi-supabase-test-db psql -U postgres -d postgres -Atc \
  "select 'source_systems=' || count(*) from pmh.source_systems union all select 'pmh_tables=' || count(*) from information_schema.tables where table_schema='pmh';"
```

Expected output includes:

```text
source_systems=5
pmh_tables=14
```

### 6. Configure the web UI

```bash
cd pocReviewUi
cp .env.example .env
nano .env
```

Set values like:

```env
DATABASE_URL=postgresql://postgres:postgres@omi-supabase-test-db:5432/postgres
PMH_UI_USER=admin
PMH_UI_PASSWORD=choose-a-strong-password
OMI_API_BASE=https://api.omi.me
OMI_API_KEY=your-omi-developer-api-key
```

Do **not** commit `.env`.

### 7. Run the web UI

From the `website/` directory:

```bash
cd ..
docker compose -f docker-compose.website.yml up -d --build
```

Open:

```text
http://SERVER_IP:8097/review
```

Use the Basic Auth username/password from `.env`.

### 8. Validate the package

From the repo root:

```bash
./scripts/validate_package.sh
```

This checks that the web app compiles and that all workflow exports are valid inactive n8n workflows.

---

## n8n setup

The repository includes workflow exports but does not install n8n for you. You can run n8n on the same server or another server.

### Minimal n8n Docker Compose example

Create a directory outside this repo, such as `/opt/n8n`, and add:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=your-domain-or-ip
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://your-domain-or-ip:5678/
      - GENERIC_TIMEZONE=UTC
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

Start it:

```bash
docker compose up -d
```

Open:

```text
http://SERVER_IP:5678
```

For production, put n8n behind HTTPS and set `WEBHOOK_URL` to the public HTTPS URL.

### Import workflows

In n8n:

1. Create a folder named `OMI-Supabase`.
2. Import each JSON file from `workflows/`.
3. Keep workflows inactive until credentials and webhook URLs are correct.
4. Create or map the Postgres credential used by the workflows.
5. Update node credentials if n8n asks for them after import.
6. Activate only the workflows you are ready to receive events for.

Included workflow exports are intentionally inactive to prevent webhook collisions.

### Recommended activation order

1. `OMI-Supabase - PMH Omi Raw Intake`
2. `OMI-Supabase - PMH Omi Conversation Events`
3. `OMI-Supabase - PMH Omi Real-time Transcript`
4. `OMI-Supabase - PMH Omi Day Summary`
5. `OMI-Supabase - PMH Omi Audio Bytes`, if you want audio metadata intake
6. `OMI-Supabase - PMH Candidate Extractor POC`

---

## Omi setup

In the Omi developer/app configuration:

1. Create or open your Omi app/integration.
2. Set webhook URLs to the matching n8n production webhook URLs.
3. Use the n8n workflow webhook paths shown after each workflow is imported.
4. Store your Omi Developer API key only in the web UI environment or a secret manager.

Do not place Omi API keys in workflow JSON, Git, or documentation.

---

## Database options

### Option A: Plain Postgres

The included SQL works with standard Postgres 16 using `pgcrypto`.

This is the fastest path to a working private system.

### Option B: Supabase-hosted database

Create a Supabase project, then apply:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/sql/001_omi_supabase_complete_setup.sql
```

Use the Supabase connection string as `DATABASE_URL` for the web UI and as the Postgres credential in n8n.

### Option C: Full self-hosted Supabase

You can use the official Supabase self-hosting stack, then apply the same SQL to the Postgres database. This is heavier than the plain Postgres path and is not required for the memory-management UI to work.

---

## Security notes

- Keep this service private unless you add stronger authentication and HTTPS.
- The web UI uses Basic Auth as a simple first gate.
- Omi memories may contain sensitive personal data.
- Sensitive and restricted memories are not recall-eligible by default.
- Trash/delete actions can delete remote Omi memories when an active Omi ID is known.
- Restore creates a new Omi memory instead of reviving old deleted IDs.
- Never commit `.env`, API keys, database passwords, or exported n8n credentials.

---

## Backups

At minimum, back up Postgres:

```bash
docker exec omi-supabase-test-db pg_dump -U postgres -d postgres > omi-supabase-backup.sql
```

Restore example:

```bash
docker exec -i omi-supabase-test-db psql -U postgres -d postgres < omi-supabase-backup.sql
```

For production, automate backups and test restores regularly.

---

## Development notes

### README screenshots and diagrams

Project screenshots should live under `docs/assets/screenshots/` and be referenced with relative Markdown image paths. Mermaid diagrams can be embedded directly in Markdown using fenced `mermaid` blocks, as shown above.

For repeatable screenshots, use a clean local/disposable database so screenshots do not expose private memory data.

Run static validation:

```bash
./scripts/validate_package.sh
```

Run a local disposable database:

```bash
cd website
docker compose -f docker-compose.test-postgres.yml up -d
```

Stop and remove disposable database data:

```bash
docker compose -f docker-compose.test-postgres.yml down -v
```

---

## Current limitations

- n8n workflows are exported with credential references but no credential secrets.
- The web UI is a practical POC-style app, not a polished multi-user product.
- Basic Auth should be replaced or fronted by SSO before broader exposure.
- Audio byte handling is metadata-first; raw audio retention requires a deliberate storage and privacy policy.

---

## License

This project is released under the [MIT License](LICENSE).
