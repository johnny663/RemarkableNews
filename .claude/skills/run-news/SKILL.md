---
name: run-news
description: Run the daily e-newspapers → OneDrive pipeline for this project. Use when the user wants to fetch today's papers (NYT front pages, Daily Press e-edition) or push them to their reMarkable.
---

# Run the papers pipeline

Runs `main.py`, which fetches the NYT US and International front pages and the whole Daily Press e-edition, rescales each PDF to the reMarkable Move screen, and uploads them to the `reMarkableNews` folder in OneDrive.

## Steps

1. Make sure the venv is active, Chromium is installed for Playwright, and `.env` has `AZURE_CLIENT_ID`:
   ```bash
   source .venv/bin/activate
   python -m playwright install chromium   # first time only
   ```
2. Run it:
   ```bash
   python3 main.py
   ```
3. Expected output: per-paper fetch → resize → upload confirmations, then `N/3 papers uploaded.`

## If it fails

- **Auth prompt appears** (`microsoft.com/link` code) — only happens on first run or after the token cache is cleared. The user must open the URL and log in.
- **`507 Insufficient Storage`** — invoke the `diagnose-onedrive` skill.
- **Missing `AZURE_CLIENT_ID`** — the script exits early; check `.env`.
- **One paper skipped** — normal; every source is best-effort (NYT scans post late some mornings, INYT has no Sunday paper). The run only fails if *nothing* uploads.

Output files: `nyt-frontpage-YYYY-MM-DD.pdf`, `nyt-intl-frontpage-YYYY-MM-DD.pdf`, `dailypress-YYYY-MM-DD.pdf`. Re-running on the same day overwrites them.
