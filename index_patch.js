// ─────────────────────────────────────────────────────────────────────────────
// PATCH: Add "Send Team Plan Email" button to index.html
// ─────────────────────────────────────────────────────────────────────────────
//
// STEP 1: Find this line in index.html (around line 2377):
//   h += '</div>';
//
//   ...which closes the "Send to Client" card. RIGHT AFTER IT, add:
//
// ─── INSERT THIS BLOCK (between the two existing cards) ──────────────────────

  h += '<div style="background:var(--cream-2);border:1px solid var(--border-md);border-radius:10px;padding:18px 20px;margin-bottom:14px;margin-top:14px;">';
  h += '<div style="font-size:10px;font-weight:700;color:var(--amber);letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">Send to Creative Team</div>';
  h += '<div style="font-size:13px;color:var(--charcoal2);margin-bottom:12px;line-height:1.6;">Sends the current <strong>team_plan_email.html</strong> file in the repo to Brittany and Diana. No new plan is generated. Update the file in GitHub whenever the plan changes.</div>';
  h += '<div style="display:flex;gap:10px;flex-wrap:wrap;">';
  h += '<button onclick="sendTeamPlanEmail(false)" id="send-team-btn" style="background:var(--amber);color:white;border:none;padding:12px 28px;border-radius:8px;font-family:Georgia,serif;font-size:14px;font-weight:700;cursor:pointer;">Send to Brittany + Diana</button>';
  h += '<button onclick="sendTeamPlanEmail(true)" id="send-team-test-btn" style="background:transparent;color:var(--amber);border:1.5px solid var(--amber);padding:12px 20px;border-radius:8px;font-family:Georgia,serif;font-size:13px;font-weight:600;cursor:pointer;">Send Test to Me</button>';
  h += '</div>';
  h += '<div id="send-team-status" style="display:none;margin-top:10px;font-size:12px;color:var(--green);font-weight:600;"></div>';
  h += '</div>';

// ─── END INSERT ───────────────────────────────────────────────────────────────
//
//
// STEP 2: Find the closing </script> tag near the bottom of index.html.
//         BEFORE IT, add the following JavaScript function:
//
// ─── INSERT THIS FUNCTION ────────────────────────────────────────────────────

async function sendTeamPlanEmail(isTest) {
  var token = getGithubToken();
  if (!token) { alert('No GitHub token saved. Enter your token in Email Preview settings first.'); return; }

  var repoFull = getGitHubRepo() || 'ebeprstudios/THCO-Social-Media-Manager';
  var btnId    = isTest ? 'send-team-test-btn' : 'send-team-btn';
  var btn      = document.getElementById(btnId);
  var statusEl = document.getElementById('send-team-status');

  if (isTest) {
    var testEmail = localStorage.getItem('tiffany_ep_email_test') || '';
    if (!testEmail) { alert('No test email saved. Enter your test email in the Email Preview settings first.'); return; }
  }

  var originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = isTest ? 'Sending test...' : 'Sending to team...';

  try {
    var parts = repoFull.split('/');
    var res = await fetch(
      'https://api.github.com/repos/' + parts[0] + '/' + parts[1] + '/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': 'token ' + token,
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: 'send_team_plan_email',
          client_payload: {
            subject:    'THCO Content Plan: April 5 to May 4',
            email_file: 'team_plan_email.html',
            is_test:    isTest
          }
        })
      }
    );

    if (res.status === 204 || res.status === 200) {
      btn.textContent = isTest ? 'Test Sent!' : 'Sent to Team!';
      btn.style.background = '#3A9E6E';
      if (statusEl) {
        statusEl.textContent = isTest
          ? 'Test email triggered. Check your inbox in ~30 seconds.'
          : 'Team email triggered. Brittany and Diana will receive it in ~30 seconds.';
        statusEl.style.display = 'block';
      }
      setTimeout(function() {
        btn.disabled = false;
        btn.textContent = originalText;
        btn.style.background = isTest ? 'transparent' : 'var(--amber)';
      }, 6000);
    } else {
      var errText = await res.text();
      throw new Error('Workflow trigger returned ' + res.status + ': ' + errText);
    }
  } catch(e) {
    alert('Could not trigger team email: ' + e.message);
    btn.disabled = false;
    btn.textContent = originalText;
    console.error(e);
  }
}

// ─── END INSERT ───────────────────────────────────────────────────────────────
