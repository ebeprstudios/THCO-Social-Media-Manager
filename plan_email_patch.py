# ═══════════════════════════════════════════════════════════════
# plan_email.py — PATCH
# Replace TWO sections in your existing plan_email.py:
#
#  SECTION 1: The "Save plan to GitHub" block (~lines 584-612)
#  SECTION 2: The auto-regenerate save block (~lines 763-784)
#
# What changed:
#   - Each plan now saves to plans/plan_{token}.json (unique file)
#   - pending_plan.json is ALSO updated (backward compat)
#   - The approval URL now includes &token={token}
#   - Token is derived from week_of (e.g. "apr6_apr19_2026")
# ═══════════════════════════════════════════════════════════════

import re

def make_plan_token(week_of):
    """
    Convert week_of string to a safe URL token.
    e.g. "April 6 - April 19, 2026" -> "apr6_apr19_2026"
         "Mar 30 - Apr 12, 2026"    -> "mar30_apr12_2026"
    """
    # Remove commas, lowercase
    s = week_of.lower().replace(",", "").strip()
    # Replace " - " separator
    s = re.sub(r'\s*-\s*', '_', s)
    # Collapse spaces to underscore
    s = re.sub(r'\s+', '_', s)
    # Keep only alphanumeric and underscore
    s = re.sub(r'[^a-z0-9_]', '', s)
    # Trim to reasonable length
    return s[:40] or 'plan'


# ───────────────────────────────────────────────────────────────
# SECTION 1 REPLACEMENT
# Find this block in plan_email.py (around line 584):
#
#   # Save plan to GitHub so plan_approval.html can load it
#   ...
#   approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"
#
# Replace the ENTIRE block with this:
# ───────────────────────────────────────────────────────────────

def save_plan_and_build_url(plan, week_of, recipient, GITHUB_REPOSITORY, GITHUB_TOKEN, UPLOAD_TOKEN):
    import base64, json, requests
    from datetime import datetime

    upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
    plan_token = make_plan_token(week_of)

    plan_file = {
        "plan": plan,
        "week_of": week_of,
        "sent_to": recipient,
        "sent_at": datetime.now().isoformat(),
        "status": "pending",
        "plan_token": plan_token
    }
    headers_gh = {
        "Authorization": f"token {UPLOAD_TOKEN or GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    content_b64 = base64.b64encode(json.dumps(plan_file, indent=2).encode()).decode()

    def upsert_file(filename, message):
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{filename}"
        r = requests.get(url, headers=headers_gh)
        sha = r.json().get("sha") if r.status_code == 200 else None
        body = {"message": message, "content": content_b64}
        if sha:
            body["sha"] = sha
        r2 = requests.put(url, headers=headers_gh, json=body)
        print(f"Saved {filename}: {r2.status_code}")
        return r2.status_code

    # Save to unique plan file (the fix — approval page loads this by token)
    upsert_file(
        f"plans/plan_{plan_token}.json",
        f"Plan saved — {week_of} (token: {plan_token})"
    )

    # Also update pending_plan.json for backward compatibility
    upsert_file(
        "pending_plan.json",
        f"Weekly plan for {week_of}"
    )

    # Build approval URL with token
    repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
    approval_url = (
        f"https://media.ebeprstudios.com/plan_approval.html"
        f"?repo={repo_encoded}"
        f"&ght={upload_token}"
        f"&token={plan_token}"   # <-- THE FIX
    )
    return approval_url


# ───────────────────────────────────────────────────────────────
# HOW TO USE IN YOUR EXISTING plan_email.py
#
# In the send_plan block, replace:
#
#   # Save plan to GitHub so plan_approval.html can load it
#   try:
#       plan_file = { ... }
#       url = f"...pending_plan.json"
#       ...
#       r2 = requests.put(url, headers=headers, json=body)
#       print(f"Plan saved to GitHub: {r2.status_code}")
#   except Exception as e:
#       print(f"Could not save plan to GitHub: {e}")
#
#   # Build approval URL with token
#   upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
#   repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
#   approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"
#
# With this:
#
#   try:
#       approval_url = save_plan_and_build_url(
#           plan, week_of, recipient,
#           GITHUB_REPOSITORY, GITHUB_TOKEN, UPLOAD_TOKEN
#       )
#       print(f"Plan saved. Approval URL: {approval_url}")
#   except Exception as e:
#       print(f"Could not save plan to GitHub: {e}")
#       upload_token = UPLOAD_TOKEN or GITHUB_TOKEN
#       repo_encoded = GITHUB_REPOSITORY.replace("/", "%2F")
#       approval_url = f"https://media.ebeprstudios.com/plan_approval.html?repo={repo_encoded}&ght={upload_token}"
#
# ───────────────────────────────────────────────────────────────
# SECTION 2 REPLACEMENT
# In the auto-regenerate block (run_notify_team, action == "rejected"),
# replace the raw GitHub save + approval_url lines with the same helper:
#
#   approval_url = save_plan_and_build_url(
#       new_plan, new_week_of, EMAIL_TO,
#       GITHUB_REPOSITORY, GITHUB_TOKEN, UPLOAD_TOKEN
#   )
# ───────────────────────────────────────────────────────────────

