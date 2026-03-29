// ================================================================
// SEND PLAN TO CLIENT FOR APPROVAL
// ================================================================
async function sendPlanToClient() {
  if (!currentGeneratedPlan) { alert('No plan generated yet. Generate a plan first.'); return; }
  var token = getGithubToken();
  if (!token) { alert('No GitHub token saved. Enter your token in Email Preview settings first.'); return; }
  var tiffanyEmail = localStorage.getItem('tiffany_ep_email_tiffany') || '';
  if (!tiffanyEmail) { alert('Please enter Tiffany\'s email in the Email Preview settings first.'); return; }
  var repoFull = getGitHubRepo() || 'ebeprstudios/THCO-Social-Media-Manager';
  var btn = document.getElementById('send-client-btn');
  var statusEl = document.getElementById('send-client-status');
  btn.disabled = true; btn.textContent = 'Saving plan...';
  try {
    // STEP 1 — Save full plan to GitHub BEFORE dispatching (avoids client_payload size limit)
    var planFile = {
      plan: currentGeneratedPlan,
      week_of: currentGeneratedPlan.week_of || '',
      sent_to: tiffanyEmail,
      sent_at: new Date().toISOString(),
      status: 'pending'
    };
    await savePlanToGitHub(token, repoFull, planFile);

    // STEP 2 — Dispatch with minimal payload only (no plan data)
    btn.textContent = 'Sending...';
    var parts = repoFull.split('/');
    var res = await fetch('https://api.github.com/repos/' + parts[0] + '/' + parts[1] + '/dispatches', {
      method: 'POST',
      headers: { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: 'send_plan_to_client',
        client_payload: {
          week_of: currentGeneratedPlan.week_of || '',
          sent_to: tiffanyEmail,
          is_test: false
        }
      })
    });
    if (res.status === 204 || res.status === 200) {
      btn.textContent = 'Sent to Tiffany!';
      btn.style.background = 'var(--green)';
      if (statusEl) { statusEl.textContent = 'Plan emailed to ' + tiffanyEmail + '. Waiting for her approval.'; statusEl.style.display = 'block'; }
      setTimeout(function() { btn.disabled = false; btn.textContent = 'Resend to Tiffany'; btn.style.background = 'var(--red)'; }, 5000);
    } else {
      throw new Error('Workflow trigger returned ' + res.status);
    }
  } catch(e) {
    alert('Could not send plan: ' + e.message);
    btn.disabled = false; btn.textContent = 'Send to Tiffany for Approval';
    console.error(e);
  }
}

async function sendTestPlanEmail() {
  if (!currentGeneratedPlan) { alert('No plan generated yet. Generate a plan first.'); return; }
  var token = getGithubToken();
  if (!token) { alert('No GitHub token saved. Enter your token in Email Preview settings first.'); return; }
  var testEmail = localStorage.getItem('tiffany_ep_email_test') || '';
  if (!testEmail) { alert('No test email saved. Enter your test email in the Email Preview settings first.'); return; }
  var repoFull = getGitHubRepo() || 'ebeprstudios/THCO-Social-Media-Manager';
  var btn = document.getElementById('send-test-plan-btn');
  btn.disabled = true; btn.textContent = 'Saving plan...';
  try {
    // STEP 1 — Save full plan to GitHub BEFORE dispatching (avoids client_payload size limit)
    var planFile = {
      plan: currentGeneratedPlan,
      week_of: currentGeneratedPlan.week_of || '',
      sent_to: testEmail,
      sent_at: new Date().toISOString(),
      status: 'pending'
    };
    await savePlanToGitHub(token, repoFull, planFile);

    // STEP 2 — Dispatch with minimal payload only (no plan data)
    btn.textContent = 'Sending test...';
    var parts = repoFull.split('/');
    var res = await fetch('https://api.github.com/repos/' + parts[0] + '/' + parts[1] + '/dispatches', {
      method: 'POST',
      headers: { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: 'send_plan_to_client',
        client_payload: {
          week_of: currentGeneratedPlan.week_of || '',
          sent_to: testEmail,
          is_test: true
        }
      })
    });
    if (res.status === 204 || res.status === 200) {
      btn.textContent = 'Test Sent!';
      btn.style.borderColor = 'var(--green)';
      btn.style.color = 'var(--green)';
      setTimeout(function() { btn.disabled = false; btn.textContent = 'Send Test to Me'; btn.style.borderColor = 'var(--amber)'; btn.style.color = 'var(--amber)'; }, 4000);
    } else {
      throw new Error('Workflow returned ' + res.status);
    }
  } catch(e) {
    alert('Could not send test: ' + e.message);
    btn.disabled = false; btn.textContent = 'Send Test to Me';
    console.error(e);
  }
}
