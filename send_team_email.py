"""
send_team_email.py
EBEPR Studios - THCO Content Studio
Sends team_plan_email.html to Brittany and Diana (Tiffany's creative team).

Secrets needed in GitHub repo:
  BRITTANY_EMAIL   - brittany@transactionez.com
  DIANA_EMAIL      - diana@divineordersupport.com
  MANAGER_EMAIL    - Erica (CC'd on every send)
  EMAIL_FROM       - sending Gmail address
  EMAIL_PASSWORD   - Gmail app password
  UPLOAD_TOKEN     - PAT with repo scope
"""
import smtplib
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
BRITTANY_EMAIL    = os.environ.get("BRITTANY_EMAIL", "")
DIANA_EMAIL       = os.environ.get("DIANA_EMAIL", "")
MANAGER_EMAIL     = os.environ.get("MANAGER_EMAIL", "")
GITHUB_TOKEN      = os.environ.get("UPLOAD_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
EMAIL_SUBJECT     = os.environ.get("EMAIL_SUBJECT", "THCO Content Plan: April 5 to May 4")
EMAIL_FILE        = os.environ.get("EMAIL_FILE", "team_plan_email.html")

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
    if not to_emails:
        raise Exception("No recipients. Set BRITTANY_EMAIL and DIANA_EMAIL in GitHub secrets.")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"]  = ", ".join(cc_emails)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    all_recipients = to_emails + (cc_emails or [])
    print(f"Sending to: {', '.join(to_emails)}")
    if cc_emails:
        print(f"CC: {', '.join(cc_emails)}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, all_recipients, msg.as_string())
    print("Team plan email sent successfully.")

if __name__ == "__main__":
    html_body = read_html_from_repo(EMAIL_FILE)
    to_list = [e.strip() for e in [BRITTANY_EMAIL, DIANA_EMAIL] if e.strip()]
    cc_list = [e.strip() for e in [MANAGER_EMAIL] if e.strip()]
    send_html_email(EMAIL_SUBJECT, html_body, to_list, cc_list)
