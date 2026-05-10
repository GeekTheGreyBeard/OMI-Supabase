# Visual Documentation

This project uses two lightweight visual documentation conventions:

1. **Screenshots** live in `docs/assets/screenshots/` and are referenced from README files with relative paths.
2. **Mermaid diagrams** are embedded directly in Markdown when a flow or architecture overview is clearer than prose.

## Screenshot capture

Screenshots in this repository were captured from a disposable local database with no personal memory data.

Recommended pattern:

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

When documenting public/open-source projects, avoid screenshots containing real names, secrets, private memories, or internal hostnames.

## Mermaid

Use Mermaid diagrams for:

- System architecture
- Data flow
- Review/approval lifecycle
- Sync and deletion behavior

Keep diagrams high-level enough to remain useful after implementation details change.
