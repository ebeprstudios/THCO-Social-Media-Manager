"""
log_voiceover.py
Triggered by GitHub Actions repository_dispatch when Cloudinary
sends a webhook notification after a voiceover upload.
"""
import json
import os
import base64
import requests
from datetime import datetime, timedelta

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO  = os.environ.get("GITHUB_REPOSITORY", "")

def get_week_label():
    d = datetime.now()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%b %-d") + " - " + sunday.strftime("%b %-d, %Y")

def parse_context(raw):
    """Parse Cloudinary context string 'key=val|key2=val2' into dict."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw.get("custom", raw)
    result = {}
    for pair in str(raw).split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result

if __name__ == "__main__":
    raw_payload = os.environ.get("PAYLOAD", "{}")
    payload = json.loads(raw_payload)
    context = parse_context(payload.get("context", {}))

    entry = {
        "id":       payload.get("public_id", ""),
        "url":      payload.get("secure_url", ""),
        "topic":    context.get("topic", payload.get("public_id","").split("/")[-1]),
        "filename": payload.get("public_id", "").split("/")[-1] + "." + payload.get("format", "m4a"),
        "date":     payload.get("created_at", "")[:10] if payload.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
        "duration": round(float(payload.get("duration", 0))) if payload.get("duration") else None,
        "bytes":    payload.get("bytes", 0),
        "format":   payload.get("format", "m4a"),
        "week":     get_week_label(),
        "source":   context.get("source", "uploaded"),
        "status":   "received"
    }

    print(f"Logging voiceover: {entry['topic']} on {entry['date']}")

    url = f"https://api.github.com/repos/{REPO}/contents/voiceovers_log.json"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    existing = []
    sha = None
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        sha = data.get("sha")
        try:
            existing = json.loads(base64.b64decode(data["content"].replace("\n","")).decode())
        except Exception:
            existing = []

    existing.insert(0, entry)
    if len(existing) > 100:
        existing = existing[:100]

    content = base64.b64encode(json.dumps(existing, indent=2).encode()).decode()
    body = {
        "message": f"Voiceover logged: {entry['topic']} ({entry['date']})",
        "content": content
    }
    if sha:
        body["sha"] = sha

    r2 = requests.put(url, headers=headers, json=body)
    print(f"GitHub log update: {r2.status_code}")
    if r2.status_code not in [200, 201]:
        print(f"Error: {r2.text[:200]}")
