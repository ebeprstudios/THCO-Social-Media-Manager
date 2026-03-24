"""
plan_email.py
Tiffany Haynes & Co. — Weekly Plan Approval System
Two modes:
  1. send_plan_to_client  — triggered when SM manager clicks "Send to Tiffany"
  2. plan_approved        — triggered when Tiffany approves on plan_approval.html
"""
import anthropic
import smtplib
import json
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
EMAIL_TO          = os.environ["EMAIL_TO"]          # Tiffany
EMAIL_CC          = os.environ.get("EMAIL_CC", "")  # Your email + team
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
UPLOAD_TOKEN      = os.environ.get("UPLOAD_TOKEN", GITHUB_TOKEN)
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
WORKFLOW_EVENT    = os.environ.get("WORKFLOW_EVENT", "send_plan")  # send_plan or notify_team

# Team emails from secrets
DESIGNER1_EMAIL   = os.environ.get("DESIGNER1_EMAIL", "")
DESIGNER2_EMAIL   = os.environ.get("DESIGNER2_EMAIL", "")
VIDEO_EDITOR_EMAIL= os.environ.get("VIDEO_EDITOR_EMAIL", "")
MANAGER_EMAIL     = os.environ.get("MANAGER_EMAIL", EMAIL_CC.split(",")[0].strip() if EMAIL_CC else "")

PILLAR_COLORS = {
    "Business and Entrepreneurship":                {"bg":"#FEF8EE","border":"#B87830","text":"#7A4E0D"},
    "Spiritual Development and Gods Math Teaching": {"bg":"#FFF5F5","border":"#A00605","text":"#7A0504"},
    "Family and Lifestyle":                         {"bg":"#F0FAF4","border":"#3A9E6E","text":"#1E6B48"},
    "Humor and Personality Shenanigans":            {"bg":"#F6F3FF","border":"#6A50A8","text":"#3D2980"},
    "Community and Testimony":                      {"bg":"#EFF6FF","border":"#3A6EA8","text":"#1E4B7A"},
}

def gh_get(filename):
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return None, None
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None, None
    data = r.json()
    try:
        content = json.loads(base64.b64decode(data["content"]).decode())
        return content, data.get("sha")
    except:
        return None, None

def gh_delete(filename, sha, message):
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY or not sha:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    requests.delete(url, headers=headers, json={"message": message, "sha": sha})

def pc(pillar):
    return PILLAR_COLORS.get(pillar, {"bg":"#F8F8F8","border":"#E3D3C8","text":"#5A5A5A"})

# ── BUILD CLIENT EMAIL (plan review) ──────────────────────────────
def build_client_email(plan, approval_url):
    today = datetime.now().strftime("%B %-d, %Y")
    week_of = plan.get("week_of", "")
    planning_note = plan.get("planning_note", "")

    days_html = ""
    for day in plan.get("days", []):
        p = pc(day.get("pillar",""))
        days_html += f'''
<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E3D3C8;border-radius:10px;overflow:hidden;margin-bottom:12px;background:#FFFDF5;">
  <tr><td style="background:{p["bg"]};padding:10px 16px;border-bottom:1px solid {p["border"]}33;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="font-size:11px;font-weight:700;color:{p["text"]};letter-spacing:1px;text-transform:uppercase;">{day.get("day","")}</td>
      <td style="padding-left:10px;font-size:11px;color:#A0A0A0;">{day.get("date","")}</td>
      <td style="padding-left:10px;font-size:9px;font-weight:700;padding:2px 8px;background:{p["bg"]};color:{p["text"]};border-radius:8px;">{day.get("post_type","")}</td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:14px 16px;">
    <div style="font-size:15px;font-weight:700;color:#414141;margin-bottom:6px;line-height:1.4;">{day.get("title","")}</div>
    <div style="font-size:13px;color:#414141;font-style:italic;margin-bottom:8px;">"{day.get("hook","")}"</div>
    <div style="font-size:12px;color:#5A5A5A;line-height:1.65;">{day.get("content_direction","")}</div>
    {"<div style='margin-top:8px;font-size:10px;font-weight:700;color:#8A8A8A;letter-spacing:1px;text-transform:uppercase;'>" + day.get("designer_needed","") + "</div>" if day.get("designer_needed","") and day.get("designer_needed","") != "None" else ""}
  </td></tr>
</table>'''

    note_html = f'<div style="background:#F4F0EB;border-left:3px solid #C49E3C;padding:12px 16px;border-radius:4px;font-size:13px;color:#5A5A5A;font-style:italic;line-height:1.75;margin-bottom:20px;">{planning_note}</div>' if planning_note else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;">
<tr><td align="center" style="padding:24px 16px 40px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<tr><td style="background:#414141;border-radius:12px 12px 0 0;padding:24px 28px;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">THE CREATIVE THEOLOGIAN MEDIA GROUP</div>
  <div style="font-size:22px;font-weight:700;color:#FFFDF5;margin-bottom:4px;">Your Weekly Content Plan</div>
  <div style="font-size:13px;color:rgba(255,255,255,0.5);">Week of {week_of} &bull; Sent {today}</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,#C49E3C,#B87830,#C49E3C);"></td></tr>

<tr><td style="background:#FFFDF5;padding:22px 28px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <div style="font-size:14px;color:#414141;line-height:1.8;margin-bottom:16px;">Hi Tiffany! Here is your content plan for the week. Review each day below, add any feedback in the notes, and click the approve button when you're ready.</div>
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">Strategic Direction</div>
  {note_html}
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">Mon &mdash; Sun Breakdown</div>
  {days_html}
</td></tr>

<tr><td style="background:#414141;padding:24px 28px;text-align:center;">
  <div style="font-size:14px;color:rgba(255,255,255,0.7);margin-bottom:16px;line-height:1.7;">Ready to approve? Click below to review, add your feedback, and send it to the team.</div>
  <a href="{approval_url}" style="display:inline-block;background:#C49E3C;color:#414141;font-family:Georgia,serif;font-size:15px;font-weight:700;padding:14px 36px;border-radius:9px;text-decoration:none;letter-spacing:0.5px;">Review + Approve This Plan</a>
  <div style="font-size:11px;color:rgba(255,255,255,0.3);margin-top:16px;">This link is private and just for you.</div>
</td></tr>

<tr><td style="background:#FFFDF5;border:1px solid #E3D3C8;border-top:none;border-radius:0 0 12px 12px;padding:14px 28px;text-align:center;">
  <div style="font-size:10px;color:#A0A0A0;letter-spacing:1.5px;text-transform:uppercase;">The Creative Theologian Media Group &bull; Confidential</div>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""

# ── BUILD TEAM TASK EMAIL ─────────────────────────────────────────
def build_team_email(plan, feedback, recipient_role, notion_copy):
    week_of = plan.get("week_of", "")
    today = datetime.now().strftime("%B %-d, %Y")
    role_colors = {
        "designer1":    {"color":"#B87830","bg":"rgba(184,120,48,0.1)","label":"Designer 1 - Thumbnails"},
        "designer2":    {"color":"#3A6EA8","bg":"rgba(58,110,168,0.1)","label":"Designer 2 - Carousels + Quotes"},
        "video_editor": {"color":"#3A9E6E","bg":"rgba(58,158,110,0.1)","label":"Video Editor - Reels"},
    }
    rc = role_colors.get(recipient_role, {"color":"#414141","bg":"rgba(65,65,65,0.08)","label":"Team Member"})
    feedback_html = f'<div style="background:#FFF3CD;border:1px solid #B87830;border-radius:8px;padding:14px 16px;margin-bottom:20px;"><div style="font-size:10px;font-weight:700;color:#7A4E0D;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">Tiffany\'s Feedback</div><div style="font-size:13px;color:#414141;line-height:1.7;">{feedback}</div></div>' if feedback else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;">
<tr><td align="center" style="padding:24px 16px 40px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<tr><td style="background:#414141;border-radius:12px 12px 0 0;padding:22px 28px;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;">APPROVED &bull; READY TO DESIGN</div>
  <div style="font-size:20px;font-weight:700;color:#FFFDF5;margin-bottom:4px;">Your Tasks — Week of {week_of}</div>
  <div style="font-size:12px;color:rgba(255,255,255,0.4);">Approved by Tiffany on {today}</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,#C49E3C,#B87830,#C49E3C);"></td></tr>

<tr><td style="background:#FFFDF5;padding:22px 28px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <div style="background:{rc["bg"]};border-radius:8px;padding:10px 16px;margin-bottom:20px;display:inline-block;">
    <span style="font-size:12px;font-weight:700;color:{rc["color"]};">{rc["label"]}</span>
  </div>
  {feedback_html}
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">Your Notion Task Copy</div>
  <div style="background:#F4F0EB;border:1px solid #E3D3C8;border-radius:8px;padding:16px;font-size:12px;color:#414141;line-height:1.8;white-space:pre-wrap;font-family:Georgia,serif;">{notion_copy}</div>
  <div style="margin-top:16px;font-size:12px;color:#8A8A8A;line-height:1.7;">Submit by <strong>Tuesday EOD</strong>. Questions? Reply to this email.</div>
</td></tr>

<tr><td style="background:#414141;border-radius:0 0 12px 12px;padding:14px 28px;text-align:center;">
  <div style="font-size:10px;color:rgba(255,255,255,0.3);letter-spacing:1.5px;text-transform:uppercase;">The Creative Theologian Media Group &bull; Week of {week_of}</div>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""

# ── BUILD MANAGER NOTIFICATION EMAIL ─────────────────────────────
def build_manager_email(plan, feedback, action):
    week_of = plan.get("week_of", "")
    today = datetime.now().strftime("%B %-d, %Y")
    action_label = "APPROVED" if action == "approved" else "CHANGES REQUESTED"
    action_color = "#3A9E6E" if action == "approved" else "#B87830"
    feedback_section = f'<div style="background:#FFF3CD;border-left:3px solid #B87830;padding:12px 16px;border-radius:4px;font-size:13px;color:#414141;line-height:1.75;margin-top:12px;"><strong>Her feedback:</strong> {feedback}</div>' if feedback else '<div style="font-size:13px;color:#8A8A8A;margin-top:8px;font-style:italic;">No feedback provided - approved as-is.</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;">
<tr><td align="center" style="padding:24px 16px 40px;">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
<tr><td style="background:#FFFDF5;border:1px solid #E3D3C8;border-radius:12px;padding:28px;">
  <div style="font-size:10px;font-weight:700;color:{action_color};letter-spacing:3px;text-transform:uppercase;margin-bottom:8px;">{action_label}</div>
  <div style="font-size:20px;font-weight:700;color:#414141;margin-bottom:6px;">Tiffany responded to the week of {week_of}</div>
  <div style="font-size:12px;color:#8A8A8A;margin-bottom:16px;">{today}</div>
  {feedback_section}
  {"<div style='margin-top:16px;font-size:13px;color:#3A9E6E;font-weight:600;'>Team task emails have been sent automatically.</div>" if action == "approved" else "<div style='margin-top:16px;font-size:13px;color:#B87830;font-weight:600;'>Revise the plan and resend for her approval.</div>"}
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

# ── SEND EMAIL ────────────────────────────────────────────────────
def send_email_msg(html, subject, to_email, cc_emails=""):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email
    if cc_emails:
        msg["Cc"]  = cc_emails
    msg.attach(MIMEText(html, "html"))
    all_to = [to_email.strip()] + [e.strip() for e in cc_emails.split(",") if e.strip()]
    all_to = list(set(all_to))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, all_to, msg.as_string())
    print(f"Sent to {to_email}" + (f" CC: {cc_emails}" if cc_emails else ""))

# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    event = WORKFLOW_EVENT
    print(f"Plan email script running. Event: {event}")

    if event == "send_plan":
        # Load pending plan from GitHub and email it to Tiffany
        plan_data, _ = gh_get("pending_plan.json")
        if not plan_data:
            print("No pending_plan.json found. Exiting.")
            exit(0)

        plan = plan_data.get("plan", {})
        week_of = plan.get("week_of", "")
        tiffany_email = plan_data.get("sent_to", EMAIL_TO)

        # Build approval URL with token
        upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
        repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
        approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"

        html = build_client_email(plan, approval_url)
        send_email_msg(html, f"Your Content Plan for {week_of} — Please Review & Approve", tiffany_email)
        print(f"Plan email sent to {tiffany_email}")

    elif event == "notify_team":
        # Load approval from GitHub and send team task emails
        approval_data, approval_sha = gh_get("plan_approval.json")
        if not approval_data:
            print("No plan_approval.json found. Exiting.")
            exit(0)

        action   = approval_data.get("action", "approved")
        feedback = approval_data.get("feedback", "")
        week_of  = approval_data.get("week_of", "")

        plan_data, _ = gh_get("pending_plan.json")
        plan = plan_data.get("plan", {}) if plan_data else {}
        delivery = plan.get("delivery", {})

        # Notify manager first
        if MANAGER_EMAIL:
            html = build_manager_email(plan, feedback, action)
            action_label = "Approved" if action == "approved" else "Changes Requested"
            send_email_msg(html, f"[{action_label}] Tiffany's Plan Response — Week of {week_of}", MANAGER_EMAIL)

        if action == "approved":
            # Send task emails to each team member
            team = [
                ("designer1",    DESIGNER1_EMAIL,    delivery.get("designer1",{}).get("notion_copy","")),
                ("designer2",    DESIGNER2_EMAIL,    delivery.get("designer2",{}).get("notion_copy","")),
                ("video_editor", VIDEO_EDITOR_EMAIL, delivery.get("video_editor",{}).get("notion_copy","")),
            ]
            for role, email, notion_copy in team:
                if email and notion_copy:
                    html = build_team_email(plan, feedback, role, notion_copy)
                    role_label = role.replace("_"," ").title()
                    send_email_msg(html, f"Your Tasks — Week of {week_of} (Approved)", email)
                    print(f"Task email sent to {role_label}: {email}")

        # Clean up approval file
        if approval_sha:
            gh_delete("plan_approval.json", approval_sha, f"Plan approval processed - {week_of}")

        print(f"Team notification complete. Action: {action}")
