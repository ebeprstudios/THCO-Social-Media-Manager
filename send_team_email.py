"""
send_team_email.py
EBEPR Studios — THCO Content Studio
Reads team_plan_email.html from the repo and sends it to the creative team
via SMTP (same method as plan_email.py — fully renders HTML in all email clients).

Triggered by: repository_dispatch event_type = send_team_plan_email
Does NOT generate a new plan. Sends whatever HTML is stored in team_plan_email.html.
"""
import smtplib
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── ENV ─────────────────────────────────────────────────────────────
EMAIL_FROM         = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD     = os.environ["EMAIL_PASSWORD"]
DESIGNER1_EMAIL    = os.environ.get("DESIGNER1_EMAIL", "")   # Brittany
DESIGNER2_EMAIL    = os.environ.get("DESIGNER2_EMAIL", "")   # Diana
VIDEO_EDITOR_EMAIL = os.environ.get("VIDEO_EDITOR_EMAIL", "") # Haroon
MANAGER_EMAIL      = os.environ.get("MANAGER_EMAIL", "")     # Erica (CC)
GITHUB_TOKEN       = os.environ.get("UPLOAD_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GITHUB_REPOSITORY  = os.environ.get("GITHUB_REPOSITORY", "")
EMAIL_SUBJECT      = os.environ.get("EMAIL_SUBJECT", "THCO Content Plan: April 5 to May 4")
EMAIL_FILE         = os.environ.get("EMAIL_FILE", "team_plan_email.html")

# ── READ HTML FROM REPO ─────────────────────────────────────────────
def read_html_from_repo(filename):
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        raise Exception("Missing GITHUB_TOKEN or GITHUB_REPOSITORY env vars.")
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Could not read {filename} from repo. Status: {r.status_code}. Response: {r.text[:200]}")
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    print(f"Read {filename} from repo ({len(content)} chars)")
    return content

# ── SEND HTML EMAIL ─────────────────────────────────────────────────
def send_html_email(subject, html_body, to_emails, cc_emails=None):
    if not to_emails:
        raise Exception("No recipients. Check DESIGNER1_EMAIL and DESIGNER2_EMAIL secrets.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"]  = ", ".join(cc_emails)

    # Attach HTML part — this is what makes it render correctly
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    all_recipients = to_emails + (cc_emails or [])

    print(f"Sending to: {', '.join(all_recipients)}")
    print(f"Subject: {subject}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, all_recipients, msg.as_string())

    print(f"Team plan email sent successfully to {len(all_recipients)} recipient(s).")

# ── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    html_body = read_html_from_repo(EMAIL_FILE)

    to_list = [e.strip() for e in [DESIGNER1_EMAIL, DESIGNER2_EMAIL] if e.strip()]
    cc_list = [e.strip() for e in [MANAGER_EMAIL] if e.strip()]

    send_html_email(EMAIL_SUBJECT, html_body, to_list, cc_list)
