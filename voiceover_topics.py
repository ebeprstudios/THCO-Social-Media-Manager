"""
Tiffany Haynes & Co. -- Weekly Voiceover Topics Email
Reads approved_topics.json if SM manager approved topics in the Content Studio.
Falls back to generating fresh topics via Claude if no approval file found.
"""

import anthropic
import smtplib
import json
import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
EMAIL_TO          = os.environ["EMAIL_TO"]
EMAIL_CC          = os.environ.get("EMAIL_CC", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")

def get_next_monday(ref=None):
    d = ref or datetime.now()
    days_ahead = 7 - d.weekday()
    if days_ahead == 7:
        days_ahead = 7
    return d + timedelta(days=days_ahead)

def format_week(start):
    end = start + timedelta(days=6)
    return f"{start.strftime('%B %-d')} - {end.strftime('%B %-d, %Y')}"

recording_week  = format_week(get_next_monday())
publishing_week = format_week(get_next_monday() + timedelta(weeks=2))

def fetch_approved_topics():
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return None, None
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/approved_topics.json"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"No approved_topics.json found ({r.status_code}). Generating fresh topics.")
        return None, None
    data = r.json()
    sha = data.get("sha")
    content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    if not content.get("approved"):
        print("File found but not marked approved. Generating fresh topics.")
        return None, None
    print(f"Found approved topics. Test mode: {content.get('test_mode', False)}")
    return content, sha

def delete_approved_file(sha):
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY or not sha:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/approved_topics.json"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    body = {"message": f"Clear approved topics after sending ({datetime.now().strftime('%Y-%m-%d')})", "sha": sha}
    r = requests.delete(url, headers=headers, json=body)
    print(f"Cleared approved_topics.json: {r.status_code}")

def generate_fresh_topics():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = "You are a content strategist. Respond ONLY with raw valid JSON. No markdown. No backticks. Start with { end with }."
    ctx = (
        "Tiffany Haynes voice: conviction-based, scripture-grounded, warm, real. Gods Math 1+1=10000.\n"
        "NEVER: divine, activate, em dashes, emojis, hustle cliches, fabricated quotes.\n"
        f"Recording: {recording_week} | Publishing: {publishing_week}\n"
    )
    schema = '{"number":N,"title":"5-8 word title","pillar":"P","content_type":"Talking Head or Teaching or Testimony or Lifestyle or Shenanigans","hook":"exact first 3 seconds","what_to_cover":["p1","p2","p3"],"why_this_works":"one sentence","scripture_angle":"or empty","estimated_length":"30 sec"}'
    pillar_groups = [
        ([1,2,3],  "Business and Entrepreneurship, Spiritual Development and Gods Math Teaching"),
        ([4,5,6],  "Family and Lifestyle, Community and Testimony"),
        ([7,8,9],  "Humor and Personality Shenanigans, Business and Entrepreneurship"),
        ([10,11,12],"Spiritual Development and Gods Math Teaching, Family and Lifestyle"),
    ]
    all_topics = []
    for nums, pillars in pillar_groups:
        items = [schema.replace("N", str(n)) for n in nums]
        prompt = ctx + f"Generate 3 fresh voiceover topics for pillars: {pillars}\nReturn ONLY: " + '{"topics":[' + ",".join(items) + "]}"
        msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=2500, system=system, messages=[{"role":"user","content":prompt}])
        raw = msg.content[0].text.strip().replace("```json","").replace("```","").strip()
        a = raw.find("{"); b = raw.rfind("}")
        batch = json.loads(raw[a:b+1])
        all_topics.extend(batch.get("topics", []))
    return {"recording_week": recording_week, "publishing_week": publishing_week, "planning_note": "", "topics": all_topics}

PILLAR_COLORS = {
    "Business and Entrepreneurship":                {"bg":"#FEF8EE","border":"#B87830","text":"#7A4E0D"},
    "Spiritual Development and Gods Math Teaching": {"bg":"#FFF5F5","border":"#A00605","text":"#7A0504"},
    "Family and Lifestyle":                         {"bg":"#F0FAF4","border":"#3A9E6E","text":"#1E6B48"},
    "Humor and Personality Shenanigans":            {"bg":"#F6F3FF","border":"#6A50A8","text":"#3D2980"},
    "Community and Testimony":                      {"bg":"#EFF6FF","border":"#3A6EA8","text":"#1E4B7A"},
}

def pc(pillar):
    return PILLAR_COLORS.get(pillar, {"bg":"#F8F8F8","border":"#999","text":"#555"})

def build_html(data, rec_week, pub_week, is_test=False):
    from urllib.parse import quote
    topics = data.get("topics", [])
    today = datetime.now().strftime("%B %-d, %Y")
    planning_note = data.get("planning_note", "")
    test_banner = '''<div style="background:#FFF3CD;border:2px solid #B87830;padding:12px 20px;text-align:center;font-family:Georgia,serif;font-size:13px;color:#7A4E0D;font-weight:700;">TEST EMAIL - Not sent to Tiffany</div>''' if is_test else ""

    # Build card HTML for each topic
    card_cells = []
    for t in topics:
        p = pc(t.get("pillar",""))
        pts = t.get("what_to_cover", [])
        if isinstance(pts, str):
            pts = [x.strip() for x in pts.split("\n") if x.strip()]
        li = "".join(f"<li style='margin-bottom:4px;'>{pt}</li>" for pt in pts)
        scr = t.get("scripture_angle","")
        scr_html = f'<div style="margin-top:8px;padding:6px 10px;border-left:3px solid {p["border"]};background:{p["bg"]};font-style:italic;font-size:11px;color:{p["text"]};">{scr}</div>' if scr else ""
        upload_topic = quote(t.get("title",""), safe="")
        upload_url = f"https://media.ebeprstudios.com/upload.html?topic={upload_topic}&cloud=dgq3ahq1m&preset=tiffany_voiceovers"

        card = f'''
<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E3D3C8;border-radius:8px;overflow:hidden;background:#FFFDF5;">
  <tr><td style="background:{p["bg"]};padding:10px 14px;border-bottom:1px solid {p["border"]}33;">
    <table cellpadding="0" cellspacing="0" width="100%"><tr>
      <td width="32" valign="top" style="padding-right:10px;">
        <div style="width:28px;height:28px;min-width:28px;min-height:28px;background:{p["border"]};border-radius:14px;text-align:center;line-height:28px;color:white;font-size:11px;font-weight:700;font-family:Georgia,serif;display:block;">{t.get("number","")}</div>
      </td>
      <td valign="top">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:2px;">{t.get("title","")}</div>
        <div style="font-size:9px;font-weight:700;color:{p["text"]};letter-spacing:1px;text-transform:uppercase;">{t.get("pillar","")} &bull; {t.get("estimated_length","")}</div>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:10px 14px;border-bottom:1px solid #E3D3C8;background:#FFFDF5;">
    <div style="font-size:8px;font-weight:700;color:#A00605;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">HOOK</div>
    <div style="font-size:12px;font-weight:600;font-style:italic;color:#414141;line-height:1.4;">&ldquo;{t.get("hook","")}&rdquo;</div>
  </td></tr>
  <tr><td style="padding:10px 14px;border-bottom:1px solid #E3D3C8;">
    <div style="font-size:8px;font-weight:700;color:#8A8A8A;letter-spacing:2px;text-transform:uppercase;margin-bottom:5px;">WHAT TO COVER</div>
    <ul style="margin:0;padding-left:16px;color:#5A5A5A;font-size:11px;line-height:1.65;">{li}</ul>{scr_html}
  </td></tr>
  <tr><td style="padding:10px 14px;background:#F4F0EB;">
    <div style="font-size:10px;color:#5A5A5A;margin-bottom:8px;"><span style="font-size:8px;font-weight:700;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;">WHY: </span>{t.get("why_this_works","")}</div>
    <a href="{upload_url}" style="display:block;text-align:center;background:#A00605;color:white;font-family:Georgia,serif;font-size:12px;font-weight:700;padding:8px 12px;border-radius:6px;text-decoration:none;">Submit Voiceover</a>
  </td></tr>
</table>'''
        card_cells.append(card)

    # Build single-column rows
    rows_html = ""
    for card in card_cells:
        rows_html += f'<tr><td style="padding:6px 0;">{card}</td></tr>'

    note_html = f'<p style="font-style:italic;color:#5A5A5A;font-size:13px;margin:0 0 12px;">{planning_note}</p>' if planning_note else ""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
{test_banner}
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;"><tr><td align="center" style="padding:24px 16px;">
<table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">
<tr><td style="background:#414141;border-radius:10px 10px 0 0;padding:24px 28px;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:4px;text-transform:uppercase;margin-bottom:6px;">TIFFANY HAYNES &amp; CO. MEDIA TEAM</div>
  <div style="font-size:24px;font-weight:700;color:#FFFDF5;margin-bottom:6px;">12 Voiceover Topics</div>
  <div style="font-size:12px;color:#B8B8B8;">Recording: {rec_week} &bull; Publishing: {pub_week}</div>
  <div style="font-size:11px;color:#8A8A8A;margin-top:3px;">Sent: {today}</div>
  <div style="margin-top:14px;">
    <a href="https://media.ebeprstudios.com/topics.html" style="display:inline-block;background:#C49E3C;color:#414141;font-family:Georgia,serif;font-size:13px;font-weight:700;padding:9px 20px;border-radius:8px;text-decoration:none;">View All Topics &amp; Submit Voiceovers</a>
  </div>
</td></tr>
<tr><td style="background:#FFFDF5;padding:20px 28px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  {note_html}

  <!-- HOW IT WORKS -->
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;text-align:center;">How This Works</div>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
    <tr>
      <td width="36" valign="top">
        <div style="width:30px;height:30px;background:#414141;border-radius:15px;text-align:center;line-height:30px;color:#C49E3C;font-size:12px;font-weight:700;font-family:Georgia,serif;">1</div>
      </td>
      <td valign="top" style="padding-left:10px;padding-bottom:14px;">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:3px;">Browse the 12 topics</div>
        <div style="font-size:12px;color:#5A5A5A;line-height:1.6;">Read through all the options below. Each one includes a hook, what to cover, and a scripture angle. Take your time and see what speaks to you.</div>
      </td>
    </tr>
    <tr>
      <td width="36" valign="top">
        <div style="width:30px;height:30px;background:#414141;border-radius:15px;text-align:center;line-height:30px;color:#C49E3C;font-size:12px;font-weight:700;font-family:Georgia,serif;">2</div>
      </td>
      <td valign="top" style="padding-left:10px;padding-bottom:14px;">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:3px;">Only record what sounds like YOU</div>
        <div style="font-size:12px;color:#5A5A5A;line-height:1.6;">Not every topic will resonate and that is completely okay. We recommend recording up to 5, but only choose the ones that feel natural and authentic to your voice and your story. If only 2 resonate this week, record those 2. Authenticity always wins over volume.</div>
      </td>
    </tr>
    <tr>
      <td width="36" valign="top">
        <div style="width:30px;height:30px;background:#414141;border-radius:15px;text-align:center;line-height:30px;color:#C49E3C;font-size:12px;font-weight:700;font-family:Georgia,serif;">3</div>
      </td>
      <td valign="top" style="padding-left:10px;padding-bottom:14px;">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:3px;">Record on your phone</div>
        <div style="font-size:12px;color:#5A5A5A;line-height:1.6;">Use your Voice Memos app or record directly in the browser. Speak naturally, like you are talking to a friend. You do not need a script. Just talk from your heart the way you always do.</div>
      </td>
    </tr>
    <tr>
      <td width="36" valign="top">
        <div style="width:30px;height:30px;background:#414141;border-radius:15px;text-align:center;line-height:30px;color:#C49E3C;font-size:12px;font-weight:700;font-family:Georgia,serif;">4</div>
      </td>
      <td valign="top" style="padding-left:10px;padding-bottom:14px;">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:3px;">Tap Submit Voiceover</div>
        <div style="font-size:12px;color:#5A5A5A;line-height:1.6;">Each topic card has a Submit Voiceover button. Tap it and your recording goes straight to the media team. No texting, no emailing, no extra steps.</div>
      </td>
    </tr>
    <tr>
      <td width="36" valign="top">
        <div style="width:30px;height:30px;background:#414141;border-radius:15px;text-align:center;line-height:30px;color:#C49E3C;font-size:12px;font-weight:700;font-family:Georgia,serif;">5</div>
      </td>
      <td valign="top" style="padding-left:10px;">
        <div style="font-size:13px;font-weight:700;color:#414141;margin-bottom:3px;">The team handles the rest</div>
        <div style="font-size:12px;color:#5A5A5A;line-height:1.6;">The Creative Theologian Media Group will begin editing your recordings the following week. Your content will be ready for publishing the week of {pub_week}. All you have to do is record and submit.</div>
      </td>
    </tr>
  </table>

  <!-- DIVIDER -->
  <div style="border-top:1px solid #E3D3C8;margin-bottom:18px;"></div>

  <!-- REMINDER BOX -->
  <div style="background:#F4F0EB;border-radius:8px;padding:14px 18px;border-left:4px solid #A00605;margin-bottom:4px;">
    <div style="font-size:12px;font-weight:700;color:#414141;margin-bottom:4px;">A note from your media team</div>
    <div style="font-size:12px;color:#5A5A5A;line-height:1.7;">These topics are suggestions, not assignments. They were created to serve your message, not the other way around. Trust your instincts. If a topic does not feel like you, skip it. The content that performs best is always the content that comes from a real place. Speak your truth and we will handle the rest. 1 + 1 = 10,000.</div>
  </div>

</td></tr>
<tr><td style="background:#FFFDF5;padding:8px 28px 20px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>
</td></tr>
<tr><td style="background:#414141;border-radius:0 0 10px 10px;padding:18px 28px;text-align:center;">
  <div style="font-size:14px;font-weight:700;color:#C49E3C;letter-spacing:3px;margin-bottom:4px;">1 + 1 = 10,000</div>
  <div style="font-size:10px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;">The Creative Theologian Media Group &bull; Internal Use Only</div>
</td></tr>
</table></td></tr></table></body></html>"""


def save_current_topics(data, rec_week, pub_week):
    """Save current topics to repo so topics.html can fetch them."""
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        print("No GitHub token - skipping current_topics.json save.")
        return
    try:
        payload = {
            "recording_week": rec_week,
            "publishing_week": pub_week,
            "saved_at": datetime.now().isoformat(),
            "topics": data.get("topics", [])
        }
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/current_topics.json"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        sha = None
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            sha = r.json().get("sha")
        content = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()
        body = {"message": f"Update current topics - {rec_week}", "content": content}
        if sha:
            body["sha"] = sha
        r2 = requests.put(url, headers=headers, json=body)
        print(f"Saved current_topics.json: {r2.status_code}")
    except Exception as e:
        print(f"Could not save current_topics.json: {e}")


    prefix = "[TEST] " if is_test else ""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{prefix}Your 12 Voiceover Topics - Week of {rec_week}"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email
    if cc_emails:
        msg["Cc"]  = cc_emails
    msg.attach(MIMEText(html, "html"))
    all_to = [to_email] + [e.strip() for e in cc_emails.split(",") if e.strip()]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, all_to, msg.as_string())
    print(f"Sent to {to_email}" + (f" CC: {cc_emails}" if cc_emails else ""))

if __name__ == "__main__":
    approved, sha = fetch_approved_topics()
    if approved:
        data      = approved
        is_test   = approved.get("test_mode", False)
        to_email  = approved.get("to_email", EMAIL_TO)
        cc_emails = approved.get("cc_emails", "") if not is_test else ""
        rec_week  = approved.get("recording_week", recording_week)
        pub_week  = approved.get("publishing_week", publishing_week)
    else:
        print("Generating fresh topics via Claude...")
        data      = generate_fresh_topics()
        is_test   = False
        to_email  = EMAIL_TO
        cc_emails = EMAIL_CC
        rec_week  = recording_week
        pub_week  = publishing_week

    html = build_html(data, rec_week, pub_week, is_test=is_test)
    save_current_topics(data, rec_week, pub_week)
    send_email(html, to_email, cc_emails, rec_week, is_test=is_test)
    if sha:
        delete_approved_file(sha)
    print("Done.")
