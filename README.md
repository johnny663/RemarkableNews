# RemarkableNews

Fetches daily news from Guardian and NewsData.io, builds a reMarkable-sized PDF digest, and uploads it to OneDrive so your reMarkable tablet can sync it automatically.

---

## What you need

| Credential | Where to get it |
|---|---|
| Guardian API key | [open-platform.theguardian.com/access](https://open-platform.theguardian.com/access/) — free, instant |
| NewsData.io API key | [newsdata.io](https://newsdata.io) → Dashboard → API Key |
| Azure Client ID | See OneDrive setup below |

---

## OneDrive setup

OneDrive access requires a one-time Azure app registration and a one-time login on your machine. After that, the token refreshes automatically.

### 1. Register an Azure app (one time)

1. Go to [portal.azure.com](https://portal.azure.com) and sign in with the **same Microsoft account** your OneDrive is on.
2. Search for **App registrations** → **New registration**.
3. Give it any name (e.g. `RemarkableNews`).
4. Under **Supported account types**, select **Personal Microsoft accounts only**.
5. Click **Register**.
6. Copy the **Application (client) ID** — this is your `AZURE_CLIENT_ID`.
7. Go to **Authentication** → **Add a platform** → **Mobile and desktop applications**.
8. Check the box for `https://login.microsoftonline.com/common/oauth2/nativeclient` and click **Configure**.
9. On the same Authentication page, scroll down and toggle **Allow public client flows** to **Yes**. Save.
10. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → search for `Files.ReadWrite` → Add.

You do **not** need a client secret.

### 2. Add your credentials to `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```
GUARDIAN_API_KEY=your_guardian_key
NEWSDATA_API_KEY=your_newsdata_key
AZURE_CLIENT_ID=your_azure_client_id   # from step 6 above
```

### 3. Run once to log in

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The first run will print a URL and a code. Open the URL in a browser, enter the code, and sign in with your Microsoft account. After that, your token is saved to `~/.remarkableNews/token_cache.json` and all future runs are silent.

---

## Running on a schedule (GitHub Actions)

The included workflow (`.github/workflows/daily.yml`) runs at **5:00am and 5:30am EDT** daily for free.

### Required GitHub secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** and add:

| Secret name | Value |
|---|---|
| `GUARDIAN_API_KEY` | Your Guardian API key |
| `NEWSDATA_API_KEY` | Your NewsData.io API key |
| `AZURE_CLIENT_ID` | Your Azure app client ID |
| `MSAL_TOKEN_CACHE` | Contents of `~/.remarkableNews/token_cache.json` (generated after your first local run) |

`MSAL_TOKEN_CACHE` is the most important one — it seeds OneDrive auth in CI. After the first successful run, the workflow keeps the token refreshed automatically via the Actions cache.

---

## reMarkable setup

On your tablet: **Settings → Storage → OneDrive** → connect your account → navigate to the `reMarkableNews` folder. New PDFs appear there each morning after the workflow runs.
