"""
send_team_email.py
EBEPR Studios - THCO Content Studio

SEND RULES - NON NEGOTIABLE:
  Team email (this script): Brittany + Diana ONLY. Never Tiffany.
  Client approval email (plan_email.py): Tiffany ONLY.
  These are two completely separate sends. Never mix them.
"""
import smtplib
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
MANAGER_EMAIL     = os.environ.get("MANAGER_EMAIL", "")
GITHUB_TOKEN      = os.environ.get("UPLOAD_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
EMAIL_SUBJECT     = os.environ.get("EMAIL_SUBJECT", "THCO Content Plan: Week 1")
EMAIL_FILE        = os.environ.get("EMAIL_FILE", "team_plan_email.html")

# TEAM ONLY - Brittany and Diana. Never Tiffany.
TO_EMAILS = [
    "brittany@transactionez.com",
    "diana@divineordersupport.com",
]

def read_html_from_repo(filename):
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        raise Exception("Missing UPLOAD_TOKEN or GITHUB_REPOSITORY.")
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Could not read {filename}. Status: {r.status_code}. {r.text[:200]}")
    content = base64.b64decode(r.json()["content"]).decode("utf-8")
    print(f"Read {filename} from repo ({len(content)} chars)")
    return content

def send_html_email(subject, html_body, to_emails, cc_emails=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"]  = ", ".join(cc_emails)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    all_recipients = to_emails + (cc_emails or [])
    print(f"Sending to:  {', '.join(to_emails)}")
    if cc_emails:
        print(f"CC:          {', '.join(cc_emails)}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, all_recipients, msg.as_string())
    print("Team email sent successfully.")

if __name__ == "__main__":
    html_body = read_html_from_repo(EMAIL_FILE)
    cc_list = [MANAGER_EMAIL.strip()] if MANAGER_EMAIL.strip() else []
    send_html_email(EMAIL_SUBJECT, html_body, TO_EMAILS, cc_list)
