from datetime import date, timedelta

import requests

# The NYT publishes a free, public scan of the day's print front page at a
# predictable, date-keyed path. No subscription or API key is needed.
SCAN_URL = "https://static01.nyt.com/images/{y:04d}/{m:02d}/{d:02d}/nytfrontpage/scan.pdf"

# The 6am job can run before the current day's front page is posted, so we fall
# back to the previous day rather than ship nothing.
LOOKBACK_DAYS = 1


def _scan_url(day: date) -> str:
    return SCAN_URL.format(y=day.year, m=day.month, d=day.day)


def fetch_front_page_scan(today: date) -> tuple[bytes, date] | None:
    """Download the NYT print front-page scan PDF.

    Tries `today`, then walks back up to LOOKBACK_DAYS to cover the case where
    the current day's scan hasn't been posted yet at 6am. Returns the raw PDF
    bytes and the date that actually resolved, or None if nothing is available.
    """
    for offset in range(LOOKBACK_DAYS + 1):
        day = today - timedelta(days=offset)
        url = _scan_url(day)
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as exc:
            print(f"  Front page {day}: request failed ({exc})")
            continue

        if resp.status_code == 404:
            print(f"  Front page {day}: not posted yet (404)")
            continue
        if resp.status_code != 200:
            print(f"  Front page {day}: HTTP {resp.status_code}")
            continue
        if "application/pdf" not in resp.headers.get("Content-Type", ""):
            print(f"  Front page {day}: not a PDF (got {resp.headers.get('Content-Type')})")
            continue

        return resp.content, day

    return None
