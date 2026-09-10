// Aura Financial Tracker - Secure Version
// Admin panel JS — Sprint 57 (ENH-02)

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    wireSearch();
    wireActionButtons();
    loadDefaultCategories();
    wireDefaultCategoryModal();
    loadAiUsage();
    loadSchedulerHealth();
    loadImpersonationLog();
});

async function loadStats() {
    try {
        const r = await fetch('/api/admin/stats');
        const j = await r.json();
        if (!j.success) return;
        document.getElementById('statTotalUsers').textContent = j.total_users;
        document.getElementById('statTotalTransactions').textContent = j.total_transactions;
        document.getElementById('statRecentSignups').textContent = j.recent_signups;
    } catch (e) {
        console.error('Failed to load admin stats:', e);
    }
}

function wireSearch() {
    const input = document.getElementById('userSearchInput');
    input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        document.querySelectorAll('#usersTableBody tr').forEach(row => {
            const match = !q || row.dataset.username.includes(q) || row.dataset.email.includes(q);
            row.style.display = match ? '' : 'none';
        });
    });
}

function wireActionButtons() {
    document.querySelectorAll('.admin-action-btn').forEach(btn => {
        btn.addEventListener('click', () => handleAction(btn));
    });
}

async function handleAction(btn) {
    const action = btn.dataset.action;
    const userId = btn.dataset.userId;
    const userName = btn.dataset.userName;

    const config = {
        'set-admin': {
            title: btn.dataset.current === 'true' ? 'Remove admin access?' : 'Grant admin access?',
            text: `${btn.dataset.current === 'true' ? 'Demote' : 'Promote'} "${userName}"? This takes effect the next time they log in.`,
            confirmButtonColor: '#7c3aed',
        },
        'set-active': {
            title: btn.dataset.current === 'true' ? 'Lock this account?' : 'Unlock this account?',
            text: btn.dataset.current === 'true'
                ? `Lock "${userName}"'s account? They won't be able to log in until unlocked.`
                : `Unlock "${userName}"'s account? Also clears any lockout counters.`,
            confirmButtonColor: '#7c3aed',
        },
        'invalidate-sessions': {
            title: 'Force logout?',
            text: `Force "${userName}" to re-authenticate on every device? Their current sessions stop working immediately.`,
            confirmButtonColor: '#f59e0b',
        },
        'delete': {
            title: 'Delete this user?',
            text: `Permanently delete "${userName}" and everything they own (transactions, accounts, loans, budgets, goals, etc.). This cannot be undone.`,
            confirmButtonColor: '#ef4444',
        },
        'impersonate': {
            title: 'View as this user?',
            text: `You'll see and act in the app as "${userName}" — full access, not just a read-only view. A banner will stay visible the whole time, with a button to return to your own account.`,
            confirmButtonColor: '#7c3aed',
        },
    }[action];

    const result = await Swal.fire({
        title: config.title,
        text: config.text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: action === 'delete' ? 'Delete' : 'Confirm',
        cancelButtonText: 'Cancel',
        confirmButtonColor: config.confirmButtonColor,
    });
    if (!result.isConfirmed) return;

    try {
        const r = await fetch(`/api/admin/users/${userId}/${action}`, { method: 'POST' });
        const j = await r.json();
        if (!j.success) {
            Swal.fire({ icon: 'error', title: 'Error', text: j.message });
            return;
        }
        if (action === 'impersonate') {
            // The whole point is to now be viewing as that user — go to
            // the dashboard, not back to /admin (which they're no longer
            // authorized for as a non-admin session).
            window.location.href = '/dashboard';
            return;
        }
        // Simplest correct option: reload to reflect the new state
        // (status badges, button labels, and — for delete — the row
        // itself) rather than hand-patch each of the four action types'
        // worth of DOM changes individually.
        window.location.reload();
    } catch (e) {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Server error, please try again.' });
    }
}

// ── Shared/default category management (ENH-02 group 3) ────────────────

async function loadDefaultCategories() {
    const body = document.getElementById('defaultCategoriesTableBody');
    try {
        const r = await fetch('/api/admin/categories');
        const j = await r.json();
        if (!j.success) return;

        body.innerHTML = '';
        if (j.categories.length === 0) {
            body.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px 0;color:var(--th);">No shared categories yet.</td></tr>';
            return;
        }
        j.categories.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(c.name)}</td>
                <td>${c.type}</td>
                <td><span class="glass-badge" style="background-color:${c.color};padding:3px 12px;">&nbsp;</span></td>
                <td>${c.usage_count} transaction${c.usage_count !== 1 ? 's' : ''}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-secondary" style="font-size:0.72rem;padding:3px 8px;"
                            data-dc-edit="${c.id}" data-dc-name="${escapeHtml(c.name)}" data-dc-type="${c.type}" data-dc-color="${c.color}">Edit</button>
                    <button class="btn btn-secondary" style="font-size:0.72rem;padding:3px 8px;color:#fca5a5;"
                            data-dc-delete="${c.id}" data-dc-name="${escapeHtml(c.name)}" data-dc-usage="${c.usage_count}">Delete</button>
                </td>`;
            body.appendChild(tr);
        });

        body.querySelectorAll('[data-dc-edit]').forEach(btn => {
            btn.addEventListener('click', () => openDefaultCategoryModal(btn.dataset));
        });
        body.querySelectorAll('[data-dc-delete]').forEach(btn => {
            btn.addEventListener('click', () => deleteDefaultCategory(btn.dataset));
        });
    } catch (e) {
        body.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px 0;color:var(--dn);">Error loading categories.</td></tr>';
    }
}

// Minimal HTML-escaping for category names rendered via innerHTML above —
// unlike vulnerable-version, this template string isn't an intentional
// injection surface, so user-controlled text (the category name) needs
// escaping before going into it.
function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

function wireDefaultCategoryModal() {
    document.getElementById('addDefaultCategoryBtn').addEventListener('click', () => openDefaultCategoryModal(null));
    document.getElementById('dc_color').addEventListener('input', function () {
        document.getElementById('dc_color_preview').style.backgroundColor = this.value;
    });
    document.getElementById('saveDefaultCategoryBtn').addEventListener('click', saveDefaultCategory);
}

function openDefaultCategoryModal(existing) {
    const form = document.getElementById('defaultCategoryForm');
    form.reset();
    document.getElementById('defaultCategoryModalTitle').textContent = existing ? 'Edit Shared Category' : 'Add Shared Category';
    document.getElementById('dc_category_id').value = existing ? existing.dcEdit : '';
    document.getElementById('dc_name').value = existing ? existing.dcName : '';
    document.getElementById(existing && existing.dcType === 'income' ? 'dc_type_income' : 'dc_type_expense').checked = true;
    const color = existing ? existing.dcColor : '#6c757d';
    document.getElementById('dc_color').value = color;
    document.getElementById('dc_color_preview').style.backgroundColor = color;

    new bootstrap.Modal(document.getElementById('defaultCategoryModal')).show();
}

async function saveDefaultCategory() {
    const categoryId = document.getElementById('dc_category_id').value;
    const name = document.getElementById('dc_name').value.trim();
    const type = document.querySelector('#defaultCategoryForm input[name="type"]:checked').value;
    const color = document.getElementById('dc_color').value;

    if (!name) {
        Swal.fire({ icon: 'error', title: 'Name required', text: 'Please enter a category name.' });
        return;
    }

    const url = categoryId ? `/api/admin/categories/${categoryId}/update` : '/api/admin/categories/create';
    try {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type, color }),
        });
        const j = await r.json();
        if (!j.success) {
            Swal.fire({ icon: 'error', title: 'Error', text: j.message });
            return;
        }
        bootstrap.Modal.getInstance(document.getElementById('defaultCategoryModal')).hide();
        loadDefaultCategories();
    } catch (e) {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Server error, please try again.' });
    }
}

// ── Impersonation audit log (ENH-02 group 6) ────────────────────────────

async function loadImpersonationLog() {
    const body = document.getElementById('impersonationLogTableBody');
    try {
        const r = await fetch('/api/admin/impersonation-log');
        const j = await r.json();
        if (!j.success) return;

        body.innerHTML = '';
        if (j.events.length === 0) {
            body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px 0;color:var(--th);">No impersonation events yet.</td></tr>';
            return;
        }
        j.events.forEach(ev => {
            const tr = document.createElement('tr');
            const endedCell = ev.ended_at
                ? escapeHtml(ev.ended_at)
                : '<span class="glass-badge" style="background:rgba(245,158,11,0.18);color:#fcd34d;">Still active</span>';
            tr.innerHTML = `
                <td>${escapeHtml(ev.admin_username)}</td>
                <td>${escapeHtml(ev.target_username)}</td>
                <td>${escapeHtml(ev.started_at)}</td>
                <td>${endedCell}</td>`;
            body.appendChild(tr);
        });
    } catch (e) {
        body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px 0;color:var(--dn);">Error loading impersonation log.</td></tr>';
    }
}

// ── Scheduler job health (ENH-02 group 5) ───────────────────────────────

async function loadSchedulerHealth() {
    const body = document.getElementById('schedulerHealthTableBody');
    try {
        const r = await fetch('/api/admin/scheduler-health');
        const j = await r.json();
        if (!j.success) return;

        body.innerHTML = '';
        j.jobs.forEach(job => {
            const tr = document.createElement('tr');
            let statusBadge;
            if (job.status === 'success') {
                statusBadge = '<span class="glass-badge" style="background:rgba(34,197,94,0.18);color:#86efac;">Success</span>';
            } else if (job.status === 'error') {
                statusBadge = `<span class="glass-badge" style="background:rgba(239,68,68,0.18);color:#fca5a5;" title="${escapeHtml(job.error_message || '')}">Error</span>`;
            } else {
                statusBadge = '<span class="glass-badge" style="background:rgba(148,163,184,0.18);color:#cbd5e1;">Never run</span>';
            }
            tr.innerHTML = `
                <td>${escapeHtml(job.label)}</td>
                <td>${escapeHtml(job.schedule)}</td>
                <td>${job.last_run || '—'}</td>
                <td>${statusBadge}</td>
                <td>${job.result_count !== null ? job.result_count : '—'}</td>`;
            body.appendChild(tr);
        });
    } catch (e) {
        body.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px 0;color:var(--dn);">Error loading scheduler health.</td></tr>';
    }
}

// ── AI advisor usage visibility (ENH-02 group 4) ────────────────────────

async function loadAiUsage() {
    const body = document.getElementById('aiUsageTableBody');
    try {
        const r = await fetch('/api/admin/ai-usage');
        const j = await r.json();
        if (!j.success) return;

        body.innerHTML = '';
        j.usage.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(u.username)}</td>
                <td>${u.prompts_sent}</td>
                <td>${u.total_messages}</td>
                <td>${u.last_activity || 'Never'}</td>`;
            body.appendChild(tr);
        });
    } catch (e) {
        body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px 0;color:var(--dn);">Error loading AI usage.</td></tr>';
    }
}

async function deleteDefaultCategory(data) {
    const usage = parseInt(data.dcUsage, 10);
    const result = await Swal.fire({
        title: 'Delete this shared category?',
        text: usage > 0
            ? `"${data.dcName}" is used by ${usage} transaction${usage !== 1 ? 's' : ''} across every user who has one — deleting it sets those transactions to uncategorized, it does not delete the transactions themselves. This cannot be undone.`
            : `Delete "${data.dcName}"? This cannot be undone.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#ef4444',
    });
    if (!result.isConfirmed) return;

    try {
        const r = await fetch(`/api/admin/categories/${data.dcDelete}/delete`, { method: 'POST' });
        const j = await r.json();
        if (!j.success) {
            Swal.fire({ icon: 'error', title: 'Error', text: j.message });
            return;
        }
        loadDefaultCategories();
    } catch (e) {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Server error, please try again.' });
    }
}
