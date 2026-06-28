---
name: diagnose-onedrive
description: Troubleshoot OneDrive / Microsoft Graph upload failures in this project (507 Insufficient Storage, auth errors, wrong-account issues). Use when main.py fails at the upload step.
---

# Diagnose OneDrive upload failures

## First, run the diagnostic

```bash
python3 check_drive.py
```

It forces a login (if no cached token), prints the real quota + `state`, and does a 5-byte test upload that surfaces Graph's **full JSON error body** — the single most useful signal.

## Known failure modes and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `507` but folder looks empty | Personal accounts share one 5 GB pool across OneDrive + Outlook email + Photos. Email attachments / photos can fill it. | Free up the shared Microsoft storage, or the account needs a paid plan. Check `state` field — `exceeded`/`critical` confirms it. |
| `507` + `quotaLimitReached` in body | Same as above, confirmed | Same |
| `AADSTS9002346 ... Microsoft Account users only` | App registered for consumers; using `/common` authority | Use `/consumers` authority in `onedrive_client.py` (already applied) |
| `scope value that is reserved` | `offline_access` passed explicitly to MSAL | MSAL adds it automatically — keep `SCOPES = ["Files.ReadWrite"]` |
| Uploads to wrong/empty OneDrive | Logged into the wrong Microsoft account | Clear the cache and re-login: `rm -f ~/.remarkableNews/token_cache.json`, then re-run |

## Force a fresh login

```bash
rm -f ~/.remarkableNews/token_cache.json
python3 check_drive.py   # will prompt for a new device-code login
```

## Avoid

The special `Apps/` folder in OneDrive returns spurious 507s for arbitrary write paths. Keep uploads in a normal root folder (`reMarkableNews`).
