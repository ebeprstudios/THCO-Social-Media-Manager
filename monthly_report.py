"""
Tiffany Haynes & Co. — Monthly Client Report
Runs on the 20th of every month via GitHub Actions.
Reads approved plans, KB data, and voiceover submissions from the repo,
generates a comprehensive HTML report via Claude, and emails it to all parties.
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
from calendar import month_name

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
EMAIL_TO          = os.environ["EMAIL_TO"]
EMAIL_CC          = os.environ.get("EMAIL_CC", "")
REPORT_EMAIL      = os.environ.get("REPORT_EMAIL", EMAIL_TO)  # who gets the report
REPORT_CC         = os.environ.get("REPORT_CC", EMAIL_CC)
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")

now = datetime.now()
REPORT_MONTH = now.strftime("%B")
REPORT_YEAR  = now.strftime("%Y")
MONTH_LABEL  = f"{REPORT_MONTH} {REPORT_YEAR}"

# ── GITHUB HELPERS ─────────────────────────────────────────────────────────────
def gh_get(filename):
    """Fetch a JSON file from the repo. Returns parsed dict or None."""
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Could not fetch {filename}: {r.status_code}")
        return None
    try:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception as e:
        print(f"Could not parse {filename}: {e}")
        return None

def gh_save(filename, data, message):
    """Save a JSON file to the repo."""
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    sha = None
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")
    content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    body = {"message": message, "content": content}
    if sha:
        body["sha"] = sha
    requests.put(url, headers=headers, json=body)

# ── COLLECT DATA ───────────────────────────────────────────────────────────────
def collect_monthly_data():
    """Pull all relevant data from the repo for this month's report."""
    data = {
        "month": MONTH_LABEL,
        "approved_plans": [],
        "knowledge_base": [],
        "voiceovers": [],
        "current_topics": {}
    }

    # Approved weekly plans
    plans = gh_get("approved_plans_history.json")
    if plans:
        # Filter to this month
        month_plans = []
        for p in plans:
            try:
                approved_dt = datetime.fromisoformat(p.get("approved_at",""))
                if approved_dt.month == now.month and approved_dt.year == now.year:
                    month_plans.append(p)
            except Exception:
                pass
        data["approved_plans"] = month_plans
        print(f"Found {len(month_plans)} approved plans for {MONTH_LABEL}")
    else:
        print("No approved_plans_history.json found")

    # Knowledge base
    kb = gh_get("knowledge_base_snapshot.json")
    if kb:
        data["knowledge_base"] = kb if isinstance(kb, list) else [kb]
        print(f"Found knowledge base with {len(data['knowledge_base'])} entries")

    # Voiceover submissions
    vo = gh_get("voiceovers_log.json")
    if vo:
        data["voiceovers"] = vo if isinstance(vo, list) else [vo]
        print(f"Found {len(data['voiceovers'])} voiceover entries")

    # Current topics (for context)
    ct = gh_get("current_topics.json")
    if ct:
        data["current_topics"] = ct

    return data

# ── PILLAR BALANCE ─────────────────────────────────────────────────────────────
def calculate_pillar_balance(approved_plans):
    PILLARS = [
        "Business and Entrepreneurship",
        "Spiritual Development and Gods Math Teaching",
        "Family and Lifestyle",
        "Humor and Personality Shenanigans",
        "Community and Testimony"
    ]
    totals = {p: 0 for p in PILLARS}
    for plan in approved_plans:
        pb = plan.get("pillar_balance", {})
        for p in PILLARS:
            totals[p] += pb.get(p, 0)
    total_posts = sum(totals.values()) or 1
    percentages = {p: round((totals[p]/total_posts)*100) for p in PILLARS}
    target = 20
    overused  = [p for p in PILLARS if percentages[p] > target + 8]
    underused = [p for p in PILLARS if percentages[p] < target - 8]
    balanced  = [p for p in PILLARS if p not in overused and p not in underused]
    return {"totals": totals, "percentages": percentages, "overused": overused,
            "underused": underused, "balanced": balanced, "total_posts": total_posts}

# ── GENERATE REPORT VIA CLAUDE ────────────────────────────────────────────────
def generate_report(data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    plans = data["approved_plans"]
    kb    = data["knowledge_base"]
    vo    = data["voiceovers"]
    balance = calculate_pillar_balance(plans)

    # Build KB summary
    kb_summary = ""
    if kb:
        latest = kb[0].get("data", {}) if isinstance(kb[0], dict) else {}
        what_working = (latest.get("what_is_working") or [])[:5]
        attention    = (latest.get("what_needs_attention") or [])[:3]
        priorities   = (latest.get("strategic_priorities") or [])[:3]
        audience     = (latest.get("audience_insights") or [])[:3]
        kb_summary = f"""
PERFORMANCE DATA FROM KNOWLEDGE BASE:
What is working: {', '.join(what_working) or 'See uploaded reports'}
Needs attention: {', '.join(attention) or 'None flagged'}
Strategic priorities: {', '.join(priorities) or 'Continue current direction'}
Audience insights: {', '.join(audience) or 'See uploaded reports'}
"""

    # Build voiceover summary
    vo_summary = f"Voiceover submissions this month: {len(vo)}"

    # Build pillar summary
    pillar_lines = "\n".join([
        f"  {p}: {balance['totals'][p]} posts ({balance['percentages'][p]}%)"
        for p in balance["totals"]
    ])

    prompt = f"""You are the lead strategist for The Creative Theologian Media Group writing a monthly performance report for Tiffany Haynes.

MONTH: {MONTH_LABEL}
BRAND VOICE: Conviction-based, scripture-grounded, warm, real. Gods Math: 1+1=10000.
TONE: Start with clear data and insights, end with warmth, encouragement, and a forward-looking perspective. Professional but personal.

DATA FOR THIS MONTH:
Approved weekly plans: {len(plans)}
Total posts planned: {balance['total_posts']}
Voiceover submissions: {len(vo)}

PILLAR BALANCE:
{pillar_lines}
Overused pillars: {', '.join(balance['overused']) or 'None - well balanced'}
Underused pillars: {', '.join(balance['underused']) or 'None - well balanced'}
{kb_summary}

Write a monthly report with these exact sections. Return ONLY valid JSON. No markdown. Start with {{.

{{
  "executive_summary": "2-3 sentences. What happened this month overall. Warm but professional.",
  "content_output": {{
    "headline": "One punchy sentence about this month's content output",
    "detail": "2-3 sentences on what was planned, what was produced, and how it served the audience"
  }},
  "pillar_analysis": {{
    "headline": "One sentence on the pillar balance story this month",
    "detail": "2-3 sentences analyzing the balance. Which pillars performed, which need more attention, why it matters for the audience.",
    "recommendation": "One specific actionable recommendation for next month's pillar focus"
  }},
  "what_worked": ["3-5 specific things that worked this month. From KB data and plan history. Specific, not generic."],
  "opportunities": ["2-3 specific opportunities or gaps to address next month"],
  "next_month_priorities": ["3 concrete strategic priorities for next month"],
  "gods_math_moment": "One paragraph. A win, a breakthrough, or a moment of growth from this month that embodies the 1+1=10000 principle. Celebratory and genuine. End with scripture angle if applicable.",
  "closing_note": "One warm paragraph closing the report. From the team to Tiffany. Encouraging, specific, forward-looking. Feels personal not corporate. Sign off as The Creative Theologian Media Group."
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system="You are a content strategist writing client reports. Respond ONLY with raw valid JSON. No markdown. No backticks. Start with { end with }.",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    a = raw.find("{"); b = raw.rfind("}")
    return json.loads(raw[a:b+1]), balance

# ── BUILD HTML REPORT ──────────────────────────────────────────────────────────
PILLAR_COLORS = {
    "Business and Entrepreneurship":                {"bg":"#FEF8EE","border":"#B87830","text":"#7A4E0D"},
    "Spiritual Development and Gods Math Teaching": {"bg":"#FFF5F5","border":"#A00605","text":"#7A0504"},
    "Family and Lifestyle":                         {"bg":"#F0FAF4","border":"#3A9E6E","text":"#1E6B48"},
    "Humor and Personality Shenanigans":            {"bg":"#F6F3FF","border":"#6A50A8","text":"#3D2980"},
    "Community and Testimony":                      {"bg":"#EFF6FF","border":"#3A6EA8","text":"#1E4B7A"},
}

def build_report_html(report, balance, data):
    today = datetime.now().strftime("%B %-d, %Y")
    plans = data["approved_plans"]
    vo    = data["voiceovers"]

    # Pillar bars
    pillar_bars = ""
    for p, count in balance["totals"].items():
        pc = PILLAR_COLORS.get(p, {"bg":"#F8F8F8","border":"#999","text":"#555"})
        pct = balance["percentages"].get(p, 0)
        target = 20
        status = "Overused" if p in balance["overused"] else ("Underused" if p in balance["underused"] else "Balanced")
        status_color = "#A00605" if status == "Overused" else ("#B87830" if status == "Underused" else "#3A9E6E")
        short = p.replace("and Entrepreneurship","").replace("and Gods Math Teaching","").replace("and Lifestyle","").replace("and Personality Shenanigans","").replace("and Testimony","").strip()
        pillar_bars += f"""
<tr>
  <td style="padding:6px 12px 6px 0;font-size:12px;color:#414141;width:180px;font-weight:600;">{short}</td>
  <td style="padding:6px 8px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="background:#E3D3C8;border-radius:4px;height:8px;overflow:hidden;">
        <div style="width:{min(100,pct)}%;height:8px;background:{pc['border']};border-radius:4px;"></div>
      </td>
    </tr></table>
  </td>
  <td style="padding:6px 0 6px 8px;font-size:11px;color:#5A5A5A;width:60px;text-align:right;">{count} posts</td>
  <td style="padding:6px 0 6px 8px;width:70px;">
    <span style="font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px;background:{pc['bg']};color:{status_color};">{status}</span>
  </td>
</tr>"""

    # What worked list
    what_worked_html = "".join([
        f'<tr><td style="padding:5px 0;border-bottom:1px solid #F4F0EB;"><table cellpadding="0" cellspacing="0"><tr><td style="width:20px;vertical-align:top;padding-top:2px;"><div style="width:8px;height:8px;background:#3A9E6E;border-radius:50%;"></div></td><td style="font-size:13px;color:#414141;line-height:1.6;padding-left:8px;">{item}</td></tr></table></td></tr>'
        for item in (report.get("what_worked") or [])
    ])

    # Opportunities list
    opps_html = "".join([
        f'<tr><td style="padding:5px 0;border-bottom:1px solid #F4F0EB;"><table cellpadding="0" cellspacing="0"><tr><td style="width:20px;vertical-align:top;padding-top:2px;"><div style="width:8px;height:8px;background:#B87830;border-radius:50%;"></div></td><td style="font-size:13px;color:#414141;line-height:1.6;padding-left:8px;">{item}</td></tr></table></td></tr>'
        for item in (report.get("opportunities") or [])
    ])

    # Next month priorities
    priorities_html = "".join([
        f'<tr><td style="padding:8px 14px;background:#F4F0EB;border-radius:7px;margin-bottom:6px;font-size:13px;color:#414141;line-height:1.6;border-left:3px solid #A00605;display:block;margin-bottom:6px;">{i+1}. {item}</td></tr>'
        for i, item in enumerate(report.get("next_month_priorities") or [])
    ])

    content_output = report.get("content_output", {})
    pillar_analysis = report.get("pillar_analysis", {})

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Monthly Report - {MONTH_LABEL}</title></head>
<body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;">
<tr><td align="center" style="padding:28px 16px 40px;">
<table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

<!-- HEADER -->
<tr><td style="background:#414141;border-radius:12px 12px 0 0;padding:28px 32px;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:4px;text-transform:uppercase;margin-bottom:8px;">THE CREATIVE THEOLOGIAN MEDIA GROUP</div>
  <div style="font-size:28px;font-weight:700;color:#FFFDF5;margin-bottom:4px;">Monthly Performance Report</div>
  <div style="font-size:16px;color:#B8B8B8;margin-bottom:12px;">{MONTH_LABEL}</div>
  <div style="font-size:11px;color:#8A8A8A;">Prepared for: Tiffany Haynes &bull; Sent: {today}</div>
</td></tr>

<!-- GOLD DIVIDER -->
<tr><td style="height:4px;background:linear-gradient(90deg,#C49E3C,#B87830,#C49E3C);"></td></tr>

<!-- EXECUTIVE SUMMARY -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">Executive Summary</div>
  <div style="font-size:14px;color:#414141;line-height:1.8;font-style:italic;border-left:3px solid #C49E3C;padding-left:14px;">{report.get('executive_summary','')}</div>
</td></tr>

<!-- STATS ROW -->
<tr><td style="background:#F4F0EB;padding:16px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="text-align:center;padding:14px;background:#FFFDF5;border:1px solid #E3D3C8;border-radius:8px;">
      <div style="font-size:28px;font-weight:700;color:#A00605;font-family:Georgia,serif;">{len(plans)}</div>
      <div style="font-size:9px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;">Weekly Plans<br>Approved</div>
    </td>
    <td width="12"></td>
    <td style="text-align:center;padding:14px;background:#FFFDF5;border:1px solid #E3D3C8;border-radius:8px;">
      <div style="font-size:28px;font-weight:700;color:#414141;font-family:Georgia,serif;">{balance['total_posts']}</div>
      <div style="font-size:9px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;">Total Posts<br>Planned</div>
    </td>
    <td width="12"></td>
    <td style="text-align:center;padding:14px;background:#FFFDF5;border:1px solid #E3D3C8;border-radius:8px;">
      <div style="font-size:28px;font-weight:700;color:#3A9E6E;font-family:Georgia,serif;">{len(vo)}</div>
      <div style="font-size:9px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;">Voiceovers<br>Submitted</div>
    </td>
    <td width="12"></td>
    <td style="text-align:center;padding:14px;background:#FFFDF5;border:1px solid #E3D3C8;border-radius:8px;">
      <div style="font-size:28px;font-weight:700;color:#B87830;font-family:Georgia,serif;">{len(balance['balanced'])}/5</div>
      <div style="font-size:9px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;">Pillars<br>Balanced</div>
    </td>
  </tr></table>
</td></tr>

<!-- CONTENT OUTPUT -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;border-top:1px solid #E3D3C8;">
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">Content Output</div>
  <div style="font-size:15px;font-weight:700;color:#414141;margin-bottom:8px;">{content_output.get('headline','')}</div>
  <div style="font-size:13px;color:#5A5A5A;line-height:1.75;">{content_output.get('detail','')}</div>
</td></tr>

<!-- PILLAR BALANCE -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;border-top:1px solid #E3D3C8;">
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">Pillar Balance</div>
  <div style="font-size:15px;font-weight:700;color:#414141;margin-bottom:12px;">{pillar_analysis.get('headline','')}</div>
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;">{pillar_bars}</table>
  <div style="font-size:13px;color:#5A5A5A;line-height:1.75;margin-bottom:10px;">{pillar_analysis.get('detail','')}</div>
  <div style="background:#EFF6FF;border:1px solid rgba(58,110,168,0.2);border-radius:7px;padding:12px 16px;font-size:12px;color:#1E4B7A;line-height:1.7;">
    <strong>Recommendation for next month:</strong> {pillar_analysis.get('recommendation','')}
  </div>
</td></tr>

<!-- WHAT WORKED -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;border-top:1px solid #E3D3C8;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr valign="top">
    <td width="48%">
      <div style="font-size:10px;font-weight:700;color:#3A9E6E;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">What Worked</div>
      <table width="100%" cellpadding="0" cellspacing="0">{what_worked_html}</table>
    </td>
    <td width="4%"></td>
    <td width="48%">
      <div style="font-size:10px;font-weight:700;color:#B87830;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">Opportunities</div>
      <table width="100%" cellpadding="0" cellspacing="0">{opps_html}</table>
    </td>
  </tr></table>
</td></tr>

<!-- NEXT MONTH PRIORITIES -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;border-top:1px solid #E3D3C8;">
  <div style="font-size:10px;font-weight:700;color:#A00605;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;">Strategic Priorities — Next Month</div>
  <table width="100%" cellpadding="0" cellspacing="0">
    {"".join([f'<tr><td style="padding:8px 14px;background:#F4F0EB;border-radius:7px;font-size:13px;color:#414141;line-height:1.6;border-left:3px solid #A00605;margin-bottom:6px;display:block;">{i+1}. {item}</td></tr><tr><td height="6"></td></tr>' for i, item in enumerate(report.get("next_month_priorities") or [])])}
  </table>
</td></tr>

<!-- GODS MATH MOMENT -->
<tr><td style="background:#414141;padding:24px 32px;border-left:1px solid #333;border-right:1px solid #333;">
  <div style="font-size:10px;font-weight:700;color:#C49E3C;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">God's Math Moment</div>
  <div style="font-size:14px;color:#FFFDF5;line-height:1.85;font-style:italic;">{report.get('gods_math_moment','')}</div>
  <div style="font-size:20px;font-weight:700;color:#C49E3C;letter-spacing:4px;margin-top:16px;text-align:center;">1 + 1 = 10,000</div>
</td></tr>

<!-- CLOSING NOTE -->
<tr><td style="background:#FFFDF5;padding:24px 32px;border-left:1px solid #E3D3C8;border-right:1px solid #E3D3C8;border-top:1px solid #E3D3C8;">
  <div style="font-size:10px;font-weight:700;color:#8A8A8A;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;">A Note From Your Team</div>
  <div style="font-size:13px;color:#5A5A5A;line-height:1.85;">{report.get('closing_note','')}</div>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#414141;border-radius:0 0 12px 12px;padding:18px 32px;text-align:center;">
  <div style="font-size:11px;color:#8A8A8A;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">The Creative Theologian Media Group</div>
  <div style="font-size:10px;color:#666;">Monthly Report &bull; {MONTH_LABEL} &bull; Confidential</div>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""

# ── SEND EMAIL ─────────────────────────────────────────────────────────────────
def send_report(html):
    to_email  = REPORT_EMAIL or EMAIL_TO
    cc_emails = REPORT_CC or EMAIL_CC

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your Monthly Performance Report — {MONTH_LABEL} | Tiffany Haynes & Co."
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email
    if cc_emails:
        msg["Cc"]  = cc_emails

    msg.attach(MIMEText(html, "html"))

    all_to = [to_email.strip()]
    if cc_emails:
        all_to += [e.strip() for e in cc_emails.split(",") if e.strip()]
    all_to = list(set(all_to))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, all_to, msg.as_string())

    print(f"Monthly report sent to {to_email}" + (f" + CC: {cc_emails}" if cc_emails else ""))

# ── SAVE SNAPSHOT FOR HISTORY ──────────────────────────────────────────────────
def save_report_log(balance, data):
    """Save a compact log entry so future reports have historical context."""
    log = gh_get("report_history.json") or []
    entry = {
        "month": MONTH_LABEL,
        "sent_at": datetime.now().isoformat(),
        "plans_count": len(data["approved_plans"]),
        "total_posts": balance["total_posts"],
        "voiceovers": len(data["voiceovers"]),
        "pillar_balance": balance["percentages"],
        "overused": balance["overused"],
        "underused": balance["underused"]
    }
    log.append(entry)
    # Keep last 24 months
    if len(log) > 24:
        log = log[-24:]
    gh_save("report_history.json", log, f"Report log - {MONTH_LABEL}")
    print(f"Report log saved. Total entries: {len(log)}")

# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting monthly report for {MONTH_LABEL}...")

    data = collect_monthly_data()
    print("Data collected. Generating report via Claude...")

    report, balance = generate_report(data)
    print("Report generated. Building HTML...")

    html = build_report_html(report, balance, data)
    print("HTML built. Sending email...")

    send_report(html)
    save_report_log(balance, data)

    print(f"Monthly report for {MONTH_LABEL} complete.")
