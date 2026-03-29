"""
plan_email.py
Tiffany Haynes & Co. — Weekly Plan Approval System
Two modes:
  1. send_plan_to_client  — triggered when SM manager clicks "Send to Tiffany"
  2. plan_approved        — triggered when Tiffany approves on plan_approval.html
"""
import smtplib
import json
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

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
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_TOKEN      = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID= os.environ.get("NOTION_DATABASE_ID", "30bbc238-46ac-80de-bf24-000bb6d3ec0a")  # Project-THCO in TCT Media Team

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
    days = plan.get("days", [])

    # Split into week 1 and week 2
    week1_days = days[:7]
    week2_days = days[7:]

    def render_days(day_list):
        html = ""
        for day in day_list:
            p = pc(day.get("pillar",""))
            html += f'''
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
        return html

    # Build voiceover recording guide from all reel days
    reel_days = [d for d in days if d.get("voiceover_topic") and d.get("post_type","").lower() == "reel"]
    voiceover_html = ""
    if reel_days:
        talking_heads = [d for d in reel_days if d.get("reel_type","") == "Talking Head"]
        voiceover_broll = [d for d in reel_days if d.get("reel_type","") == "Voiceover"]

        def reel_row(d, num):
            reel_type = d.get("reel_type", "")
            badge_color = "#A00605" if reel_type == "Talking Head" else "#B87830"
            badge_bg = "rgba(160,6,5,0.1)" if reel_type == "Talking Head" else "rgba(184,120,48,0.1)"
            badge_icon = "🎥" if reel_type == "Talking Head" else "🎙️"
            badge_label = reel_type or "Reel"
            shot_list_html = ""
            if d.get("shot_list") and reel_type == "Voiceover":
                shot_list_html = f'''
<div style="margin-top:8px;background:#F4F0EB;border-radius:6px;padding:10px 12px;">
  <div style="font-size:9px;font-weight:700;color:#B87830;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px;">📋 B-Roll Shots to Film</div>
  <div style="font-size:11px;color:#5A5A5A;line-height:1.8;white-space:pre-wrap;">{d.get("shot_list","")}</div>
</div>'''
            return f'''
<tr>
  <td style="padding:14px 16px;border-bottom:1px solid #F0EBE3;vertical-align:top;width:28px;">
    <div style="width:24px;height:24px;background:#C49E3C;border-radius:50%;text-align:center;line-height:24px;font-size:11px;font-weight:700;color:#414141;">{num}</div>
  </td>
  <td style="padding:14px 16px;border-bottom:1px solid #F0EBE3;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
      <span style="font-size:10px;font-weight:700;color:#A0A0A0;letter-spacing:1px;text-transform:uppercase;">{d.get("day","")} &bull; {d.get("date","")}</span>
      <span style="font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;background:{badge_bg};color:{badge_color};">{badge_icon} {badge_label}</span>
    </div>
    <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:4px;">{d.get("title","")}</div>
    <div style="font-size:12px;color:#5A5A5A;line-height:1.65;">{d.get("voiceover_topic","")}</div>
    {shot_list_html}
  </td>
</tr>'''

        all_rows = "".join([reel_row(d, i+1) for i, d in enumerate(reel_days)])

        summary_line = f"{len(talking_heads)} Talking Head{' reel' if len(talking_heads)==1 else ' reels'} &bull; {len(voiceover_broll)} Voiceover + B-Roll reel{'s' if len(voiceover_broll)!=1 else ''}" if talking_heads and voiceover_broll else f"{len(reel_days)} reel{'s' if len(reel_days)!=1 else ''}"

        voiceover_html = f'''
<tr><td style="background:#FFFDF5;padding:22px 28px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <div style="background:#414141;border-radius:10px;overflow:hidden;">
    <div style="padding:16px 20px;">
      <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;">🎬 Recording Guide</div>
      <div style="font-size:16px;font-weight:700;color:#FFFDF5;margin-bottom:3px;">Your {len(reel_days)} Reels This Fortnight</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.45);">{summary_line} &bull; Each voiceover takes 30-60 seconds &bull; Your natural voice, no script needed</div>
    </div>
    <div style="padding:10px 16px;background:rgba(255,255,255,0.05);display:flex;gap:16px;">
      <span style="font-size:11px;color:rgba(255,255,255,0.6);">🎥 <strong style="color:rgba(255,255,255,0.9);">Talking Head</strong> = you on camera speaking directly</span>
      <span style="font-size:11px;color:rgba(255,255,255,0.6);">🎙️ <strong style="color:rgba(255,255,255,0.9);">Voiceover</strong> = record audio only, plays over B-roll you film</span>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#FFFDF5;">
      {all_rows}
    </table>
  </div>
</td></tr>'''

    note_html = f'<div style="background:#F4F0EB;border-left:3px solid #C49E3C;padding:12px 16px;border-radius:4px;font-size:13px;color:#5A5A5A;font-style:italic;line-height:1.75;margin-bottom:20px;">{planning_note}</div>' if planning_note else ""

    week1_html = render_days(week1_days)
    week2_html = render_days(week2_days) if week2_days else ""

    week2_section = f'''
<div style="font-size:10px;font-weight:700;color:#B87830;letter-spacing:2px;text-transform:uppercase;margin:20px 0 12px;padding-top:16px;border-top:2px solid #E3D3C8;">Week 2 Breakdown</div>
{week2_html}''' if week2_html else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;">
<tr><td align="center" style="padding:24px 16px 40px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<tr><td style="background:#414141;border-radius:12px 12px 0 0;padding:24px 28px;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">THE CREATIVE THEOLOGIAN MEDIA GROUP</div>
  <div style="font-size:22px;font-weight:700;color:#FFFDF5;margin-bottom:4px;">Your 2-Week Content Plan</div>
  <div style="font-size:13px;color:rgba(255,255,255,0.5);">{week_of} &bull; Sent {today}</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,#C49E3C,#B87830,#C49E3C);"></td></tr>

<tr><td style="background:#FFFDF5;padding:22px 28px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <div style="font-size:14px;color:#414141;line-height:1.8;margin-bottom:16px;">Hi Tiffany! Here is your 2-week content plan. Review each day below, leave notes on anything you'd like changed, and approve at the bottom.</div>
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">Strategic Direction</div>
  {note_html}
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">Week 1 Breakdown</div>
  {week1_html}
  {week2_section}
</td></tr>

{voiceover_html}

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

# ── NOTION TASK CREATION ──────────────────────────────────────────
def create_notion_task(project_name, role, description, week_of_str, post_type="Video Reels"):
    """Create a task in the Project-THCO Notion database (TCT Media Team)."""
    if not NOTION_TOKEN:
        print("NOTION_TOKEN not set — skipping Notion task creation.")
        return None
    try:
        from datetime import datetime as _dt, timedelta as _td

        # Calculate dates from week_of
        due_date = None
        publish_date = None
        try:
            start_str = week_of_str.split("-")[0].strip()
            if not any(str(y) in start_str for y in range(2020, 2030)):
                year = week_of_str.split(",")[-1].strip()
                start_str = f"{start_str}, {year}"
            start = _dt.strptime(start_str, "%B %d, %Y")
            due_date    = (start + _td(days=13)).strftime("%Y-%m-%d")   # end of editing week
            publish_date= (start + _td(days=14)).strftime("%Y-%m-%d")   # start of publishing week
        except Exception:
            pass

        # Map role to Drop in Que and Type
        role_config = {
            "designer1":    {"drop_in_que": "W/ Graphic Designer", "type": "Graphic"},
            "designer2":    {"drop_in_que": "W/ Graphic Designer", "type": "Carousel"},
            "video_editor": {"drop_in_que": "W/ Editor",           "type": "Video Reels"},
        }
        cfg = role_config.get(role, {"drop_in_que": "W/ Graphic Designer", "type": "Graphic"})

        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        properties = {
            "Project name": {"title": [{"text": {"content": project_name}}]},
            "Status":       {"status": {"name": "Not started"}},
            "Priority":     {"select": {"name": "High"}},
            "Client":       {"select": {"name": "THCO"}},
            "Team":         {"select": {"name": "Editing & Design"}},
            "Type":         {"select": {"name": cfg["type"]}},
            "Drop in Que":  {"multi_select": [{"name": cfg["drop_in_que"]}]},
            "Task Summary": {"rich_text": [{"text": {"content": description[:2000]}}]},
        }
        if due_date:
            properties["Due date"] = {"date": {"start": due_date}}
        if publish_date:
            properties["Publish Date"] = {"date": {"start": publish_date}}

        body = {"parent": {"database_id": NOTION_DATABASE_ID}, "properties": properties}
        r = requests.post(url, headers=headers, json=body)
        if r.status_code == 200:
            page_id = r.json().get("id", "")
            print(f"Notion task created: {project_name} → {cfg['drop_in_que']} (ID: {page_id})")
            return page_id
        else:
            print(f"Notion task failed ({r.status_code}): {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Notion task error: {e}")
        return None


def build_planning_horizon(week_of_str):
    """Calculate the 3-week timeline from the week_of string."""
    from datetime import datetime, timedelta
    try:
        start_str = week_of_str.split("-")[0].strip()
        if not any(str(y) in start_str for y in range(2020, 2030)):
            year = week_of_str.split(",")[-1].strip()
            start_str = f"{start_str}, {year}"
        start_date = datetime.strptime(start_str, "%B %d, %Y")
        record_start = start_date
        record_end   = start_date + timedelta(days=6)
        edit_start   = start_date + timedelta(weeks=1)
        edit_end     = edit_start + timedelta(days=6)
        pub_start    = start_date + timedelta(weeks=2)
        pub_end      = pub_start + timedelta(days=6)

        def fmt(d): return d.strftime("%B %-d")
        def fmt_yr(d): return d.strftime("%B %-d, %Y")

        recording  = f"{fmt(record_start)} - {fmt_yr(record_end)}"
        editing    = f"{fmt(edit_start)} - {fmt_yr(edit_end)}"
        publishing = f"{fmt(pub_start)} - {fmt_yr(pub_end)}"
        return recording, editing, publishing
    except Exception:
        return week_of_str, "Following week", "Week after that"


def build_team_email(plan, feedback, recipient_role, notion_copy, day_feedback=None):
    week_of = plan.get("week_of", "")
    today = datetime.now().strftime("%B %-d, %Y")
    role_colors = {
        "designer1":    {"color":"#B87830","bg":"rgba(184,120,48,0.1)","label":"Designer 1 - Thumbnails"},
        "designer2":    {"color":"#3A6EA8","bg":"rgba(58,110,168,0.1)","label":"Designer 2 - Carousels + Quotes"},
        "video_editor": {"color":"#3A9E6E","bg":"rgba(58,158,110,0.1)","label":"Video Editor - Reels"},
    }
    rc = role_colors.get(recipient_role, {"color":"#414141","bg":"rgba(65,65,65,0.08)","label":"Team Member"})

    recording, editing, publishing = build_planning_horizon(week_of)
    horizon_html = f"""
<div style="background:#EFF6FF;border:1px solid #3A6EA8;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
  <div style="font-size:10px;font-weight:700;color:#1E4B7A;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">&#128197; 2-Week Planning Horizon</div>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="font-size:11px;color:#1E4B7A;font-weight:700;padding-bottom:4px;">&#127909; Recording Week</td>
      <td style="font-size:12px;color:#414141;padding-bottom:4px;">{recording}</td>
    </tr>
    <tr>
      <td style="font-size:11px;color:#1E4B7A;font-weight:700;padding-bottom:4px;">&#9986;&#65039; Editing Week</td>
      <td style="font-size:12px;color:#414141;padding-bottom:4px;">{editing}</td>
    </tr>
    <tr>
      <td style="font-size:11px;color:#1E4B7A;font-weight:700;">&#128640; Publishing Week</td>
      <td style="font-size:12px;color:#414141;">{publishing}</td>
    </tr>
  </table>
  <div style="font-size:11px;color:#5A7A9A;margin-top:10px;line-height:1.6;">Final deliverables are due by end of the editing week so scheduling can begin on time.</div>
</div>"""

    feedback_parts = []
    if day_feedback:
        day_lines = "".join([
            f'<div style="margin-bottom:8px;padding:8px 12px;background:#FFFDF5;border-left:3px solid #B87830;border-radius:4px;">'
            f'<div style="font-size:11px;font-weight:700;color:#414141;">{d.get("day","")} — {d.get("title","")}</div>'
            f'<div style="font-size:12px;color:#5A5A5A;margin-top:3px;">{d.get("note","")}</div></div>'
            for d in day_feedback
        ])
        feedback_parts.append(f'<div style="margin-bottom:8px;font-size:10px;font-weight:700;color:#7A4E0D;letter-spacing:2px;text-transform:uppercase;">Per-Day Notes</div>{day_lines}')
    if feedback:
        feedback_parts.append(f'<div style="font-size:10px;font-weight:700;color:#7A4E0D;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;{"margin-top:12px;" if day_feedback else ""}">Overall Notes</div><div style="font-size:13px;color:#414141;line-height:1.7;">{feedback}</div>')

    feedback_html = f'<div style="background:#FFF3CD;border:1px solid #B87830;border-radius:8px;padding:14px 16px;margin-bottom:20px;">{"".join(feedback_parts)}</div>' if feedback_parts else ""

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
  {horizon_html}
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
def build_manager_email(plan, feedback, action, day_feedback=None):
    week_of = plan.get("week_of", "") if plan else ""
    today = datetime.now().strftime("%B %-d, %Y")
    action_label = "APPROVED" if action == "approved" else "REJECTED"
    action_color = "#3A9E6E" if action == "approved" else "#A00605"

    day_fb_html = ""
    if day_feedback:
        day_fb_html = '<div style="margin-top:14px;border-top:1px solid #E3D3C8;padding-top:12px;">'
        day_fb_html += '<div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Per-Day Notes from Tiffany</div>'
        for d in day_feedback:
            day_fb_html += f'<div style="background:#F4F0EB;border-left:3px solid #B87830;padding:8px 12px;border-radius:4px;margin-bottom:6px;"><div style="font-size:11px;font-weight:700;color:#414141;">{d.get("day","")} — {d.get("title","")}</div><div style="font-size:12px;color:#5A5A5A;margin-top:3px;">{d.get("note","")}</div></div>'
        day_fb_html += '</div>'

    overall_html = f'<div style="background:#FFF3CD;border-left:3px solid #B87830;padding:12px 16px;border-radius:4px;font-size:13px;color:#414141;line-height:1.7;margin-top:10px;"><strong>Overall notes:</strong> {feedback}</div>' if feedback else ""

    feedback_section = (day_fb_html + overall_html) if (day_feedback or feedback) else '<div style="font-size:13px;color:#8A8A8A;margin-top:8px;font-style:italic;">No feedback provided - approved as-is.</div>'

    next_step = "<div style='margin-top:16px;font-size:13px;color:#3A9E6E;font-weight:600;'>Team task emails have been sent automatically.</div>" if action == "approved" else "<div style='margin-top:16px;font-size:13px;color:#A00605;font-weight:600;'>Plan was REJECTED. Build a new plan from scratch.</div>"

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
  {next_step}
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

# ── SEND EMAIL ────────────────────────────────────────────────────
def send_email_msg(html, subject, to_email, cc_emails=""):
    to_email  = to_email.strip().replace('\n','').replace('\r','')
    cc_emails = cc_emails.strip().replace('\n','').replace('\r','') if cc_emails else ""
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

# ── AUTO-REGENERATE PLAN (on rejection) ──────────────────────────
def auto_regenerate_plan(old_plan, feedback, day_feedback):
    """Call Claude to generate a revised plan based on rejection feedback."""
    print("Auto-regenerating plan after rejection...")

    week_of  = old_plan.get("week_of", "")
    days     = old_plan.get("days", [])
    note     = old_plan.get("planning_note", "")

    rejected_summary = "\n".join([
        f"- {d.get('day')}: {d.get('post_type')} | {d.get('pillar')} | \"{d.get('title')}\" | Hook: {d.get('hook','')}"
        for d in days
    ])

    day_fb_text = ""
    if day_feedback:
        day_fb_text = "\nPER-DAY NOTES:\n" + "\n".join([
            f"- {d.get('day')} ({d.get('title','')}): {d.get('note','')}"
            for d in day_feedback
        ])

    prompt = f"""You are the lead content strategist for Tiffany Haynes and Co.
The client rejected the following 2-week content plan and provided feedback.
Generate a REVISED plan that addresses her feedback completely.

REJECTED PLAN (week of {week_of}):
{rejected_summary}

REJECTION FEEDBACK:{day_fb_text}
OVERALL: {feedback or "No overall feedback provided."}

Brand voice: Authentic, faith-driven, entrepreneurial. Bold, warm, direct.
Pillars: Business and Entrepreneurship, Spiritual Development and Gods Math Teaching,
Family and Lifestyle, Humor and Personality Shenanigans, Community and Testimony
Content mix per week: 3 Reels, 2 Carousels, 1 Quote Post, 1 Lifestyle

Return ONLY valid JSON matching this exact structure. No markdown. No backticks. Start with {{ end with }}.

{{
  "week_of": "{week_of}",
  "planning_note": "Brief note explaining the revisions made based on feedback",
  "days": [
    {{
      "day": "Monday",
      "date": "",
      "post_type": "Reel or Carousel or Quote Post or Static Image",
      "pillar": "exact pillar name from the list above",
      "title": "Post title",
      "hook": "Opening hook line",
      "content_direction": "2-3 sentences on what to cover",
      "voiceover_topic": "Recording direction for Tiffany",
      "designer_needed": "Designer 1 or Designer 2 or None",
      "thumbnail_hook": "Short thumbnail text",
      "carousel_outline": "",
      "quote": "",
      "fresh_or_scripted": "fresh"
    }}
  ],
  "delivery": {{
    "designer1": {{"name": "Designer 1", "sub": "Thumbnails", "notion_copy": "DESIGNER 1 TASKS\\n\\nWeek of {week_of}\\n\\nCreate thumbnails for each reel listed below..."}},
    "designer2": {{"name": "Designer 2", "sub": "Carousels and Quote Posts", "notion_copy": "DESIGNER 2 TASKS\\n\\nWeek of {week_of}\\n\\nCreate assets for carousels and quote posts..."}},
    "video_editor": {{"name": "Video Editor", "sub": "Reels", "notion_copy": "VIDEO EDITOR TASKS\\n\\nWeek of {week_of}\\n\\nEdit reels for the following days..."}}
  }}
}}"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    resp.raise_for_status()
    raw = resp.json()["content"][0]["text"].strip()
    raw = raw.replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ── RUN NOTIFY TEAM ───────────────────────────────────────────────
def run_notify_team(action, feedback, day_feedback, week_of, plan, delivery, approval_sha):
    # Notify manager
    if MANAGER_EMAIL:
        html = build_manager_email(plan, feedback, action, day_feedback)
        action_label = "Approved" if action == "approved" else "Rejected"
        manager_emails = [e.strip().replace('\n','').replace('\r','') for e in MANAGER_EMAIL.replace('\n',',').split(',') if e.strip()]
        primary = manager_emails[0]
        cc_rest = ', '.join(manager_emails[1:]) if len(manager_emails) > 1 else ''
        send_email_msg(html, f"[{action_label}] Tiffany Plan Response - Week of {week_of}", primary, cc_rest)

    if action == "approved":
        manager_cc = [e.strip().replace('\n','').replace('\r','') for e in MANAGER_EMAIL.replace('\n',',').split(',') if e.strip()]
        manager_cc_str = ', '.join(manager_cc)
        team = [
            ("designer1",    DESIGNER1_EMAIL,    delivery.get("designer1",{}).get("notion_copy","")),
            ("designer2",    DESIGNER2_EMAIL,    delivery.get("designer2",{}).get("notion_copy","")),
            ("video_editor", VIDEO_EDITOR_EMAIL, delivery.get("video_editor",{}).get("notion_copy","")),
        ]
        role_map = {
            "designer1":    "Designer 1 - Thumbnails",
            "designer2":    "Designer 2 - Carousels & Quotes",
            "video_editor": "Video Editor - Reels",
        }
        for role, email, notion_copy in team:
            if email and notion_copy:
                html = build_team_email(plan, feedback, role, notion_copy, day_feedback)
                role_label = role.replace("_"," ").title()
                send_email_msg(html, f"Your Tasks — Week of {week_of} (Approved)", email, manager_cc_str)
                print(f"Task email sent to {role_label}: {email} (CC: {manager_cc_str})")
                notion_role = role_map.get(role, "General/All Roles")
                task_name = f"{notion_role} — Week of {week_of}"
                create_notion_task(task_name, role, notion_copy, week_of)

    elif action == "rejected":
        try:
            new_plan = auto_regenerate_plan(plan, feedback, day_feedback)
            new_week_of = new_plan.get("week_of", week_of)

            plan_file = {
                "plan": new_plan,
                "week_of": new_week_of,
                "sent_to": EMAIL_TO,
                "sent_at": datetime.now().isoformat(),
                "status": "pending",
                "revision": True
            }
            url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/pending_plan.json"
            headers_gh = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            existing = requests.get(url, headers=headers_gh)
            sha = existing.json().get("sha") if existing.status_code == 200 else None
            body = {"message": f"Auto-revised plan for {new_week_of}", "content": base64.b64encode(json.dumps(plan_file, indent=2).encode()).decode()}
            if sha: body["sha"] = sha
            requests.put(url, headers=headers_gh, json=body)
            print(f"Revised plan saved to GitHub.")

            upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
            repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
            approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"
            html = build_client_email(new_plan, approval_url)
            send_email_msg(html, f"Revised Content Plan for {new_week_of} - Please Review & Approve", EMAIL_TO)
            print(f"Revised plan auto-sent to Tiffany: {EMAIL_TO}")

            if MANAGER_EMAIL:
                manager_emails = [e.strip().replace('\n','').replace('\r','') for e in MANAGER_EMAIL.replace('\n',',').split(',') if e.strip()]
                notify_html = f"""<html><body style="font-family:Georgia,serif;background:#F4F0EB;padding:24px;">
<div style="max-width:520px;margin:0 auto;background:#FFFDF5;border:1px solid #E3D3C8;border-radius:12px;padding:28px;">
<div style="font-size:10px;font-weight:700;color:#B87830;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px;">AUTO-REVISED PLAN SENT</div>
<div style="font-size:18px;font-weight:700;color:#414141;margin-bottom:8px;">A revised plan was automatically generated and sent to Tiffany.</div>
<div style="font-size:13px;color:#5A5A5A;line-height:1.7;">Based on her rejection feedback, Claude generated a new plan and sent it for approval. No action needed unless she rejects again.</div>
<div style="margin-top:16px;font-size:13px;color:#8A8A8A;font-style:italic;">Original feedback: {feedback or "No feedback provided."}</div>
</div></body></html>"""
                send_email_msg(notify_html, f"[Auto-Revised] New Plan Sent to Tiffany - Week of {new_week_of}", manager_emails[0])

        except Exception as e:
            print(f"Auto-regeneration failed: {e}")
            if MANAGER_EMAIL:
                manager_emails = [em.strip().replace('\n','').replace('\r','') for em in MANAGER_EMAIL.replace('\n',',').split(',') if em.strip()]
                err_html = f"""<html><body style="font-family:Georgia,serif;padding:24px;">
<div style="max-width:520px;margin:0 auto;background:#FFF5F5;border:1px solid #A00605;border-radius:12px;padding:28px;">
<div style="font-size:16px;font-weight:700;color:#A00605;margin-bottom:8px;">&#9888; Auto-Regeneration Failed</div>
<div style="font-size:13px;color:#414141;line-height:1.7;">Tiffany rejected the plan but the auto-revision failed. Please generate a new plan manually and resend.<br><br><strong>Error:</strong> {str(e)}</div>
</div></body></html>"""
                send_email_msg(err_html, "[ACTION REQUIRED] Plan Rejected - Auto-Revision Failed", manager_emails[0])

    # Clean up approval file
    if approval_sha:
        gh_delete("plan_approval.json", approval_sha, f"Plan approval processed - {week_of}")

    print(f"Team notification complete. Action: {action}")


# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    event = WORKFLOW_EVENT
    print(f"Plan email script running. Event: '{event}'")
    print(f"EVENT_PAYLOAD length: {len(os.environ.get('EVENT_PAYLOAD', '{}'))} chars")

    if event == "send_plan":
        trigger_source = os.environ.get("TRIGGER_SOURCE", "")
        payload_raw = os.environ.get("EVENT_PAYLOAD", "{}")
        print(f"EVENT_PAYLOAD raw: {payload_raw[:100]}")
        print(f"Trigger source: {trigger_source}")

        # ── BI-WEEKLY CHECK ──────────────────────────────────────────
        if trigger_source == "schedule":
            iso_week = datetime.now().isocalendar()[1]
            print(f"Scheduled run. ISO week number: {iso_week}")
            if iso_week % 2 != 0:
                print(f"Odd week ({iso_week}) — skipping. Auto-send runs on even weeks only.")
                exit(0)
            print(f"Even week ({iso_week}) — proceeding with auto-send.")

            try:
                from datetime import timedelta
                today = datetime.now()
                days_to_monday = (7 - today.weekday()) % 7 or 7
                next_monday = today + timedelta(days=days_to_monday)
                date_strs = []
                for i in range(14):
                    d = next_monday + timedelta(days=i)
                    date_strs.append(d.strftime("%A, %b %-d"))
                week_of = f"{date_strs[0]} - {date_strs[13]}"

                kb_context = ""
                try:
                    kb_data, _ = gh_get("kb_snapshot.json")
                    if kb_data:
                        kb_context = f"PERFORMANCE INSIGHTS: {json.dumps(kb_data)[:2000]}\n\n"
                except Exception:
                    pass

                auto_prompt = (
                    f"You are the lead content strategist for Tiffany Haynes and Co. "
                    f"Generate a complete 2-week content plan.\n\n"
                    f"{kb_context}"
                    f"WEEK 1: {date_strs[0]} through {date_strs[6]}\n"
                    f"WEEK 2: {date_strs[7]} through {date_strs[13]}\n\n"
                    f"Brand voice: Authentic, faith-driven, entrepreneurial. Bold, warm, direct.\n"
                    f"Pillars: Business and Entrepreneurship, Spiritual Development and Gods Math Teaching, "
                    f"Family and Lifestyle, Humor and Personality Shenanigans, Community and Testimony\n"
                    f"Content mix per week: 3 Reels, 2 Carousels, 1 Quote Post, 1 Lifestyle\n\n"
                    f"Return ONLY valid JSON. No markdown. No backticks.\n\n"
                    f'{{"week_of":"{week_of}","mode":"fresh","planning_note":"Strategic direction for these two weeks.",'
                    f'"pillar_balance":{{"Business and Entrepreneurship":0,"Spiritual Development and Gods Math Teaching":0,'
                    f'"Family and Lifestyle":0,"Humor and Personality Shenanigans":0,"Community and Testimony":0}},'
                    f'"gaps_addressed":[],'
                    f'"days":[{{"day":"Monday","date":"{date_strs[0]}","week_label":"Week 1","post_type":"Reel",'
                    f'"pillar":"pillar","title":"","hook":"","content_direction":"","voiceover_topic":"",'
                    f'"designer_needed":"Designer 1","thumbnail_hook":"","carousel_outline":"","quote":"","fresh_or_scripted":"fresh"}}],'
                    f'"delivery":{{"designer1":{{"name":"Designer 1","sub":"Thumbnails","notion_copy":""}},'
                    f'"designer2":{{"name":"Designer 2","sub":"Carousels and Quote Posts","notion_copy":""}},'
                    f'"video_editor":{{"name":"Video Editor","sub":"Reels","notion_copy":""}}}}}}'
                )

                import urllib.request as _req
                req_data = json.dumps({
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": auto_prompt}]
                }).encode()
                req = _req.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01"
                    }
                )
                with _req.urlopen(req) as resp:
                    result = json.loads(resp.read().decode())
                raw_text = next((b["text"] for b in result.get("content",[]) if b.get("type")=="text"), "")
                plan = json.loads(raw_text.replace("```json","").replace("```","").strip())
                week_of = plan.get("week_of", week_of)
                is_test = False
                recipient = EMAIL_TO
                print(f"Auto-generated plan for {week_of}")
            except Exception as e:
                print(f"Auto-generate failed: {e}")
                exit(1)

        else:
            try:
                payload = json.loads(payload_raw)
                if payload is None:
                    payload = {}
            except Exception:
                payload = {}

            plan      = payload.get("plan", {}) if payload else {}
            week_of   = payload.get("week_of", plan.get("week_of", "")) if payload else ""
            is_test   = payload.get("is_test", False) if payload else False
            recipient = payload.get("sent_to", EMAIL_TO) if payload else EMAIL_TO

            print(f"Payload plan days: {len(plan.get('days', []))}, week_of: '{week_of}'")

            # Fallback: if payload had no plan, try pending_plan.json
            if not plan:
                print("No plan in payload — trying pending_plan.json fallback...")
                plan_data, _ = gh_get("pending_plan.json")
                if plan_data:
                    plan      = plan_data.get("plan", {})
                    week_of   = plan_data.get("week_of", plan.get("week_of", ""))
                    recipient = plan_data.get("sent_to", recipient)
                    print(f"Plan loaded from pending_plan.json — week_of: '{week_of}'")
                else:
                    print("No plan in payload and no pending_plan.json found. Exiting.")
                    exit(0)

        # Save plan to GitHub so plan_approval.html and notify-team can load it
        try:
            plan_file = {
                "plan": plan,
                "week_of": week_of,
                "sent_to": recipient,
                "sent_at": datetime.now().isoformat(),
                "status": "pending"
            }
            print(f"Saving pending_plan.json — week_of: '{week_of}', days: {len(plan.get('days',[]))}, delivery keys: {list(plan.get('delivery',{}).keys())}")
            for role in ["designer1", "designer2", "video_editor"]:
                nc = plan.get("delivery",{}).get(role,{}).get("notion_copy","")
                print(f"  {role} notion_copy length being saved: {len(nc)}")
            url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/pending_plan.json"
            headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            sha = None
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                sha = r.json().get("sha")
            content = base64.b64encode(json.dumps(plan_file, indent=2).encode()).decode()
            body = {"message": f"Weekly plan for {week_of}", "content": content}
            if sha:
                body["sha"] = sha
            r2 = requests.put(url, headers=headers, json=body)
            print(f"Plan saved to GitHub: {r2.status_code}")
        except Exception as e:
            print(f"Could not save plan to GitHub: {e}")

        # Build approval URL and send email
        upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
        repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
        approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"

        html = build_client_email(plan, approval_url)
        subject = f"[TEST PREVIEW] Content Plan for {week_of}" if is_test else f"Your Content Plan for {week_of} - Please Review & Approve"
        send_email_msg(html, subject, recipient)
        print(f"Plan email sent to {recipient}" + (" (TEST)" if is_test else ""))

    elif event == "notify_team":
        approval_data, approval_sha = gh_get("plan_approval.json")
        if not approval_data:
            print("No plan_approval.json found. Exiting.")
            exit(0)

        action       = approval_data.get("action", "approved")
        feedback     = approval_data.get("overall_feedback", approval_data.get("feedback", ""))
        day_feedback = approval_data.get("day_feedback", [])
        week_of      = approval_data.get("week_of", "")
        print(f"Approval loaded — action: '{action}', week_of from approval: '{week_of}'")

        plan_data, _ = gh_get("pending_plan.json")
        print(f"pending_plan.json returned: {type(plan_data).__name__} — value: {str(plan_data)[:200]}")
        if plan_data is not None and isinstance(plan_data, dict) and plan_data:
            print(f"pending_plan.json top-level keys: {list(plan_data.keys())}")
            print(f"pending_plan.json week_of: '{plan_data.get('week_of','')}'")
            plan = plan_data.get("plan", {})
            print(f"plan keys: {list(plan.keys()) if plan else 'EMPTY'}")
            print(f"plan.week_of: '{plan.get('week_of','')}'")
            print(f"plan days count: {len(plan.get('days', []))}")
            delivery = plan.get("delivery", {})
            print(f"delivery keys: {list(delivery.keys())}")
            for role in ["designer1", "designer2", "video_editor"]:
                nc = delivery.get(role, {}).get("notion_copy", "")
                print(f"  {role} notion_copy length: {len(nc)}")
        else:
            print("pending_plan.json is empty or invalid — plan will be empty")
            plan = {}
            delivery = {}

        # week_of fallback chain
        if not week_of:
            week_of = (plan_data or {}).get("week_of", "") or plan.get("week_of", "")
            print(f"week_of after fallback: '{week_of}'")

        print(f"MANAGER_EMAIL set: {bool(MANAGER_EMAIL)}")
        print(f"DESIGNER1_EMAIL set: {bool(DESIGNER1_EMAIL)}")
        print(f"DESIGNER2_EMAIL set: {bool(DESIGNER2_EMAIL)}")
        print(f"VIDEO_EDITOR_EMAIL set: {bool(VIDEO_EDITOR_EMAIL)}")

        run_notify_team(action, feedback, day_feedback, week_of, plan, delivery, approval_sha)
