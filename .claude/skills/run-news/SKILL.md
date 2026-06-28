---
name: run-news
description: Run the daily NewsData.io → PDF → OneDrive pipeline for this project. Use when the user wants to fetch today's news, generate the digest, or push it to their reMarkable.
---

# Run the news pipeline

Runs `main.py`, which fetches news from NewsData.io, builds a paginated PDF digest (cover + TOC, one article per page), and uploads it to the `reMarkableNews` folder in OneDrive.

## Steps

1. Make sure the venv is active and `.env` has `NEWSDATA_API_KEY` and `AZURE_CLIENT_ID`:
   ```bash
   source .venv/bin/activate
   ```
2. Run it:
   ```bash
   python3 main.py
   ```
3. Expected output: article count → PDF size → upload confirmation with a `webUrl`.

## If it fails

- **Auth prompt appears** (`microsoft.com/link` code) — only happens on first run or after the token cache is cleared. The user must open the URL and log in.
- **`507 Insufficient Storage`** — invoke the `diagnose-onedrive` skill.
- **Missing keys** — the script exits early; check `.env`.

The output file is named `news-YYYY-MM-DD.pdf`. Re-running on the same day overwrites it. The run prints how many articles came back full-text vs summary-only (free NewsData.io plans return summaries only).
