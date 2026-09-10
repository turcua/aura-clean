/**
 * Aura Financial Tracker - Secure Version
 * Recurring Transactions page controller
 * Sprint 12 (bugfix): moved out of an inline <script> block — see categories.js
 * for why (CSP script-src 'self' blocks inline scripts and inline onclick
 * attributes with no visible console error in some setups).
 */

let allAccounts = [], allCategories = [], allLoans = [];

document.addEventListener('DOMContentLoaded', function() {
    loadAccounts();
    loadCategories();
    loadLoansForLink();
    loadRecurring();
    document.getElementById('saveRecurringBtn').addEventListener('click', saveRecurring);
    document.getElementById('updateRecurringBtn').addEventListener('click', updateRecurring);
    document.getElementById('confirmUseTemplateBtn').addEventListener('click', activateTemplate);
    document.getElementById('runNowBtn').addEventListener('click', triggerGeneration);
    document.getElementById('addStartDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('useTemplateStart').value = new Date().toISOString().split('T')[0];
    document.getElementById('templates-tab').addEventListener('shown.bs.tab', loadTemplates);
    setupCategoryCombobox('add');
    setupCategoryCombobox('edit');
});

function loadAccounts() {
    fetch('/api/accounts/list')
        .then(r => r.json())
        .then(data => { if (data.success) { allAccounts = data.accounts; populateAccountSelects(); } });
}

function loadCategories() {
    fetch('/api/categories/list')
        .then(r => r.json())
        .then(data => { if (data.success) { allCategories = data.categories; } });
}

function populateAccountSelects() {
    ['addRAccount', 'editRAccount'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = '';
        allAccounts.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = a.name;
            sel.appendChild(opt);
        });
    });
}

// Sprint 51 (ENH-12) — separate from loadAccounts()/loadCategories() above,
// same "load full list once, populate two <select>s" pattern.
function loadLoansForLink() {
    fetch('/api/loans/list')
        .then(r => r.json())
        .then(data => { if (data.success) { allLoans = data.loans; populateLoanSelects(); } });
}

function populateLoanSelects() {
    ['addRLoan', 'editRLoan'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = '';
        const none = document.createElement('option');
        none.value = '';
        none.textContent = 'No loan';
        sel.appendChild(none);
        allLoans.forEach(l => {
            const opt = document.createElement('option');
            opt.value = l.id;
            opt.textContent = l.name;
            sel.appendChild(opt);
        });
    });
}

// ── Category searchable combobox (ENH-15/Sprint 57) ─────────────────────────
// Same pattern as ENH-10 (transactions.js), generalized over an id prefix
// since this page needs two independent instances (Add + Edit) sharing one
// allCategories list, rather than the transaction form's single instance.
function categoryOptionLabel(c) {
    return `[${c.type}] ${c.name}`;
}

function setupCategoryCombobox(prefix) {
    const input = document.getElementById(`${prefix}RCategorySearchInput`);
    const hidden = document.getElementById(`${prefix}RCategory`);
    const dropdown = document.getElementById(`${prefix}RCategoryDropdown`);
    if (!input || !hidden || !dropdown) return;

    function render(filterText) {
        dropdown.innerHTML = '';
        const filter = (filterText || '').toLowerCase();
        const matches = allCategories.filter(c => categoryOptionLabel(c).toLowerCase().includes(filter));

        if (matches.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'searchable-select-empty';
            empty.textContent = 'No matching categories';
            dropdown.appendChild(empty);
        } else {
            matches.forEach(c => {
                const opt = document.createElement('div');
                opt.className = 'searchable-select-option';
                opt.textContent = categoryOptionLabel(c);
                opt.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    hidden.value = c.id;
                    input.value = categoryOptionLabel(c);
                    dropdown.style.display = 'none';
                });
                dropdown.appendChild(opt);
            });
        }
        dropdown.style.display = 'block';
    }

    input.addEventListener('input', () => {
        hidden.value = '';
        render(input.value);
    });
    input.addEventListener('focus', () => render(input.value));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const firstMatch = dropdown.querySelector('.searchable-select-option');
            if (firstMatch) firstMatch.dispatchEvent(new Event('mousedown'));
        } else if (e.key === 'Escape') {
            dropdown.style.display = 'none';
        }
    });
    input.addEventListener('blur', () => {
        setTimeout(() => { dropdown.style.display = 'none'; }, 150);
    });
}

function loadRecurring() {
    fetch('/api/recurring/list')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const all = data.recurring;
            renderList('allRecurringList', all);
            renderList('activeRecurringList', all.filter(r => r.is_active));
            renderList('pausedRecurringList', all.filter(r => !r.is_active));
        });
}

function renderList(containerId, items) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (!items.length) {
        const empty = document.createElement('div');
        empty.className = 'text-center py-4';
        empty.style.color = 'var(--th)';
        empty.textContent = 'No recurring transactions found.';
        container.appendChild(empty);
        return;
    }

    const wrap = document.createElement('div');
    wrap.style.overflowX = 'auto';
    const table = document.createElement('table');
    table.className = 'glass-table';
    table.innerHTML = '<thead><tr><th>Description</th><th>Type</th><th>Amount</th><th>Frequency</th><th>Next Run</th><th>Status</th><th>Actions</th></tr></thead>';
    const tbody = document.createElement('tbody');

    items.forEach(r => {
        const tr = document.createElement('tr');

        const descTd = document.createElement('td');
        descTd.textContent = r.description || '-';

        const typeTd = document.createElement('td');
        const typeBadge = document.createElement('span');
        typeBadge.className = `glass-badge ${r.type === 'income' ? 'badge-income' : 'badge-expense'}`;
        typeBadge.textContent = r.type;
        typeTd.appendChild(typeBadge);

        const amountTd = document.createElement('td');
        amountTd.textContent = formatMoney(parseFloat(r.amount), r.currency);

        const freqTd = document.createElement('td');
        freqTd.textContent = r.frequency;

        const nextTd = document.createElement('td');
        nextTd.textContent = r.next_run_date || '-';

        const statusTd = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = `glass-badge ${r.is_active ? 'badge-income' : ''}`;
        statusBadge.textContent = r.is_active ? 'Active' : 'Paused';
        statusTd.appendChild(statusBadge);

        const actionsTd = document.createElement('td');
        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'btn btn-sm btn-secondary';
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => openEditRecurring(r.id));

        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'btn btn-sm btn-secondary';
        toggleBtn.style.marginLeft = '6px';
        toggleBtn.textContent = r.is_active ? 'Pause' : 'Resume';
        toggleBtn.addEventListener('click', () => toggleRecurring(r.id, !r.is_active));

        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'btn btn-sm btn-secondary';
        delBtn.style.marginLeft = '6px';
        delBtn.textContent = 'Delete';
        delBtn.addEventListener('click', () => deleteRecurring(r.id));

        actionsTd.appendChild(editBtn);
        actionsTd.appendChild(toggleBtn);
        actionsTd.appendChild(delBtn);

        tr.appendChild(descTd);
        tr.appendChild(typeTd);
        tr.appendChild(amountTd);
        tr.appendChild(freqTd);
        tr.appendChild(nextTd);
        tr.appendChild(statusTd);
        tr.appendChild(actionsTd);
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    container.appendChild(wrap);
}

function saveRecurring() {
    const form = document.getElementById('addRecurringForm');
    const fd = new FormData(form);
    const isTemplate = document.getElementById('saveAsTemplate').checked;
    const data = {
        account_id: fd.get('account_id'),
        category_id: fd.get('category_id') || null,
        loan_id: fd.get('loan_id') || null,
        type: fd.get('type'),
        amount: fd.get('amount'),
        description: fd.get('description'),
        frequency: fd.get('frequency'),
        start_date: fd.get('start_date'),
        end_date: fd.get('end_date') || null,
        is_template: isTemplate,
    };
    fetch('/api/recurring/create', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const label = isTemplate ? 'Template Saved!' : 'Created!';
                Swal.fire({icon: 'success', title: label, timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('addRecurringModal')).hide();
                form.reset();
                document.getElementById('saveAsTemplate').checked = false;
                if (isTemplate) { loadTemplates(); } else { loadRecurring(); }
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function loadTemplates() {
    fetch('/api/recurring/templates')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('templatesList');
            container.innerHTML = '';
            if (!data.success || !data.templates.length) {
                const empty = document.createElement('div');
                empty.className = 'text-center py-4';
                empty.style.color = 'var(--th)';
                empty.textContent = 'No templates saved yet. Use "Save as Template" when adding a recurring transaction.';
                container.appendChild(empty);
                return;
            }

            const wrap = document.createElement('div');
            wrap.style.overflowX = 'auto';
            const table = document.createElement('table');
            table.className = 'glass-table';
            table.innerHTML = '<thead><tr><th>Description</th><th>Type</th><th>Amount</th><th>Frequency</th><th>Actions</th></tr></thead>';
            const tbody = document.createElement('tbody');

            data.templates.forEach(t => {
                const tr = document.createElement('tr');

                const descTd = document.createElement('td');
                descTd.textContent = t.description || '-';

                const typeTd = document.createElement('td');
                const typeBadge = document.createElement('span');
                typeBadge.className = `glass-badge ${t.type === 'income' ? 'badge-income' : 'badge-expense'}`;
                typeBadge.textContent = t.type;
                typeTd.appendChild(typeBadge);

                const amountTd = document.createElement('td');
                amountTd.textContent = formatMoney(parseFloat(t.amount), t.currency);

                const freqTd = document.createElement('td');
                freqTd.textContent = t.frequency;

                const actionsTd = document.createElement('td');
                const useBtn = document.createElement('button');
                useBtn.type = 'button';
                useBtn.className = 'btn btn-sm btn-secondary';
                useBtn.textContent = 'Use';
                useBtn.addEventListener('click', () => openUseTemplate(t.id, t.description || 'Template'));

                const delBtn = document.createElement('button');
                delBtn.type = 'button';
                delBtn.className = 'btn btn-sm btn-secondary';
                delBtn.style.marginLeft = '6px';
                delBtn.textContent = 'Delete';
                delBtn.addEventListener('click', () => deleteRecurring(t.id));

                actionsTd.appendChild(useBtn);
                actionsTd.appendChild(delBtn);

                tr.appendChild(descTd);
                tr.appendChild(typeTd);
                tr.appendChild(amountTd);
                tr.appendChild(freqTd);
                tr.appendChild(actionsTd);
                tbody.appendChild(tr);
            });

            table.appendChild(tbody);
            wrap.appendChild(table);
            container.appendChild(wrap);
        });
}

function openUseTemplate(templateId, name) {
    document.getElementById('useTemplateId').value = templateId;
    document.getElementById('templateModalName').textContent = name;
    document.getElementById('useTemplateEnd').value = '';
    new bootstrap.Modal(document.getElementById('useTemplateModal')).show();
}

function activateTemplate() {
    const templateId = document.getElementById('useTemplateId').value;
    const startDate = document.getElementById('useTemplateStart').value;
    const endDate = document.getElementById('useTemplateEnd').value || null;

    fetch(`/api/recurring/from-template/${templateId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({start_date: startDate, end_date: endDate})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            Swal.fire({icon: 'success', title: 'Activated!', text: 'Recurring transaction created from template.', timer: 1800, showConfirmButton: false});
            bootstrap.Modal.getInstance(document.getElementById('useTemplateModal')).hide();
            loadRecurring();
        } else {
            Swal.fire({icon: 'error', title: 'Error', text: data.message});
        }
    });
}

function openEditRecurring(rtId) {
    fetch(`/api/recurring/${rtId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const r = data.recurring;
                document.getElementById('editRtId').value = r.id;
                document.getElementById('editRType').value = r.type;
                document.getElementById('editRAmount').value = r.amount;
                document.getElementById('editRDesc').value = r.description || '';
                document.getElementById('editRFreq').value = r.frequency;
                document.getElementById('editRStart').value = r.start_date || '';
                document.getElementById('editREnd').value = r.end_date || '';
                if (r.account_id) document.getElementById('editRAccount').value = r.account_id;
                const editCategory = r.category_id ? allCategories.find(c => c.id === r.category_id) : null;
                document.getElementById('editRCategory').value = editCategory ? editCategory.id : '';
                document.getElementById('editRCategorySearchInput').value = editCategory ? categoryOptionLabel(editCategory) : '';
                document.getElementById('editRLoan').value = r.loan_id || '';
                new bootstrap.Modal(document.getElementById('editRecurringModal')).show();
            }
        });
}

function updateRecurring() {
    const form = document.getElementById('editRecurringForm');
    const fd = new FormData(form);
    const rtId = fd.get('rt_id');
    const data = {
        account_id: fd.get('account_id'),
        category_id: fd.get('category_id') || null,
        loan_id: fd.get('loan_id') || null,
        type: fd.get('type'),
        amount: fd.get('amount'),
        description: fd.get('description'),
        frequency: fd.get('frequency'),
        start_date: fd.get('start_date'),
        end_date: fd.get('end_date') || null,
    };
    fetch(`/api/recurring/${rtId}/update`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Updated!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('editRecurringModal')).hide();
                loadRecurring();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function toggleRecurring(rtId, isActive) {
    fetch(`/api/recurring/${rtId}/toggle`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({is_active: isActive})
    }).then(r => r.json()).then(data => { if (data.success) loadRecurring(); });
}

function deleteRecurring(rtId) {
    Swal.fire({
        title: 'Delete?', text: 'Delete this recurring rule? Generated transactions are kept.',
        icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (result.isConfirmed) {
            fetch(`/api/recurring/${rtId}/delete`, {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) { Swal.fire({icon: 'success', title: 'Deleted!', timer: 1500, showConfirmButton: false}); loadRecurring(); }
                    else { Swal.fire({icon: 'error', title: 'Error', text: data.message}); }
                });
        }
    });
}

function triggerGeneration() {
    Swal.fire({title: 'Running...', text: 'Generating due recurring transactions', didOpen: () => Swal.showLoading(), allowOutsideClick: false});
    fetch('/api/recurring/trigger', {method: 'POST'})
        .then(r => r.json())
        .then(data => { Swal.fire({icon: 'success', title: 'Done!', text: data.message}); loadRecurring(); })
        .catch(() => Swal.fire({icon: 'error', title: 'Error', text: 'Trigger failed'}));
}
