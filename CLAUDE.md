# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this does

Daily Python script: fetches **three e-newspapers** → rescales each to the reMarkable Move screen → uploads to `reMarkableNews/` in OneDrive → deletes papers older than 2 days. The reMarkable tablet imports that folder via its OneDrive integration.

**Three papers, each a separate PDF (all best-effort — one failing doesn't stop the others; the run only fails if nothing uploads):**
- **NYT (US edition)** — free public front-page scan at a date-keyed `static01.nyt.com` URL.
- **NYT International Edition** — same mechanism, different path (`INYT_frontpage_global.YYYYMMDD.pdf`); no Sunday paper.
- **Daily Press** — the **whole e-edition** as one multi-page PDF. The PageSuite reader's content is public on the CDN, but the "today → edition GUID" index is auth-gated, so headless Chromium loads the public reader and sniffs the first CDN request to recover the GUIDs.

The NYT full paper is subscriber-only; only its freely published front pages are fetched. The article-digest pipeline (NewsData.io + Guardian → reportlab PDF) was retired; `RemarkableNewsFable` is the sibling repo experimenting with the papers-only concept.

**PDF sizing:** every page is scaled to fit the Move's ~954×1696 screen aspect (`PAGE_SIZE` in `pdf_utils.py`), centered, no cropping.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env   # fill in AZURE_CLIENT_ID
```

**The only credential is an Azure Client ID** — register a public client app in [portal.azure.com](https://portal.azure.com):
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

## Scheduling — GitHub Actions (`.github/workflows/daily.yml`)

- Crons at 7:23 and 7:53 UTC — deliberately early with off-hour minutes, because scheduled runs drift 2.5–4h under load; after drift they land ~5am US Eastern.
- A `concurrency` group serializes runs: each run restores and *rotates* the OneDrive refresh token via the Actions cache, so overlapping runs would rotate it out from under each other.
- Repo secrets required: `AZURE_CLIENT_ID` and `MSAL_TOKEN_CACHE` (the contents of your local `~/.remarkableNews/token_cache.json`).
- **OneDrive token persistence:** the refresh token rotates on each use, so a static secret can't be reused forever. The workflow restores the newest token cache via `actions/cache` (unique key + `restore-keys` prefix), runs, and saves the rotated cache back. `MSAL_TOKEN_CACHE` only seeds the *first* run; a seed step self-heals if the restored cache is corrupt.
- Caveats: GitHub disables the schedule after 60 days with no commits; if the job fails 7+ days straight the Actions cache is evicted and you re-seed from the secret.

## Architecture

| File | Responsibility |
|------|---------------|
| `main.py` | Orchestrator — fetches each paper (best-effort), resizes, uploads, prunes old files |
| `nyt_frontpage.py` | US + International front-page scans; shared date-keyed fetcher with 1-day lookback |
| `dailypress_client.py` | Headless Chromium resolves the latest edition GUIDs, then downloads `edition.pdf` |
| `pdf_utils.py` | `resize_pdf_to_move` — rescales any PDF to the Move page size (pypdf) |
| `onedrive_client.py` | MSAL device-code auth + Graph upload + `delete_old_pdfs` cleanup |
| `check_drive.py` | Diagnostic — prints OneDrive quota + a test-upload error body (see `diagnose-onedrive` skill) |

**Auth flow:** First run triggers MSAL device code flow (user visits a URL, logs in once). The refresh token is serialized to `~/.remarkableNews/token_cache.json` and reused silently on all future runs. Microsoft personal account refresh tokens are valid for 90 days of inactivity.

**Cleanup:** `delete_old_pdfs` lists the folder and removes files matching `nyt-frontpage-`, `nyt-intl-frontpage-`, `dailypress-` (and legacy `news-`) `YYYY-MM-DD.pdf` names older than `KEEP_DAYS` (2). It only touches those exact patterns, so other files in the folder are safe.

**OneDrive path:** Files land at `reMarkableNews/{filename}` at the OneDrive root. Avoid the special `Apps/` folder — Graph returns a spurious 507 when writing arbitrary paths under it. The reMarkable tablet imports from OneDrive via its Integrations feature (Settings → Integrations → connect OneDrive, then browse to the folder).
