import os
import sys
from datetime import date

from dotenv import load_dotenv

from guardian_client import fetch_articles as fetch_guardian
from newsdata_client import fetch_articles as fetch_newsdata
from nyt_frontpage import fetch_front_page_scan
from onedrive_client import delete_old_pdfs, get_access_token, upload_pdf
from pdf_builder import build_pdf, resize_pdf_to_move

GUARDIAN_MAX = 12    # full-text articles
NEWSDATA_MAX = 8     # summary articles, placed first
KEEP_DAYS = 2        # delete digests older than this many days


def main() -> None:
    load_dotenv()

    guardian_key = os.environ.get("GUARDIAN_API_KEY")
    news_key = os.environ.get("NEWSDATA_API_KEY")
    client_id = os.environ.get("AZURE_CLIENT_ID")

    if not news_key or not client_id:
        print("Error: set NEWSDATA_API_KEY and AZURE_CLIENT_ID in .env")
        sys.exit(1)

    today = date.today().isoformat()
    filename = f"news-{today}.pdf"

    articles = []

    # NewsData.io first — summaries from a range of outlets
    print("Fetching summaries from NewsData.io...")
    newsdata = fetch_newsdata(news_key, max_articles=NEWSDATA_MAX)
    print(f"  {len(newsdata)} summary articles")
    articles.extend(newsdata)

    # The Guardian after — full article text
    if guardian_key:
        print("Fetching full articles from The Guardian...")
        guardian = fetch_guardian(guardian_key, max_articles=GUARDIAN_MAX)
        print(f"  {len(guardian)} full-text articles")
        articles.extend(guardian)
    else:
        print("GUARDIAN_API_KEY not set — skipping Guardian (no full-text section)")

    full = sum(1 for a in articles if a.is_full)
    print(f"  Total: {len(articles)} articles ({full} full-text, {len(articles) - full} summary-only)")

    if not articles:
        print("No articles returned — aborting.")
        sys.exit(1)

    print("Building PDF...")
    pdf_bytes = build_pdf(articles, today)
    print(f"  {len(pdf_bytes) / 1024:.0f} KB")

    print("Authenticating with OneDrive...")
    token = get_access_token(client_id)

    print(f"Uploading {filename}...")
    web_url = upload_pdf(token, filename, pdf_bytes)
    print(f"  Done: {web_url}")

    # NYT print front-page scan — fetched as a PDF, resized for the Move, and
    # uploaded as a separate file. Best-effort: the digest is already up, so a
    # missing scan (e.g. not posted yet) just warns instead of failing the run.
    print("Fetching NYT front-page scan...")
    scan = fetch_front_page_scan(date.today())
    if scan:
        scan_bytes, scan_date = scan
        scan_name = f"nyt-frontpage-{scan_date.isoformat()}.pdf"
        resized = resize_pdf_to_move(scan_bytes)
        print(f"  {scan_date} scan resized to {len(resized) / 1024:.0f} KB; uploading {scan_name}...")
        scan_url = upload_pdf(token, scan_name, resized)
        print(f"  Done: {scan_url}")
    else:
        print("  No front-page scan available — skipping.")

    print(f"Cleaning up digests older than {KEEP_DAYS} days...")
    removed = delete_old_pdfs(token, KEEP_DAYS, date.today())
    if removed:
        print(f"  Deleted: {', '.join(removed)}")
    else:
        print("  Nothing to delete")


if __name__ == "__main__":
    main()
