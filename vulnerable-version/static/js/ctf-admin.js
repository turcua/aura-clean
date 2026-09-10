// ============================================================================
// CTF ORGANIZER CONTROL PANEL - JAVASCRIPT
// Sprint 46
// ============================================================================

function setStatus(el, message, ok) {
    el.textContent = message;
    el.className = 'status-msg ' + (ok ? 'ok' : 'err');
}

async function loadMode() {
    const pill = document.getElementById('currentModePill');
    try {
        const res = await fetch('/api/ctf-admin/mode');
        const data = await res.json();
        if (data.success) {
            pill.textContent = data.mode;
            pill.className = 'mode-pill ' + data.mode;
        }
    } catch (e) {
        pill.textContent = 'unknown';
    }
}

async function setMode(mode) {
    const status = document.getElementById('modeStatus');
    try {
        const res = await fetch('/api/ctf-admin/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode }),
        });
        const data = await res.json();
        if (data.success) {
            setStatus(status, `Mode set to "${data.mode}".`, true);
            loadMode();
        } else {
            setStatus(status, 'Failed to set mode.', false);
        }
    } catch (e) {
        setStatus(status, 'Request failed.', false);
    }
}

async function seedVictims() {
    const status = document.getElementById('dataStatus');
    const btn = document.getElementById('seedBtn');
    btn.disabled = true;
    setStatus(status, 'Seeding…', true);
    try {
        const res = await fetch('/api/ctf-admin/seed', { method: 'POST' });
        const data = await res.json();
        setStatus(status, data.message || 'Done.', data.success);
    } catch (e) {
        setStatus(status, 'Request failed.', false);
    } finally {
        btn.disabled = false;
    }
}

async function resetCtf() {
    const status = document.getElementById('dataStatus');
    if (!confirm('This removes every user except testuser/admin, including all victims and anything created during a session. Continue?')) {
        return;
    }
    const btn = document.getElementById('resetBtn');
    btn.disabled = true;
    setStatus(status, 'Resetting…', true);
    try {
        const res = await fetch('/api/ctf-admin/reset', { method: 'POST' });
        const data = await res.json();
        setStatus(status, data.message || 'Done.', data.success);
    } catch (e) {
        setStatus(status, 'Request failed.', false);
    } finally {
        btn.disabled = false;
    }
}

async function loadPrefix() {
    const pill = document.getElementById('currentPrefix');
    const input = document.getElementById('prefixInput');
    try {
        const res = await fetch('/api/ctf-admin/flag-prefix');
        const data = await res.json();
        if (data.success) {
            pill.textContent = `current: ${data.prefix}{...}`;
            input.placeholder = data.prefix;
        }
    } catch (e) {
        pill.textContent = '';
    }
}

async function savePrefix() {
    const status = document.getElementById('prefixStatus');
    const input = document.getElementById('prefixInput');
    const prefix = input.value.trim();
    if (!prefix) {
        setStatus(status, 'Enter a prefix first.', false);
        return;
    }
    try {
        const res = await fetch('/api/ctf-admin/flag-prefix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prefix }),
        });
        const data = await res.json();
        if (data.success) {
            setStatus(status, `Prefix updated to "${data.prefix}". Only affects flags generated from now on.`, true);
            input.value = '';
            loadPrefix();
        } else {
            setStatus(status, data.message || 'Failed to update prefix.', false);
        }
    } catch (e) {
        setStatus(status, 'Request failed.', false);
    }
}

let lastFlags = [];
let auditView = 'time';

function renderAuditByTime(flags) {
    const rows = flags.map(f => `
        <tr>
            <td>${f.username}</td>
            <td>${f.vuln_id}</td>
            <td>${f.name || ''}</td>
            <td class="flag-val">${f.flag_value}</td>
            <td>${f.found_at || ''}</td>
        </tr>
    `).join('');
    return `
        <table class="audit-table">
            <thead>
                <tr><th>User</th><th>Vuln</th><th>Name</th><th>Flag</th><th>Found At</th></tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderAuditByVuln(flags) {
    const groups = new Map();
    flags.forEach(f => {
        if (!groups.has(f.vuln_id)) groups.set(f.vuln_id, { name: f.name, entries: [] });
        groups.get(f.vuln_id).entries.push(f);
    });
    const sortedIds = Array.from(groups.keys()).sort();
    return sortedIds.map(vulnId => {
        const group = groups.get(vulnId);
        const rows = group.entries.map(f => `
            <tr>
                <td>${f.username}</td>
                <td class="flag-val">${f.flag_value}</td>
                <td>${f.found_at || ''}</td>
            </tr>
        `).join('');
        return `
            <div class="vuln-group">
                <div class="vuln-group-heading"><span class="vuln-id-tag">${vulnId}</span>${group.name || ''}</div>
                <table class="audit-table">
                    <thead>
                        <tr><th>User</th><th>Flag</th><th>Found At</th></tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;
    }).join('');
}

function renderAudit() {
    const container = document.getElementById('auditContainer');
    if (lastFlags.length === 0) {
        container.innerHTML = '<div class="audit-empty">No flags issued yet.</div>';
        return;
    }
    container.innerHTML = auditView === 'vuln' ? renderAuditByVuln(lastFlags) : renderAuditByTime(lastFlags);
}

async function loadAudit() {
    const container = document.getElementById('auditContainer');
    container.innerHTML = '<div class="audit-empty">Loading…</div>';
    try {
        const res = await fetch('/api/ctf-admin/flags-audit');
        const data = await res.json();
        lastFlags = data.success ? data.flags : [];
        renderAudit();
    } catch (e) {
        container.innerHTML = '<div class="audit-empty">Couldn\'t load flags.</div>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadMode();
    loadPrefix();
    loadAudit();

    document.querySelectorAll('[data-mode]').forEach(btn => {
        btn.addEventListener('click', () => setMode(btn.getAttribute('data-mode')));
    });
    document.getElementById('seedBtn').addEventListener('click', seedVictims);
    document.getElementById('resetBtn').addEventListener('click', resetCtf);
    document.getElementById('prefixBtn').addEventListener('click', savePrefix);
    document.getElementById('refreshAuditBtn').addEventListener('click', loadAudit);

    document.querySelectorAll('.audit-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            auditView = tab.getAttribute('data-audit-view');
            document.querySelectorAll('.audit-tab').forEach(t => t.classList.toggle('is-active', t === tab));
            renderAudit();
        });
    });
});
