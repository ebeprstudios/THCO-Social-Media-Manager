"""
send_team_email.py
EBEPR Studios - THCO Content Studio

SEND RULES - NON NEGOTIABLE:
  IS_TEST=true  → sends to Erica ONLY. Subject prefixed [TEST].
  IS_TEST=false → sends to Brittany + Diana. Erica ALWAYS CC'd.

Erica (ebeprinc@gmail.com) is HARDCODED on every send.
Never rely only on MANAGER_EMAIL secret. Both are included.
"""
import smtplib
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
MANAGER_EMAIL     = os.environ.get("MANAGER_EMAIL", "").strip()
GITHUB_TOKEN      = os.environ.get("UPLOAD_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
EMAIL_SUBJECT     = os.environ.get("EMAIL_SUBJECT", "THCO Content Plan: Week 1")
EMAIL_FILE        = os.environ.get("EMAIL_FILE", "team_plan_email.html")
IS_TEST           = os.environ.get("IS_TEST", "false").lower() == "true"

# Erica hardcoded — always included regardless of secrets
ERICA_EMAIL = "ebeprinc@gmail.com"

# Team recipients
TEAM_TO = [
    "brittany@transactionez.com",
    "diana@divineordersupport.com",
]

def build_cc_list():
    """Erica always CC'd. Include MANAGER_EMAIL too if set and different."""
    cc = [ERICA_EMAIL]
    if MANAGER_EMAIL and MANAGER_EMAIL.lower() != ERICA_EMAIL.lower():
        cc.append(MANAGER_EMAIL)
    return cc

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
    print("Email sent successfully.")

if __name__ == "__main__":
    html_body = read_html_from_repo(EMAIL_FILE)

    if IS_TEST:
        # TEST: Erica only. Team never sees it.
        print(f"TEST MODE: sending only to {ERICA_EMAIL}")
        send_html_email(f"[TEST] {EMAIL_SUBJECT}", html_body, [ERICA_EMAIL])
    else:
        # LIVE: Brittany + Diana. Erica always CC'd.
        cc = build_cc_list()
        send_html_email(EMAIL_SUBJECT, html_body, TEAM_TO, cc)
