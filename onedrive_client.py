import json
import re
from datetime import date, timedelta
from pathlib import Path

import msal
import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite"]
REMARKABLE_FOLDER = "reMarkableNews"
CACHE_PATH = Path.home() / ".remarkableNews" / "token_cache.json"


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        data = CACHE_PATH.read_text()
        if data.strip():
            try:
                cache.deserialize(data)
            except ValueError:
                # Corrupt/partial cache — start fresh rather than crash.
                # A valid token still has to be seeded for headless (CI) auth.
                pass
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(cache.serialize())


def _build_app(client_id: str) -> msal.PublicClientApplication:
    cache = _load_cache()
    return msal.PublicClientApplication(
        client_id,
        authority="https://login.microsoftonline.com/consumers",
        token_cache=cache,
    )


def get_access_token(client_id: str) -> str:
    app = _build_app(client_id)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(app.token_cache)
            return result["access_token"]

    # First run: device code flow — user opens a browser to authenticate once
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Device flow failed: {flow.get('error_description')}")

    print(flow["message"])  # prints the URL and code for the user
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Authentication failed: {result.get('error_description')}")

    _save_cache(app.token_cache)
    return result["access_token"]


def upload_pdf(access_token: str, filename: str, pdf_bytes: bytes) -> str:
    path = f"{REMARKABLE_FOLDER}/{filename}"
    url = f"{GRAPH_BASE}/me/drive/root:/{path}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/pdf",
    }

    resp = requests.put(url, headers=headers, data=pdf_bytes, timeout=60)
    resp.raise_for_status()
    return resp.json().get("webUrl", "uploaded")


# Matches the names we generate, e.g. "news-2026-06-28.pdf",
# "nyt-frontpage-2026-06-28.pdf", "dailypress-2026-06-28.pdf". Other files in
# the folder are left alone.
_NEWS_FILE = re.compile(r"^(?:news|nyt-frontpage|dailypress)-(\d{4}-\d{2}-\d{2})\.pdf$")


def delete_old_pdfs(access_token: str, keep_days: int, today: date) -> list[str]:
    """Delete digests older than keep_days, based on the date in the filename.

    Only touches files matching the `news-YYYY-MM-DD.pdf` pattern this script
    creates — other files in the folder are left alone. Returns deleted names.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    list_url = f"{GRAPH_BASE}/me/drive/root:/{REMARKABLE_FOLDER}:/children"
    resp = requests.get(list_url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return []  # folder doesn't exist yet — nothing to clean
    resp.raise_for_status()

    cutoff = today - timedelta(days=keep_days)
    deleted = []

    for item in resp.json().get("value", []):
        match = _NEWS_FILE.match(item.get("name", ""))
        if not match:
            continue
        file_date = date.fromisoformat(match.group(1))
        if file_date < cutoff:
            del_url = f"{GRAPH_BASE}/me/drive/items/{item['id']}"
            d = requests.delete(del_url, headers=headers, timeout=30)
            d.raise_for_status()
            deleted.append(item["name"])

    return deleted
