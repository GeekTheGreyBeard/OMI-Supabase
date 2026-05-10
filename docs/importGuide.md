# OMI-Supabase Import Guide

## n8n

Create a folder named `OMI-Supabase` in the target n8n instance and import the workflow JSON files from `workflows/`.

Keep imported workflows inactive until credentials and webhook paths are reviewed.

Expected credentials/connection references:

- Postgres/Supabase database credential targeting the PMH database.
- Any Omi webhook/API credential required by the deployment.

Recommended activation order:

1. Raw Intake
2. Conversation Events
3. Real-time Transcript
4. Day Summary
5. Audio Bytes, if metadata retention is desired
6. Candidate Extractor POC

Do not import or activate the old Review Action Router for public use. Review actions belong behind the authenticated website.

## Supabase/Postgres

Apply:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/sql/001_omi_supabase_complete_setup.sql
```

The script creates schema `pmh`, review lifecycle tables, source systems, sync jobs, audit tables, audio/transcription metadata, approved memories, tag registry, views, and review function.

## Website

```bash
cd website/pocReviewUi
cp .env.example .env
# Fill DATABASE_URL, PMH_UI_USER, PMH_UI_PASSWORD, OMI_API_KEY.
cd ..
docker compose -f docker-compose.website.yml up -d --build
```

Default exposed port: `8097`.

## Safety defaults

- Omi workflow exports are inactive.
- Website requires Basic Auth.
- Sensitive/restricted memories are recall-ineligible by default.
- Trash deletes active Omi memory if known; restore queues creation of a new Omi memory rather than reusing old IDs.
