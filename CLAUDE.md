# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this does

Daily Python script: fetches news from **two sources** → builds one paginated PDF digest → uploads to `reMarkableNews/` in OneDrive → deletes digests older than 2 days. The reMarkable tablet imports that folder via its OneDrive integration.

**Two content sources, combined into one PDF (NewsData first, Guardian after):**
- **NewsData.io** — summaries from many outlets. Full text is **paid-only** (`full_content=1` → 422 on free); free tier returns the `description`. `prioritydomain=top` filters out press-release spam.
- **The Guardian Open Platform** — returns **complete article bodies for free** (`show-fields=bodyText`). Single publisher, but real full text.

Each `Article` carries an `is_full` flag and a `source`; summary-only articles are marked in the PDF. We moved off the NYT API because it only ever exposes abstracts. Guardian is optional — if `GUARDIAN_API_KEY` is unset, the run skips it gracefully.

**PDF is tuned for the reMarkable Paper Pro Move:** page size matches the Move's ~954×1696 screen aspect (`PAGE_SIZE` in `pdf_builder.py`), and the cover is a clickable summary list — each entry is an internal PDF link (`<a href="#articleN">`) that jumps to that article's page on the device. Switch `PAGE_SIZE` to `LETTER` for larger tablets.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in both keys
```

**Credentials needed (`.env`):**

1. **NewsData.io API key** — [newsdata.io](https://newsdata.io) → Dashboard → API Key (paid plan needed for full article text)
2. **Guardian API key** — [open-platform.theguardian.com/access](https://open-platform.theguardian.com/access/) (free, instant; returns full article text)
3. **Azure Client ID** — register a public client app in [portal.azure.com](https://portal.azure.com):
   - App registrations → New → set "Supported account types" to personal Microsoft accounts
   - Authentication → Add platform → Mobile/desktop → enable `https://login.microsoftonline.com/common/oauth2/nativeclient`
   - Toggle "Allow public client flows" to Yes
   - No client secret needed (public client / device code flow)
   - API permissions: `Files.ReadWrite` (delegated, Microsoft Graph)

## Running

```bash
# First run: opens a browser auth prompt once, caches the token
python main.py

# Subsequent runs are silent (token auto-refreshed from ~/.remarkableNews/token_cache.json)
```

## Scheduling

**Local cron (only runs while the laptop is awake):**
```bash
crontab -e
0 6 * * * cd /path/to/remarkableNews && /path/to/.venv/bin/python main.py >> /tmp/remarkableNews.log 2>&1
```

**Cloud (runs regardless of your laptop) — GitHub Actions, `.github/workflows/daily.yml`:**
- Free; ~2,000 min/month on private repos (this job uses ~60), unlimited on public.
- Repo secrets required: `GUARDIAN_API_KEY`, `NEWSDATA_API_KEY`, `AZURE_CLIENT_ID`, and `MSAL_TOKEN_CACHE` (the contents of your local `~/.remarkableNews/token_cache.json`).
- **OneDrive token persistence:** the refresh token rotates on each use, so a static secret can't be reused forever. The workflow restores the newest token cache via `actions/cache` (unique key + `restore-keys` prefix), runs, and saves the rotated cache back. `MSAL_TOKEN_CACHE` only seeds the *first* run.
- Caveats: scheduled runs drift 5–30+ min; GitHub disables the schedule after 60 days with no commits; if the job fails 7+ days straight the Actions cache is evicted and you re-seed from the secret.

## Architecture

| File | Responsibility |
|------|---------------|
| `main.py` | Orchestrator — fetches NewsData (first) + Guardian (after), builds PDF, uploads, prunes old files |
| `models.py` | Shared `Article` dataclass (`is_full`, `source`) used by both clients and the PDF builder |
| `newsdata_client.py` | `newsdata.io/api/1/latest`, `prioritydomain=top`, paginates; `full_content` opt-in (paid) |
| `guardian_client.py` | `content.guardianapis.com/search` with `show-fields=bodyText` — full text, free |
| `pdf_builder.py` | `reportlab` PDF: Move-sized pages, clickable summary cover, one article per page, footer |
| `onedrive_client.py` | MSAL device-code auth + Graph upload + `delete_old_pdfs` cleanup |
| `nyt_client.py` | Unused legacy NYT client, kept as an alternate source |
| `check_drive.py` | Diagnostic — prints OneDrive quota + a test-upload error body (see `diagnose-onedrive` skill) |

**Auth flow:** First run triggers MSAL device code flow (user visits a URL, logs in once). The refresh token is serialized to `~/.remarkableNews/token_cache.json` and reused silently on all future runs. Microsoft personal account refresh tokens are valid for 90 days of inactivity.

**Cleanup:** `delete_old_pdfs` lists the folder and removes files matching `news-YYYY-MM-DD.pdf` older than `KEEP_DAYS` (2). It only touches that exact name pattern, so other files in the folder are safe.

**OneDrive path:** Files land at `reMarkableNews/{filename}` at the OneDrive root. Avoid the special `Apps/` folder — Graph returns a spurious 507 when writing arbitrary paths under it. The reMarkable tablet imports from OneDrive via its Integrations feature (Settings → connect OneDrive, then browse to the folder).
