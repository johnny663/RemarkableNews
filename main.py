import os
import sys
from datetime import date

from dotenv import load_dotenv

from dailypress_client import fetch_full_edition
from mailer import send_papers
from nyt_frontpage import fetch_front_page_scan, fetch_intl_front_page_scan
from onedrive_client import (
    create_share_link,
    delete_old_pdfs,
    get_access_token,
    upload_pdf,
)
from pdf_utils import resize_pdf_to_move

KEEP_DAYS = 2  # delete papers older than this many days


def _upload(token: str, name: str, pdf_bytes: bytes) -> str:
    """Resize, upload, and return an anonymous sharing link for the email."""
    resized = resize_pdf_to_move(pdf_bytes)
    print(f"  Resized to {len(resized) / 1024:.0f} KB; uploading {name}...")
    url = upload_pdf(token, name, resized)
    print(f"  Done: {url}")
    return create_share_link(token, name)


def main() -> None:
    load_dotenv()

    client_id = os.environ.get("AZURE_CLIENT_ID")
    if not client_id:
        print("Error: set AZURE_CLIENT_ID in .env")
        sys.exit(1)

    today = date.today()

    print("Authenticating with OneDrive...")
    token = get_access_token(client_id)

    papers: list[tuple[str, str]] = []  # (filename, share link) for the email

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
        name = f"nyt-frontpage-{day.isoformat()}.pdf"
        papers.append((name, _upload(token, name, pdf_bytes)))
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
        name = f"nyt-intl-frontpage-{day.isoformat()}.pdf"
        papers.append((name, _upload(token, name, pdf_bytes)))
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
        name = f"dailypress-{day.isoformat()}.pdf"
        papers.append((name, _upload(token, name, pdf_bytes)))
    else:
        print("  No Daily Press edition available — skipping.")

    # Email OneDrive links to the papers — optional and best-effort: a mail
    # failure never fails the run, since the papers are already up on OneDrive.
    print("Emailing paper links...")
    try:
        send_papers(papers, today)
    except Exception as exc:
        print(f"  Email failed: {exc}")

    print(f"Cleaning up papers older than {KEEP_DAYS} days...")
    removed = delete_old_pdfs(token, KEEP_DAYS, today)
    if removed:
        print(f"  Deleted: {', '.join(removed)}")
    else:
        print("  Nothing to delete")

    if not papers:
        print("No papers uploaded — failing the run so it's visible.")
        sys.exit(1)
    print(f"{len(papers)}/3 papers uploaded.")


if __name__ == "__main__":
    main()
