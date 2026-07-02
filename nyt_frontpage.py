from datetime import date, timedelta

import requests

# The NYT publishes free, public scans of the day's print front pages at
# predictable, date-keyed paths. No subscription or API key is needed.
# US edition:
SCAN_URL = "https://static01.nyt.com/images/{y:04d}/{m:02d}/{d:02d}/nytfrontpage/scan.pdf"
# International edition (no Sunday paper; the filename repeats the date):
INTL_SCAN_URL = (
    "https://static01.nyt.com/images/{y:04d}/{m:02d}/{d:02d}/nytfrontpage/"
    "INYT_frontpage_global.{y:04d}{m:02d}{d:02d}.pdf"
)

# The 6am job can run before the current day's front page is posted, so we fall
# back to the previous day rather than ship nothing.
LOOKBACK_DAYS = 1


def _fetch_scan(url_template: str, label: str, today: date) -> tuple[bytes, date] | None:
    """Download a date-keyed front-page scan PDF.

    Tries `today`, then walks back up to LOOKBACK_DAYS to cover the case where
    the current day's scan hasn't been posted yet at 6am. Returns the raw PDF
    bytes and the date that actually resolved, or None if nothing is available.
    """
    for offset in range(LOOKBACK_DAYS + 1):
        day = today - timedelta(days=offset)
        url = url_template.format(y=day.year, m=day.month, d=day.day)
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as exc:
            print(f"  {label} {day}: request failed ({exc})")
            continue

        if resp.status_code == 404:
            print(f"  {label} {day}: not posted yet (404)")
            continue
        if resp.status_code != 200:
            print(f"  {label} {day}: HTTP {resp.status_code}")
            continue
        if "application/pdf" not in resp.headers.get("Content-Type", ""):
            print(f"  {label} {day}: not a PDF (got {resp.headers.get('Content-Type')})")
            continue

        return resp.content, day

    return None


def fetch_front_page_scan(today: date) -> tuple[bytes, date] | None:
    """The US-edition print front page."""
    return _fetch_scan(SCAN_URL, "Front page", today)


def fetch_intl_front_page_scan(today: date) -> tuple[bytes, date] | None:
    """The International-edition print front page (published Mon-Sat)."""
    return _fetch_scan(INTL_SCAN_URL, "Intl front page", today)
