# Visual Documentation

This project uses two lightweight visual documentation conventions:

1. **Screenshots** live in `docs/assets/screenshots/` and are referenced from README files with relative paths.
2. **Mermaid diagrams** are embedded directly in Markdown when a flow or architecture overview is clearer than prose.

## Screenshot capture

Screenshots in this repository were captured from disposable local services with no personal memory data. The n8n screenshots use imported public workflow exports and a throwaway local n8n owner account.

Recommended pattern for the FastAPI review UI:

```bash
SCREENSHOT_BASIC_USER='screenshot' \
SCREENSHOT_BASIC_PASSWORD='screenshot-pass' \
path/to/capture-screenshot.sh \
  --url http://127.0.0.1:8097/review \
  --out docs/assets/screenshots/review-queue.png \
  --width 1440 \
  --height 1000 \
  --full-page true
```

For n8n workflow screenshots, import the public workflow JSON files into a disposable local n8n instance and capture only the workflow list/canvas screens. Avoid execution details, credentials, environment variables, or any private run data.

When documenting public/open-source projects, avoid screenshots containing real names, secrets, private memories, internal hostnames, or private execution data.

## Mermaid

Use Mermaid diagrams for:

- System architecture
- Data flow
- Review/approval lifecycle
- Sync and deletion behavior

Keep diagrams high-level enough to remain useful after implementation details change.
