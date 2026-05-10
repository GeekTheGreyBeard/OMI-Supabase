# OMI-Supabase

Standalone personal project for Supabase-backed Omi memory management.

This project was split out of PatriciAI `personalMemoryHub` so the Supabase/Omi path can evolve independently without collisions.

## Documentation

- Obsidian project path: `OpenClaw/Projects/OMI-Supabase/`
- Import guide: `docs/importGuide.md`
- Test notes: `docs/testing.md`

## Contents

- `workflows/` — inactive n8n workflow JSON exports for Omi/Supabase intake and candidate extraction.
- `workflow-manifest.json` — source workflow IDs and production `OMI-Supabase` folder/copy IDs.
- `supabase/sql/001_omi_supabase_complete_setup.sql` — complete setup SQL for Supabase/Postgres.
- `website/pocReviewUi/` — FastAPI review/primary/trash/submission UI.
- `website/docker-compose.website.yml` — website deployment compose.
- `website/docker-compose.test-postgres.yml` — disposable Postgres test harness.
- `scripts/validate_package.sh` — package validation helper.

## Safety

- Workflow exports are inactive by default to avoid webhook collisions.
- No real secrets are committed. Use `.env.example` as a template.
- Website requires Basic Auth.
- Review actions remain behind the authenticated website, not public webhook flows.

## GitHub status

Local repository is initialized and committed. GitHub private repo creation was attempted, but the current PatriciAI GitHub PAT lacks repository creation permission (`createRepository` blocked). Once `GeekTheGreyBeard/OMI-Supabase` exists or a PAT with create-repo permission is available, push with:

```bash
git remote add origin https://github.com/GeekTheGreyBeard/OMI-Supabase.git
git push -u origin main
```
