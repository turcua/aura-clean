// ============================================================================
// CTF FLAG POPUP - JAVASCRIPT
// Sprint 43: Sound Breathing - Rapid Fire Slice
//
// App-wide (loaded from base.html for every logged-in page, not just
// /scoreboard) - polls GET /api/scoreboard/notifications and toasts
// anything not yet announced to this account, then immediately acks it.
//
// Bug fixed 2026-08-08 (found via real testing): the original version
// tracked "already shown" in localStorage, which is scoped to the browser,
// not the account - any fresh incognito window or different browser had
// no memory of what it already announced, so every legitimately-earned
// flag kept re-popping up. "Already notified" is now server-side truth
// (scoreboard_progress.notified_at), so it's consistent no matter which
// browser/device/session you're in.
// ============================================================================

const CTF_POLL_MS = 15000;

function ctfEnsureStack() {
    let stack = document.getElementById('ctfToastStack');
    if (!stack) {
        stack = document.createElement('div');
        stack.id = 'ctfToastStack';
        stack.className = 'ctf-toast-stack';
        document.body.appendChild(stack);
    }
    return stack;
}

function ctfShowToast(entry) {
    const stack = ctfEnsureStack();
    const toast = document.createElement('div');
    toast.className = 'ctf-toast';

    const flagHtml = entry.flag_value
        ? `<div class="ctf-toast-flag">${entry.flag_value}</div>`
        : '';

    toast.innerHTML = `
        <div class="ctf-toast-title">Vulnerability found</div>
        <div class="ctf-toast-name">${entry.vuln_id}${entry.name ? ' — ' + entry.name : ''}</div>
        ${flagHtml}
    `;

    stack.appendChild(toast);
    setTimeout(() => toast.remove(), 10000);
}

async function ctfAck(vulnId) {
    try {
        await fetch('/api/scoreboard/notifications/ack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vuln_id: vulnId }),
        });
    } catch (e) { /* best-effort */ }
}

async function ctfCheckFlags() {
    if (typeof window.CURRENT_USER_ID === 'undefined' || !window.CURRENT_USER_ID) return;

    try {
        const res = await fetch('/api/scoreboard/notifications');
        const data = await res.json();
        if (!data.success) return;

        for (const entry of data.notifications) {
            ctfShowToast(entry);
            await ctfAck(entry.vuln_id);
        }
    } catch (e) { /* best-effort, silent */ }
}

document.addEventListener('DOMContentLoaded', function () {
    ctfCheckFlags();
    setInterval(ctfCheckFlags, CTF_POLL_MS);
});
