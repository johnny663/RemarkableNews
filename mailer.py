import os
import smtplib
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


def send_papers(papers: list[tuple[str, bytes]]) -> int:
    """Email each paper as its own PDF attachment to every recipient.

    One message per paper keeps each mail under provider attachment limits
    (the Daily Press e-edition alone can run to many MB). Email is optional:
    missing recipients or SMTP settings just skip with a note. Returns the
    number of messages sent.
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
    sender = os.environ.get("SMTP_FROM", user)
    if not (host and user and password):
        print("  SMTP_HOST/SMTP_USER/SMTP_PASS not set — skipping email.")
        return 0

    sent = 0
    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        for name, pdf_bytes in papers:
            msg = EmailMessage()
            msg["Subject"] = name.removesuffix(".pdf")
            msg["From"] = sender
            msg["To"] = ", ".join(recipients)
            msg.set_content("Attached: today's paper from RemarkableNews.")
            msg.add_attachment(
                pdf_bytes, maintype="application", subtype="pdf", filename=name
            )
            smtp.send_message(msg)
            print(f"  Sent {name} to {len(recipients)} recipient(s)")
            sent += 1
    return sent
