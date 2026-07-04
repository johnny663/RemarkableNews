import os
import sys
from datetime import date

from dotenv import load_dotenv

from dailypress_client import fetch_full_edition
from nyt_frontpage import fetch_front_page_scan, fetch_intl_front_page_scan
from onedrive_client import delete_old_pdfs, get_access_token, upload_pdf
from pdf_utils import resize_pdf_to_move

KEEP_DAYS = 2  # delete papers older than this many days


def _upload(token: str, name: str, pdf_bytes: bytes) -> None:
    resized = resize_pdf_to_move(pdf_bytes)
    print(f"  Resized to {len(resized) / 1024:.0f} KB; uploading {name}...")
    url = upload_pdf(token, name, resized)
    print(f"  Done: {url}")


def main() -> None:
    load_dotenv()

    client_id = os.environ.get("AZURE_CLIENT_ID")
    if not client_id:
        print("Error: set AZURE_CLIENT_ID in .env")
        sys.exit(1)

    today = date.today()

    print("Authenticating with OneDrive...")
    token = get_access_token(client_id)

    uploaded = 0

    # Each paper is best-effort: one source being down shouldn't stop the
    # others from shipping. The run only fails if NOTHING uploads.

    print("Fetching NYT front-page scan...")
    try:
        nyt = fetch_front_page_scan(today)
    except Exception as exc:
        nyt = None
        print(f"  NYT fetch failed: {exc}")
    if nyt:
        pdf_bytes, day = nyt
        _upload(token, f"nyt-frontpage-{day.isoformat()}.pdf", pdf_bytes)
        uploaded += 1
    else:
        print("  No front-page scan available — skipping.")

    print("Fetching NYT International front page...")
    try:
        intl = fetch_intl_front_page_scan(today)
    except Exception as exc:
        intl = None
        print(f"  Intl fetch failed: {exc}")
    if intl:
        pdf_bytes, day = intl
        _upload(token, f"nyt-intl-frontpage-{day.isoformat()}.pdf", pdf_bytes)
        uploaded += 1
    else:
        print("  No International front page available — skipping.")

    print("Fetching Daily Press e-edition (headless)...")
    try:
        edition = fetch_full_edition()
    except Exception as exc:  # Playwright/browser/network issues
        edition = None
        print(f"  Daily Press fetch failed: {exc}")
    if edition:
        pdf_bytes, day = edition
        _upload(token, f"dailypress-{day.isoformat()}.pdf", pdf_bytes)
        uploaded += 1
    else:
        print("  No Daily Press edition available — skipping.")

    print(f"Cleaning up papers older than {KEEP_DAYS} days...")
    removed = delete_old_pdfs(token, KEEP_DAYS, today)
    if removed:
        print(f"  Deleted: {', '.join(removed)}")
    else:
        print("  Nothing to delete")

    if uploaded == 0:
        print("No papers uploaded — failing the run so it's visible.")
        sys.exit(1)
    print(f"{uploaded}/3 papers uploaded.")


if __name__ == "__main__":
    main()
