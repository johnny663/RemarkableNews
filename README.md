# RemarkableNews

Daily e-newspapers for the reMarkable Paper Pro Move. Every morning it fetches:

| Paper | What you get | Source |
|---|---|---|
| **New York Times** | Print front-page scan | NYT's free public daily scan |
| **NYT International Edition** | Print front page (Mon–Sat) | NYT's free public daily scan |
| **Daily Press** | The **whole e-edition**, every page | Public PageSuite CDN, resolved headlessly |

Each PDF is rescaled to the Move's screen aspect and uploaded to the `reMarkableNews` folder in OneDrive, which the tablet syncs via its OneDrive integration. Papers older than 2 days are cleaned up automatically.

The NYT full paper is subscriber-only; this fetches only its freely published front pages. Every source is best-effort — one paper being unavailable doesn't stop the others.

---

## Setup

The only credential needed is an Azure app Client ID for OneDrive access.

### 1. Register an Azure app (one time)

1. Go to [portal.azure.com](https://portal.azure.com) and sign in with the **same Microsoft account** your OneDrive is on.
2. **App registrations** → **New registration**; any name; **Personal Microsoft accounts only**; Register.
3. Copy the **Application (client) ID** — this is your `AZURE_CLIENT_ID`.
4. **Authentication** → **Add a platform** → **Mobile and desktop applications** → check `https://login.microsoftonline.com/common/oauth2/nativeclient` → Configure.
5. Still under Authentication, toggle **Allow public client flows** to **Yes**. Save.
6. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → `Files.ReadWrite` → Add.

No client secret is needed.

### 2. Run once locally to log in

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env      # fill in AZURE_CLIENT_ID
python main.py
```

The first run prints a URL and code — sign in once in a browser. The token is saved to `~/.remarkableNews/token_cache.json` and refreshes silently afterwards.

### 3. Schedule it (GitHub Actions)

The included workflow (`.github/workflows/daily.yml`) runs twice daily, scheduled at **7:23 and 7:53 UTC**. GitHub Actions cron is best-effort and routinely runs 2–4 hours late, so these early slots are chosen deliberately: after typical drift the papers land around **5am US Eastern**. If your timing needs differ, edit the `cron` lines in the workflow (remember GitHub cron is UTC and doesn't follow DST).

Add two repository secrets (**Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | Your Azure app client ID |
| `MSAL_TOKEN_CACHE` | Contents of `~/.remarkableNews/token_cache.json` from step 2 |

The workflow keeps the rotating OneDrive token alive across runs via the Actions cache; the secret only seeds the first run.

---

## Email delivery (optional)

The pipeline can also send one email each morning with OneDrive links to the day's papers (links, not attachments — so even the large Daily Press e-edition is included, with no size limits).

1. **Paste recipient addresses into `recipients.txt`** — one per line (`#` lines are ignored). No recipients = no email, silently skipped.
2. **Set the SMTP settings** in `.env` (locally) or as repository secrets (for Actions): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` (optional `SMTP_FROM` if your provider's username isn't an email address). For Gmail, use `smtp.gmail.com` with an [App Password](https://myaccount.google.com/apppasswords) — your normal password won't work.

The links are anonymous view links — anyone who has one can open that PDF. Email is best-effort: a mail failure never fails the run, since the papers are already on OneDrive.

> Note: if this repo is public, addresses in `recipients.txt` are publicly visible. Keep the repo private or use addresses you don't mind exposing.

---

## reMarkable setup

On your tablet, open **Settings → Integrations** and connect your OneDrive account, then browse to the `reMarkableNews` folder. The morning's papers appear there after the workflow runs.

---

## Architecture

| File | Responsibility |
|---|---|
| `main.py` | Orchestrator — fetch each paper (best-effort), resize, upload, prune |
| `nyt_frontpage.py` | NYT US + International front-page scans from their date-keyed public URLs, 1-day lookback |
| `dailypress_client.py` | Resolves the latest Daily Press edition GUID with headless Chromium, downloads the whole-paper PDF |
| `pdf_utils.py` | Rescales any PDF to the Move's page size, centered, no cropping |
| `onedrive_client.py` | MSAL device-code auth + Graph upload + age-based cleanup |
| `check_drive.py` | Diagnostic — prints OneDrive quota + a test-upload error body |
