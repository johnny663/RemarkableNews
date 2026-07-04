import os
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

# Recipients live in their own file so they can be edited without touching
# code: one address per line, # comments and blank lines ignored.
RECIPIENTS_FILE = Path(__file__).parent / "recipients.txt"


def load_recipients() -> list[str]:
    if not RECIPIENTS_FILE.exists():
        return []
    recipients = []
    for line in RECIPIENTS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            recipients.append(line)
    return recipients


def send_papers(papers: list[tuple[str, str]], today: date) -> int:
    """Email one message with OneDrive links to today's papers.

    Links instead of attachments: no provider size limits, so even the
    multi-MB Daily Press e-edition is deliverable. Email is optional:
    missing recipients or SMTP settings just skip with a note. Returns the
    number of messages sent (0 or 1).
    """
    recipients = load_recipients()
    if not recipients:
        print("  No recipients in recipients.txt — skipping email.")
        return 0

    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    # In CI an unset secret arrives as an empty string, so `or` (not a
    # get-default) is what keeps int() from choking.
    port = int(os.environ.get("SMTP_PORT") or "587")
    sender = os.environ.get("SMTP_FROM") or user
    if not (host and user and password):
        print("  SMTP_HOST/SMTP_USER/SMTP_PASS not set — skipping email.")
        return 0

    lines = ["Today's papers:", ""]
    for name, link in papers:
        lines.append(f"{name.removesuffix('.pdf')}:")
        lines.append(link)
        lines.append("")

    msg = EmailMessage()
    msg["Subject"] = f"Martin Newspaper — {today.isoformat()}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(lines))

    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"  Sent links for {len(papers)} paper(s) to {len(recipients)} recipient(s)")
    return 1
