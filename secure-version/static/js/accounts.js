/**
 * Aura Financial Tracker - Secure Version
 * Accounts page controller
 * Sprint 12 (bugfix): moved out of an inline <script> block — see categories.js
 * for why (CSP script-src 'self' blocks inline scripts and inline onclick
 * attributes with no visible console error in some setups).
 */

document.addEventListener('DOMContentLoaded', function() {
    loadCurrencies();
    loadAccounts();
    loadSummary();
    document.getElementById('saveAccountBtn').addEventListener('click', saveAccount);
    document.getElementById('updateAccountBtn').addEventListener('click', updateAccount);
    document.getElementById('executeTransferBtn').addEventListener('click', executeTransfer);
    document.getElementById('transferDate').valueAsDate = new Date();
    initAccountSortable();

    // Sprint 57 (ENH-11): interest fields only make sense for
    // type=savings — toggled live as the type select changes, in both
    // modals. Server-side scoping (_parse_interest_fields()) is the real
    // enforcement; this is just so the form doesn't show irrelevant
    // fields for a checking/credit_card/etc. account.
    document.getElementById('addAccountType').addEventListener('change', function() {
        toggleInterestSection('addAccountType', 'addInterestSection');
    });
    document.getElementById('editAccountType').addEventListener('change', function() {
        toggleInterestSection('editAccountType', 'editInterestSection');
    });
});

function toggleInterestSection(typeSelectId, sectionId) {
    const isSavings = document.getElementById(typeSelectId).value === 'savings';
    document.getElementById(sectionId).style.display = isSavings ? '' : 'none';
}

// ── Drag-and-drop reordering (Sprint 53, UI-01) ──────────────────────────────
// Sortable.create() tracks #accountsList's children live, so it survives
// loadAccounts() clearing/repopulating the grid without re-initializing.
function initAccountSortable() {
    Sortable.create(document.getElementById('accountsList'), {
        handle: '.account-drag-handle',
        animation: 150,
        onEnd: onAccountReorder,
    });
}

function onAccountReorder() {
    const grid = document.getElementById('accountsList');
    const order = Array.from(grid.children)
        .map(el => parseInt(el.dataset.id, 10))
        .filter(id => !isNaN(id));
    if (!order.length) return;

    fetch('/api/accounts/reorder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order})
    })
        .then(r => r.json())
        .then(j => {
            if (!j.success) {
                Swal.fire({icon: 'error', title: 'Could not save account order', text: j.message});
                loadAccounts();
            }
        })
        .catch(() => loadAccounts());
}

function loadCurrencies() {
    return fetch('/api/currencies/list')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            ['addAccountCurrency', 'editAccountCurrency'].forEach(id => {
                const sel = document.getElementById(id);
                if (!sel) return;
                const prevValue = sel.value;
                sel.innerHTML = '';
                data.currencies.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.code;
                    opt.textContent = c.code;
                    sel.appendChild(opt);
                });
                if (prevValue) sel.value = prevValue;
            });
        });
}

function loadSummary() {
    fetch('/api/accounts/summary')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('netWorthDisplay').textContent = formatMoney(data.net_worth, 'RON');
                document.getElementById('budgetBalanceDisplay').textContent = formatMoney(data.budget_balance, 'RON');
            }
        });
}

function loadAccounts() {
    fetch('/api/accounts/list')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('accountsList');
            container.innerHTML = '';
            if (!data.success || data.accounts.length === 0) {
                const empty = document.createElement('div');
                empty.style.cssText = 'grid-column:1/-1;text-align:center;color:var(--th);padding:40px 0;';
                const p = document.createElement('p');
                p.textContent = 'No accounts yet. Add your first account!';
                empty.appendChild(p);
                container.appendChild(empty);
                document.getElementById('accountCountDisplay').textContent = '0';
                return;
            }
            document.getElementById('accountCountDisplay').textContent = data.accounts.length;
            data.accounts.forEach(a => container.appendChild(buildAccountCard(a)));
            populateTransferSelects(data.accounts);
        })
        .catch(err => console.error(err));
}

function buildAccountCard(a) {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.dataset.id = a.id;
    card.style.cssText = 'display:flex;flex-direction:column;';

    const header = document.createElement('div');
    header.className = 'glass-card-header';
    header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
    const titleWrap = document.createElement('div');
    titleWrap.style.cssText = 'display:flex;align-items:center;gap:6px;min-width:0;';
    const dragHandle = document.createElement('span');
    dragHandle.className = 'widget-drag-handle account-drag-handle';
    dragHandle.title = 'Drag to reorder';
    dragHandle.textContent = '⠿';
    const title = document.createElement('span');
    title.className = 'glass-card-title';
    title.textContent = a.name;
    titleWrap.appendChild(dragHandle);
    titleWrap.appendChild(title);
    const badge = document.createElement('span');
    badge.className = a.include_in_budget ? 'glass-badge badge-income' : 'glass-badge';
    badge.textContent = a.include_in_budget ? 'In Budget' : 'Excluded';
    header.appendChild(titleWrap);
    header.appendChild(badge);

    const body = document.createElement('div');
    body.style.cssText = 'padding:16px 20px;flex:1;';
    const balance = document.createElement('h3');
    balance.className = a.current_balance >= 0 ? 'amount-positive' : 'amount-negative';
    balance.style.marginBottom = '4px';
    balance.textContent = formatMoney(a.current_balance, a.currency);
    const meta = document.createElement('small');
    meta.style.color = 'var(--ts)';
    meta.textContent = `${a.type.replace('_', ' ')} • Initial: ${formatMoney(a.initial_balance, a.currency)}`;
    body.appendChild(balance);
    body.appendChild(meta);
    // Sprint 57 (ENH-11): visible confirmation the interest setting took
    // effect, without needing to reopen the edit modal to check.
    if (a.interest_rate_annual) {
        const interestNote = document.createElement('small');
        interestNote.style.cssText = 'display:block;color:var(--th);margin-top:2px;';
        interestNote.textContent = `${a.interest_rate_annual}% annual interest, accrued ${a.interest_accrual_frequency}`;
        body.appendChild(interestNote);
    }
    if (a.description) {
        const desc = document.createElement('p');
        desc.style.cssText = 'color:var(--ts);font-size:0.85rem;margin-top:8px;';
        desc.textContent = a.description;
        body.appendChild(desc);
    }

    const actions = document.createElement('div');
    actions.style.cssText = 'padding:12px 20px;border-top:1px solid var(--gb);display:flex;gap:8px;margin-top:auto;';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-sm btn-secondary flex-fill';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', () => openEditAccount(a.id));
    const transferBtn = document.createElement('button');
    transferBtn.type = 'button';
    transferBtn.className = 'btn btn-sm btn-secondary flex-fill';
    transferBtn.textContent = 'Transfer';
    transferBtn.addEventListener('click', () => openTransfer(a.id));
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn btn-sm btn-secondary flex-fill';
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', () => deleteAccount(a.id, a.name));
    actions.appendChild(editBtn);
    actions.appendChild(transferBtn);
    actions.appendChild(delBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);
    return card;
}

function saveAccount() {
    const form = document.getElementById('addAccountForm');
    const fd = new FormData(form);
    const data = {
        name: fd.get('name'),
        type: fd.get('type'),
        currency: fd.get('currency'),
        initial_balance: fd.get('initial_balance'),
        description: fd.get('description') || '',
        include_in_budget: fd.get('include_in_budget') === 'on',
        interest_rate_annual: fd.get('interest_rate_annual') || '',
        interest_accrual_frequency: fd.get('interest_accrual_frequency') || '',
    };
    fetch('/api/accounts/create', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Account Created!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('addAccountModal')).hide();
                form.reset();
                document.getElementById('addInterestSection').style.display = 'none';
                loadAccounts(); loadSummary();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function openEditAccount(accountId) {
    fetch(`/api/accounts/${accountId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const a = data.account;
                document.getElementById('editAccountId').value = a.id;
                document.getElementById('editAccountName').value = a.name;
                document.getElementById('editAccountType').value = a.type;
                loadCurrencies().then(() => {
                    document.getElementById('editAccountCurrency').value = a.currency;
                });
                document.getElementById('editAccountDesc').value = a.description || '';
                document.getElementById('editIncludeBudget').checked = a.include_in_budget;
                document.getElementById('editInterestRate').value = a.interest_rate_annual != null ? a.interest_rate_annual : '';
                document.getElementById('editInterestFrequency').value = a.interest_accrual_frequency || 'monthly';
                toggleInterestSection('editAccountType', 'editInterestSection');
                new bootstrap.Modal(document.getElementById('editAccountModal')).show();
            }
        });
}

function updateAccount() {
    const form = document.getElementById('editAccountForm');
    const fd = new FormData(form);
    const accountId = fd.get('account_id');
    const data = {
        name: fd.get('name'),
        type: fd.get('type'),
        currency: fd.get('currency'),
        description: fd.get('description') || '',
        include_in_budget: document.getElementById('editIncludeBudget').checked,
        interest_rate_annual: fd.get('interest_rate_annual') || '',
        interest_accrual_frequency: fd.get('interest_accrual_frequency') || '',
    };
    fetch(`/api/accounts/${accountId}/update`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Updated!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('editAccountModal')).hide();
                loadAccounts(); loadSummary();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function deleteAccount(accountId, accountName) {
    Swal.fire({
        title: 'Delete Account?',
        text: `Delete "${accountName}"? This cannot be undone.`,
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (result.isConfirmed) {
            fetch(`/api/accounts/${accountId}/delete`, {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({icon: 'success', title: 'Deleted!', timer: 1500, showConfirmButton: false});
                        loadAccounts(); loadSummary();
                    } else {
                        Swal.fire({icon: 'error', title: 'Error', text: data.message});
                    }
                });
        }
    });
}

function populateTransferSelects(accounts) {
    const fromSelect = document.getElementById('transferFrom');
    const toSelect = document.getElementById('transferTo');
    const prevFrom = fromSelect.value;
    const prevTo = toSelect.value;
    fromSelect.innerHTML = '';
    toSelect.innerHTML = '';
    accounts.forEach(a => {
        const optionText = `${a.name} (${formatMoney(a.current_balance, a.currency)})`;
        const fromOpt = document.createElement('option');
        fromOpt.value = a.id;
        fromOpt.textContent = optionText;
        fromSelect.appendChild(fromOpt);
        const toOpt = document.createElement('option');
        toOpt.value = a.id;
        toOpt.textContent = optionText;
        toSelect.appendChild(toOpt);
    });
    if (prevFrom) fromSelect.value = prevFrom;
    if (prevTo) toSelect.value = prevTo;
}

function openTransfer(fromAccountId) {
    new bootstrap.Modal(document.getElementById('transferModal')).show();
    if (fromAccountId) {
        document.getElementById('transferFrom').value = fromAccountId;
    }
}

function executeTransfer() {
    const form = document.getElementById('transferForm');
    const fd = new FormData(form);
    const fromId = fd.get('from_account_id');
    const toId = fd.get('to_account_id');

    if (fromId === toId) {
        Swal.fire({icon: 'error', title: 'Error', text: 'From and To accounts must be different'});
        return;
    }

    const data = {
        from_account_id: fromId,
        to_account_id: toId,
        amount: fd.get('amount'),
        description: fd.get('description') || 'Transfer',
        transfer_date: fd.get('transfer_date'),
    };
    fetch('/api/transfers/create', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Transfer Complete!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('transferModal')).hide();
                form.reset();
                document.getElementById('transferDate').valueAsDate = new Date();
                loadAccounts(); loadSummary();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}
