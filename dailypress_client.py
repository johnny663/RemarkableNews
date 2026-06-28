import re
from datetime import date

import requests

# Daily Press e-edition is a PageSuite reader. The day's content (the whole
# paper as one PDF, per-page PDFs, the manifest) is all public on the CDN — but
# the *index* that says which edition GUID is "today" is auth-gated. So we load
# the public reader headlessly, let its JS resolve the latest edition, and
# capture the first content URL it requests (which embeds both GUIDs we need).
SHORTCODE = "DAI635"
ACCOUNT_GUID = "fea9d757-caf1-44de-a806-73630a1ba0bf"
PUBLICATION_GUID = "80867110-f46f-4c64-af4a-3a83b619f594"

READER_URL = f"https://enewspaper.dailypress.com/shortcode/{SHORTCODE}"
PUBLISHED = "https://published.pagesuite.com"
PUBLISHED_PDF = "https://published.pdf.pagesuite.com"
UA = "Mozilla/5.0"

_GUID = r"[0-9a-f-]{36}"
# Matches https://published[.pdf].pagesuite.com/{account}/{publication}/{edition}/{published}/...
_RESOURCE = re.compile(
    rf"published(?:\.pdf)?\.pagesuite\.com/{ACCOUNT_GUID}/{PUBLICATION_GUID}/({_GUID})/({_GUID})/"
)


def _discover_edition() -> tuple[str, str] | None:
    """Resolve the latest edition's (editionGUID, publishedGUID) via headless browser.

    The GUIDs aren't in the server HTML and aren't date-derivable, and the
    editions feed needs a subscriber token — so we drive a headless Chromium,
    let the reader resolve the latest edition anonymously, and sniff the first
    CDN request it makes. Returns None if nothing resolved.
    """
    from playwright.sync_api import sync_playwright

    found: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        def on_request(req) -> None:
            if "ed" in found:
                return
            m = _RESOURCE.search(req.url)
            if m:
                found["ed"], found["pub"] = m.group(1), m.group(2)

        page.on("request", on_request)
        try:
            page.goto(READER_URL, wait_until="domcontentloaded", timeout=45000)
            for _ in range(30):  # give the JS up to ~30s to resolve + load a page
                if "ed" in found:
                    break
                page.wait_for_timeout(1000)
        finally:
            browser.close()

    if "ed" not in found:
        return None
    return found["ed"], found["pub"]


def fetch_full_edition() -> tuple[bytes, date] | None:
    """Download the whole Daily Press e-edition as a single multi-page PDF.

    Returns (pdf_bytes, edition_date), or None if the edition can't be resolved
    or downloaded. The edition date comes from the public manifest so the
    filename is accurate even when the 6am run still sees yesterday's paper.
    """
    guids = _discover_edition()
    if not guids:
        print("  Could not resolve the latest Daily Press edition")
        return None
    ed, pub = guids
    base = f"{ACCOUNT_GUID}/{PUBLICATION_GUID}/{ed}/{pub}"

    # Manifest → real publication date (best-effort; falls back to today).
    pub_date = date.today()
    meta = requests.get(f"{PUBLISHED}/{base}/edition.json", timeout=60, headers={"User-Agent": UA})
    if meta.status_code == 200:
        try:
            pub_date = date.fromisoformat(meta.json()["pubdate"][:10])
        except (ValueError, KeyError, requests.JSONDecodeError):
            pass

    # The whole paper, one public PDF.
    resp = requests.get(f"{PUBLISHED_PDF}/{base}/edition.pdf", timeout=180, headers={"User-Agent": UA})
    if resp.status_code != 200 or "application/pdf" not in resp.headers.get("Content-Type", ""):
        print(f"  Daily Press edition PDF unavailable (HTTP {resp.status_code})")
        return None

    return resp.content, pub_date
