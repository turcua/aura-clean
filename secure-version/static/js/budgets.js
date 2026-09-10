/**
 * Aura Financial Tracker - Secure Version
 * Budgets page controller
 * Sprint 13: Transfers + Budgets + Savings Goals
 *
 * Loaded as an external <script src> (CSP script-src 'self' — no inline
 * scripts/onclick, see categories.js for the full rationale). Every
 * interactive element is wired with addEventListener and every dynamic
 * node built with document.createElement / textContent.
 */

let allCategories = [];

document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    loadBudgets();
    autoFillDates();
    document.getElementById('periodType').addEventListener('change', autoFillDates);
    document.getElementById('saveBudgetBtn').addEventListener('click', saveBudget);
    document.getElementById('addLimitRowBtn').addEventListener('click', () => addCategoryLimitRow());
});

function loadCategories() {
    fetch('/api/categories/list?type=expense')
        .then(r => r.json())
        .then(data => { if (data.success) allCategories = data.categories; });
}

function autoFillDates() {
    const period = document.getElementById('periodType').value;
    const today = new Date();
    let start, end;
    if (period === 'monthly') {
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (period === 'yearly') {
        start = new Date(today.getFullYear(), 0, 1);
        end = new Date(today.getFullYear(), 11, 31);
    } else {
        return;
    }
    document.getElementById('startDate').value = start.toISOString().split('T')[0];
    document.getElementById('endDate').value = end.toISOString().split('T')[0];
}

// ENH-15/Sprint 57: searchable combobox for a dynamically-added budget row.
// Scoped to this row's own elements via closures instead of ids, since an
// arbitrary number of rows can exist at once and ids must stay unique.
function categoryOptionLabel(c) {
    return `[${c.type}] ${c.name}`;
}

function wireCategoryRowCombobox(input, hidden, dropdown) {
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

function addCategoryLimitRow() {
    const container = document.getElementById('categoryLimits');
    const row = document.createElement('div');
    row.className = 'row mb-2 category-limit-row';

    const selectCol = document.createElement('div');
    selectCol.className = 'col-7';
    selectCol.style.position = 'relative';

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'glass-input';
    searchInput.autocomplete = 'off';
    searchInput.placeholder = 'Search or select category…';

    const hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = 'cat_id';

    const dropdown = document.createElement('div');
    dropdown.className = 'searchable-select-dropdown';
    dropdown.style.display = 'none';

    wireCategoryRowCombobox(searchInput, hidden, dropdown);

    selectCol.appendChild(searchInput);
    selectCol.appendChild(hidden);
    selectCol.appendChild(dropdown);

    const limitCol = document.createElement('div');
    limitCol.className = 'col-4';
    const limitInput = document.createElement('input');
    limitInput.type = 'number';
    limitInput.className = 'glass-input';
    limitInput.name = 'cat_limit';
    limitInput.placeholder = 'Limit $';
    limitInput.step = '0.01';
    limitInput.min = '0.01';
    limitCol.appendChild(limitInput);

    const removeCol = document.createElement('div');
    removeCol.className = 'col-1';
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-sm btn-secondary';
    removeBtn.textContent = '✕';
    removeBtn.addEventListener('click', () => row.remove());
    removeCol.appendChild(removeBtn);

    row.appendChild(selectCol);
    row.appendChild(limitCol);
    row.appendChild(removeCol);
    container.appendChild(row);
}

function loadBudgets() {
    fetch('/api/budgets/list')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('budgetsList');
            container.innerHTML = '';
            if (!data.success || data.budgets.length === 0) {
                const empty = document.createElement('div');
                empty.style.cssText = 'grid-column:1/-1;text-align:center;color:var(--th);padding:40px 0;';
                const p = document.createElement('p');
                p.textContent = 'No budgets yet. Create your first budget!';
                empty.appendChild(p);
                container.appendChild(empty);
                return;
            }
            data.budgets.forEach(b => container.appendChild(buildBudgetCard(b)));
        })
        .catch(err => console.error(err));
}

function buildBudgetCard(b) {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.cssText = 'display:flex;flex-direction:column;';

    fetch(`/api/budgets/${b.id}`)
        .then(r => r.json())
        .then(detail => {
            const limits = detail.category_limits || [];
            const totalSpent = limits.reduce((s, l) => s + (l.spent || 0), 0);
            const pct = b.total_limit > 0 ? Math.min((totalSpent / b.total_limit) * 100, 100) : 0;
            const barClass = pct >= 90 ? 'bg-danger' : pct >= 70 ? 'bg-warning' : '';

            const header = document.createElement('div');
            header.className = 'glass-card-header';
            header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
            const title = document.createElement('span');
            title.className = 'glass-card-title';
            title.textContent = b.name;
            const badge = document.createElement('span');
            badge.className = 'glass-badge';
            badge.textContent = b.period_type;
            header.appendChild(title);
            header.appendChild(badge);

            const body = document.createElement('div');
            body.style.cssText = 'padding:16px 20px;flex:1;';
            const dates = document.createElement('p');
            dates.style.cssText = 'color:var(--ts);font-size:0.85rem;margin-bottom:8px;';
            dates.textContent = `${b.start_date} → ${b.end_date}`;
            body.appendChild(dates);

            const totalRow = document.createElement('div');
            totalRow.className = 'd-flex justify-content-between mb-1';
            const totalLabel = document.createElement('span');
            totalLabel.textContent = `Total: ${formatMoney(totalSpent, 'RON')} / ${formatMoney(b.total_limit, 'RON')}`;
            const pctLabel = document.createElement('span');
            pctLabel.textContent = `${pct.toFixed(0)}%`;
            totalRow.appendChild(totalLabel);
            totalRow.appendChild(pctLabel);
            body.appendChild(totalRow);

            const progress = document.createElement('div');
            progress.className = 'progress mb-3';
            const progressBar = document.createElement('div');
            progressBar.className = `progress-bar ${barClass}`;
            progressBar.style.width = `${pct}%`;
            progress.appendChild(progressBar);
            body.appendChild(progress);

            if (limits.length > 0) {
                const tableWrap = document.createElement('div');
                tableWrap.style.overflowX = 'auto';
                const table = document.createElement('table');
                table.className = 'glass-table';
                const tbody = document.createElement('tbody');
                limits.forEach(l => {
                    const lPct = l.limit_amount > 0 ? Math.min((l.spent / l.limit_amount) * 100, 100) : 0;
                    const lBar = lPct >= 90 ? 'bg-danger' : lPct >= 70 ? 'bg-warning' : '';
                    const tr = document.createElement('tr');

                    const nameTd = document.createElement('td');
                    nameTd.textContent = l.category_name || 'Unknown';
                    const amountTd = document.createElement('td');
                    amountTd.textContent = `${formatMoney(l.spent || 0, 'RON')} / ${formatMoney(l.limit_amount, 'RON')}`;
                    const barTd = document.createElement('td');
                    barTd.width = '100';
                    const miniProgress = document.createElement('div');
                    miniProgress.className = 'progress';
                    miniProgress.style.height = '8px';
                    const miniBar = document.createElement('div');
                    miniBar.className = `progress-bar ${lBar}`;
                    miniBar.style.width = `${lPct}%`;
                    miniProgress.appendChild(miniBar);
                    barTd.appendChild(miniProgress);

                    tr.appendChild(nameTd);
                    tr.appendChild(amountTd);
                    tr.appendChild(barTd);
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);
                tableWrap.appendChild(table);
                body.appendChild(tableWrap);
            } else {
                const noLimits = document.createElement('p');
                noLimits.style.cssText = 'color:var(--ts);font-size:0.85rem;';
                noLimits.textContent = 'No category limits set.';
                body.appendChild(noLimits);
            }

            const footer = document.createElement('div');
            footer.style.cssText = 'padding:12px 20px;border-top:1px solid var(--gb);margin-top:auto;';
            const delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'btn btn-sm btn-secondary';
            delBtn.textContent = 'Delete';
            delBtn.addEventListener('click', () => deleteBudget(b.id, b.name));
            footer.appendChild(delBtn);

            card.appendChild(header);
            card.appendChild(body);
            card.appendChild(footer);
        });

    return card;
}

function saveBudget() {
    const form = document.getElementById('addBudgetForm');
    const fd = new FormData(form);

    const catRows = document.querySelectorAll('#categoryLimits .category-limit-row');
    const categoryLimits = [];
    catRows.forEach(row => {
        const catId = row.querySelector('[name=cat_id]').value;
        const limit = row.querySelector('[name=cat_limit]').value;
        if (catId && limit) categoryLimits.push({category_id: catId, limit_amount: parseFloat(limit)});
    });

    const data = {
        name: fd.get('name'),
        period_type: fd.get('period_type'),
        start_date: fd.get('start_date'),
        end_date: fd.get('end_date'),
        total_limit: fd.get('total_limit'),
        category_limits: categoryLimits,
    };

    fetch('/api/budgets/create', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Budget Created!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('addBudgetModal')).hide();
                form.reset();
                document.getElementById('categoryLimits').innerHTML = '';
                autoFillDates();
                loadBudgets();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function deleteBudget(budgetId, budgetName) {
    Swal.fire({
        title: 'Delete Budget?',
        text: `Delete "${budgetName}"? This cannot be undone.`,
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (result.isConfirmed) {
            fetch(`/api/budgets/${budgetId}/delete`, {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({icon: 'success', title: 'Deleted!', timer: 1500, showConfirmButton: false});
                        loadBudgets();
                    } else {
                        Swal.fire({icon: 'error', title: 'Error', text: data.message});
                    }
                });
        }
    });
}
