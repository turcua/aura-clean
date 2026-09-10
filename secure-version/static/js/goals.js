/**
 * Aura Financial Tracker - Secure Version
 * Savings Goals page controller
 * Sprint 13: Transfers + Budgets + Savings Goals
 *
 * Loaded as an external <script src> (CSP script-src 'self' — no inline
 * scripts/onclick, see categories.js for the full rationale). Every
 * interactive element is wired with addEventListener and every dynamic
 * node built with document.createElement / textContent.
 */

let accountsMap = {};

function getAccountName(accountId) {
    return accountsMap[accountId] || `Account #${accountId}`;
}

document.addEventListener('DOMContentLoaded', function() {
    loadAccounts(loadGoals);
    document.getElementById('saveGoalBtn').addEventListener('click', saveGoal);
    document.getElementById('updateGoalBtn').addEventListener('click', updateGoal);
    document.getElementById('saveProgressBtn').addEventListener('click', saveProgress);
    document.getElementById('addTargetAmount').addEventListener('input', () => recalcTimeline('add'));
    document.getElementById('addTargetDate').addEventListener('input', () => calcFromDeadline('add'));
    document.getElementById('addMonthlyTarget').addEventListener('input', () => calcFromMonthly('add'));
});

function loadAccounts(callback) {
    fetch('/api/accounts/list')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                data.accounts.forEach(a => { accountsMap[a.id] = a.name; });
                ['addGoalAccount', 'editGoalAccount'].forEach(id => {
                    const sel = document.getElementById(id);
                    if (!sel) return;
                    sel.innerHTML = '';
                    const noneOpt = document.createElement('option');
                    noneOpt.value = '';
                    noneOpt.textContent = '-- None --';
                    sel.appendChild(noneOpt);
                    data.accounts.forEach(a => {
                        const opt = document.createElement('option');
                        opt.value = a.id;
                        opt.textContent = a.name;
                        sel.appendChild(opt);
                    });
                });
            }
            if (callback) callback();
        });
}

function loadGoals() {
    fetch('/api/goals/list')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('goalsList');
            container.innerHTML = '';
            if (!data.success || data.goals.length === 0) {
                const empty = document.createElement('div');
                empty.style.cssText = 'grid-column:1/-1;text-align:center;color:var(--th);padding:40px 0;';
                const p = document.createElement('p');
                p.textContent = 'No savings goals yet. Set your first goal!';
                empty.appendChild(p);
                container.appendChild(empty);
                return;
            }
            data.goals.forEach(g => container.appendChild(buildGoalCard(g)));
        })
        .catch(err => console.error(err));
}

function buildGoalCard(g) {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.cssText = 'display:flex;flex-direction:column;';
    const pct = g.progress_percent;
    const barClass = pct >= 90 ? 'bg-warning' : '';

    const header = document.createElement('div');
    header.className = 'glass-card-header';
    header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
    const title = document.createElement('span');
    title.className = 'glass-card-title';
    title.textContent = g.name;
    const badge = document.createElement('span');
    badge.className = g.status === 'achieved' ? 'glass-badge badge-income' : 'glass-badge';
    badge.textContent = g.status;
    header.appendChild(title);
    header.appendChild(badge);

    const body = document.createElement('div');
    body.style.cssText = 'padding:16px 20px;flex:1;';

    const statsWrap = document.createElement('div');
    statsWrap.className = 'text-center mb-3';
    const pctDisplay = document.createElement('h2');
    pctDisplay.className = 'stat-value';
    pctDisplay.textContent = `${pct}%`;
    const amountLine = document.createElement('small');
    amountLine.style.color = 'var(--ts)';
    amountLine.textContent = `${formatMoneyRon(g.current_amount || 0)} of ${formatMoneyRon(g.target_amount || 0)}`;
    statsWrap.appendChild(pctDisplay);
    statsWrap.appendChild(amountLine);
    body.appendChild(statsWrap);

    const progress = document.createElement('div');
    progress.className = 'progress mb-3';
    progress.style.height = '12px';
    const progressBar = document.createElement('div');
    progressBar.className = `progress-bar ${barClass}`;
    progressBar.style.width = `${pct}%`;
    progress.appendChild(progressBar);
    body.appendChild(progress);

    const remaining = document.createElement('p');
    remaining.style.cssText = 'color:var(--ts);font-size:0.85rem;';
    remaining.textContent = `Remaining: ${formatMoneyRon(g.remaining_amount || 0)}`;
    body.appendChild(remaining);

    if (g.target_date) {
        const dateP = document.createElement('p');
        dateP.style.cssText = 'color:var(--ts);font-size:0.85rem;';
        dateP.textContent = `Target Date: ${g.target_date}`;
        body.appendChild(dateP);
    }
    if (g.monthly_target) {
        const monthlyP = document.createElement('p');
        monthlyP.style.cssText = 'color:var(--ts);font-size:0.85rem;';
        monthlyP.textContent = `Monthly: ${formatMoneyRon(parseFloat(g.monthly_target))}`;
        body.appendChild(monthlyP);
    }
    if (g.account_id) {
        const linkedP = document.createElement('p');
        linkedP.style.cssText = 'color:var(--ts);font-size:0.85rem;';
        linkedP.textContent = `Linked: ${getAccountName(g.account_id)}`;
        body.appendChild(linkedP);
    }

    const footer = document.createElement('div');
    footer.style.cssText = 'padding:12px 20px;border-top:1px solid var(--gb);display:flex;gap:4px;margin-top:auto;';
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'btn btn-sm btn-secondary flex-fill';
    addBtn.textContent = 'Add';
    addBtn.addEventListener('click', () => openProgress(g.id));
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-sm btn-secondary flex-fill';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', () => openEditGoal(g.id));
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn btn-sm btn-secondary flex-fill';
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', () => deleteGoal(g.id, g.name));
    footer.appendChild(addBtn);
    footer.appendChild(editBtn);
    footer.appendChild(delBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(footer);
    return card;
}

function calcFromDeadline(prefix) {
    const target = parseFloat(document.getElementById(prefix + 'TargetAmount').value) || 0;
    const currentEl = document.querySelector(`#${prefix}GoalForm [name=current_amount]`);
    const current = parseFloat(currentEl ? currentEl.value : 0) || 0;
    const dateVal = document.getElementById(prefix + 'TargetDate').value;
    const result = document.getElementById(prefix + 'ModeAResult');
    if (!dateVal || !target) { result.textContent = ''; return; }
    const months = monthsBetween(new Date(), new Date(dateVal));
    if (months <= 0) { result.textContent = 'Date must be in the future.'; return; }
    const monthly = (target - current) / months;
    result.textContent = `→ Save ${formatMoneyRon(monthly)}/month`;
    document.getElementById(prefix + 'MonthlyTarget').value = '';
    document.getElementById(prefix + 'ModeBResult').textContent = '';
}

function calcFromMonthly(prefix) {
    const target = parseFloat(document.getElementById(prefix + 'TargetAmount').value) || 0;
    const currentEl = document.querySelector(`#${prefix}GoalForm [name=current_amount]`);
    const current = parseFloat(currentEl ? currentEl.value : 0) || 0;
    const monthly = parseFloat(document.getElementById(prefix + 'MonthlyTarget').value) || 0;
    const result = document.getElementById(prefix + 'ModeBResult');
    if (!monthly || !target) { result.textContent = ''; return; }
    const months = Math.ceil((target - current) / monthly);
    const finish = new Date();
    finish.setMonth(finish.getMonth() + months);
    result.textContent = `→ Done by ${finish.toLocaleDateString('en-US', {year: 'numeric', month: 'long'})}`;
    document.getElementById(prefix + 'TargetDate').value = '';
    document.getElementById(prefix + 'ModeAResult').textContent = '';
}

function recalcTimeline(prefix) {
    const dateVal = document.getElementById(prefix + 'TargetDate')?.value;
    const monthly = document.getElementById(prefix + 'MonthlyTarget')?.value;
    if (dateVal) calcFromDeadline(prefix);
    else if (monthly) calcFromMonthly(prefix);
}

function monthsBetween(d1, d2) {
    return (d2.getFullYear() - d1.getFullYear()) * 12 + (d2.getMonth() - d1.getMonth());
}

function saveGoal() {
    const form = document.getElementById('addGoalForm');
    const fd = new FormData(form);
    const data = {
        account_id: fd.get('account_id') || null,
        name: fd.get('name'),
        target_amount: fd.get('target_amount'),
        current_amount: fd.get('current_amount') || 0,
        target_date: fd.get('target_date') || null,
        monthly_target: fd.get('monthly_target') || null,
    };
    fetch('/api/goals/create', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Goal Created!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('addGoalModal')).hide();
                form.reset();
                document.getElementById('addModeAResult').textContent = '';
                document.getElementById('addModeBResult').textContent = '';
                loadGoals();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function openEditGoal(goalId) {
    fetch(`/api/goals/${goalId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const g = data.goal;
                document.getElementById('editGoalId').value = g.id;
                document.getElementById('editGoalName').value = g.name;
                document.getElementById('editTargetAmount').value = g.target_amount;
                document.getElementById('editCurrentAmount').value = g.current_amount;
                document.getElementById('editTargetDate').value = g.target_date || '';
                document.getElementById('editMonthlyTarget').value = g.monthly_target || '';
                document.getElementById('editGoalStatus').value = g.status;
                document.getElementById('editGoalAccount').value = g.account_id || '';
                new bootstrap.Modal(document.getElementById('editGoalModal')).show();
            }
        });
}

function updateGoal() {
    const form = document.getElementById('editGoalForm');
    const fd = new FormData(form);
    const goalId = fd.get('goal_id');
    const data = {
        account_id: fd.get('account_id') || null,
        name: fd.get('name'),
        target_amount: fd.get('target_amount'),
        current_amount: fd.get('current_amount'),
        target_date: fd.get('target_date') || null,
        monthly_target: fd.get('monthly_target') || null,
        status: fd.get('status'),
    };
    fetch(`/api/goals/${goalId}/update`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Updated!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('editGoalModal')).hide();
                loadGoals();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function openProgress(goalId) {
    document.getElementById('progressGoalId').value = goalId;
    document.getElementById('progressAmount').value = '';
    new bootstrap.Modal(document.getElementById('progressModal')).show();
}

function saveProgress() {
    const goalId = document.getElementById('progressGoalId').value;
    const amount = document.getElementById('progressAmount').value;
    fetch(`/api/goals/${goalId}/progress`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({amount})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            Swal.fire({icon: 'success', title: 'Progress Added!', timer: 1500, showConfirmButton: false});
            bootstrap.Modal.getInstance(document.getElementById('progressModal')).hide();
            loadGoals();
        } else {
            Swal.fire({icon: 'error', title: 'Error', text: data.message});
        }
    });
}

function deleteGoal(goalId, name) {
    Swal.fire({
        title: 'Delete Goal?', text: `Delete "${name}"?`, icon: 'warning',
        showCancelButton: true, confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (result.isConfirmed) {
            fetch(`/api/goals/${goalId}/delete`, {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({icon: 'success', title: 'Deleted!', timer: 1500, showConfirmButton: false});
                        loadGoals();
                    } else {
                        Swal.fire({icon: 'error', title: 'Error', text: data.message});
                    }
                });
        }
    });
}

function formatMoneyRon(val) {
    return formatMoney(val, 'RON');
}
