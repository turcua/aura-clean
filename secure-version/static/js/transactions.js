/**
 * Aura Financial Tracker - Secure Version
 * Transactions page controller
 * Sprint 11 (bugfix): moved out of an inline <script> block — see categories.js
 * for why (CSP script-src 'self' blocks inline scripts and inline onclick
 * attributes with no visible console error in some setups).
 */

const TRANSACTIONS_PER_PAGE = 25;
let currentTransactionsPage = 1;

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('transaction_date').valueAsDate = new Date();
    loadCategories();
    loadAccounts();
    loadLoans();
    loadFilterOptions();
    loadTransactions(1);
    setupEventListeners();
    setupCategorySearch();
});

function setupEventListeners() {
    document.getElementById('saveTransactionBtn').addEventListener('click', saveTransaction);

    document.querySelectorAll('input[name="type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            loadCategories();
        });
    });

    const modal = document.getElementById('addTransactionModal');
    modal.addEventListener('hidden.bs.modal', function() {
        resetTransactionModal();
    });

    document.getElementById('applyFiltersBtn').addEventListener('click', () => loadTransactions(1));
    document.getElementById('clearFiltersBtn').addEventListener('click', clearFilters);
}

// ── Filter bar (ENH-05/Sprint 50) ───────────────────────────────────────────
// Separate from the Add Transaction modal's own category/account <select>s
// (loadCategories()/loadAccounts() above) — those are type-scoped for the
// form; these show every category/account regardless of type, for filtering.
function loadFilterOptions() {
    fetch('/api/categories/list')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('filterCategory');
            if (!data.success) return;
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                select.appendChild(option);
            });
        })
        .catch(() => {});

    fetch('/api/accounts/list')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('filterAccount');
            if (!data.success) return;
            data.accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = account.name;
                select.appendChild(option);
            });
        })
        .catch(() => {});
}

function currentFilterParams() {
    const params = new URLSearchParams();
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    const category = document.getElementById('filterCategory').value;
    const account = document.getElementById('filterAccount').value;
    const type = document.getElementById('filterType').value;
    const includeTransfers = document.getElementById('filterIncludeTransfers').checked;

    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (category) params.set('category_id', category);
    if (account) params.set('account_id', account);
    if (type) params.set('type', type);
    if (includeTransfers) params.set('include_transfers', '1');
    return params;
}

function clearFilters() {
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterAccount').value = '';
    document.getElementById('filterType').value = '';
    document.getElementById('filterIncludeTransfers').checked = false;
    loadTransactions(1);
}

// ── Category searchable combobox (ENH-10/Sprint 52) ─────────────────────────
// Replaces a plain <select> — every user sees 15 seeded default categories
// plus their own, unworkable as a scroll list. category_id stays a hidden
// input with the same name/id, so saveTransaction()/updateTransaction() need
// no changes; only the populate/pre-fill logic here does.
let formCategories = [];

function loadCategories() {
    const type = document.querySelector('input[name="type"]:checked').value;
    document.getElementById('category_id').value = '';
    document.getElementById('categorySearchInput').value = '';

    return fetch(`/api/categories/list?type=${type}`)
        .then(response => response.json())
        .then(data => {
            formCategories = data.success ? data.categories : [];
        })
        .catch(() => {
            formCategories = [];
        });
}

function renderCategoryDropdown(filterText) {
    const dropdown = document.getElementById('categorySearchDropdown');
    dropdown.innerHTML = '';
    const filter = (filterText || '').toLowerCase();
    const matches = formCategories.filter(c => c.name.toLowerCase().includes(filter));

    if (matches.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'searchable-select-empty';
        empty.textContent = 'No matching categories';
        dropdown.appendChild(empty);
    } else {
        matches.forEach(category => {
            const opt = document.createElement('div');
            opt.className = 'searchable-select-option';
            opt.textContent = category.name;
            // mousedown (not click) fires before the input's blur handler,
            // so the selection registers before the dropdown gets hidden.
            opt.addEventListener('mousedown', (e) => {
                e.preventDefault();
                document.getElementById('category_id').value = category.id;
                document.getElementById('categorySearchInput').value = category.name;
                dropdown.style.display = 'none';
            });
            dropdown.appendChild(opt);
        });
    }
    dropdown.style.display = 'block';
}

function setupCategorySearch() {
    const input = document.getElementById('categorySearchInput');
    const dropdown = document.getElementById('categorySearchDropdown');

    input.addEventListener('input', () => {
        document.getElementById('category_id').value = '';
        renderCategoryDropdown(input.value);
    });
    input.addEventListener('focus', () => renderCategoryDropdown(input.value));
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

function loadAccounts() {
    const accountSelect = document.getElementById('account_id');

    return fetch('/api/accounts/list')
        .then(response => response.json())
        .then(data => {
            accountSelect.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = data.success ? 'No account' : 'Error loading accounts';
            accountSelect.appendChild(placeholder);

            if (data.success) {
                data.accounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account.id;
                    option.textContent = account.name;
                    accountSelect.appendChild(option);
                });
            }
        })
        .catch(() => {
            accountSelect.innerHTML = '<option value="">Error loading accounts</option>';
        });
}

function loadLoans() {
    const loanSelect = document.getElementById('loan_id');

    return fetch('/api/loans/list')
        .then(response => response.json())
        .then(data => {
            loanSelect.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = data.success ? 'No loan' : 'Error loading loans';
            loanSelect.appendChild(placeholder);

            if (data.success) {
                data.loans.forEach(loan => {
                    const option = document.createElement('option');
                    option.value = loan.id;
                    option.textContent = loan.name;
                    loanSelect.appendChild(option);
                });
            }
        })
        .catch(() => {
            loanSelect.innerHTML = '<option value="">Error loading loans</option>';
        });
}

function loadTransactions(page) {
    currentTransactionsPage = page || currentTransactionsPage;
    const tbody = document.getElementById('transactionsList');

    const params = currentFilterParams();
    params.set('page', currentTransactionsPage);
    params.set('per_page', TRANSACTIONS_PER_PAGE);

    fetch(`/api/transactions/list?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            tbody.innerHTML = '';
            if (!data.success) {
                tbody.appendChild(messageRow(`Error loading transactions: ${data.message}`, 'var(--dn)'));
                renderPaginationControls(null);
                return;
            }
            if (data.transactions.length === 0) {
                const msg = currentTransactionsPage > 1
                    ? 'No transactions on this page.'
                    : 'No transactions yet. Click "Add Transaction" to get started!';
                tbody.appendChild(messageRow(msg, 'var(--th)'));
                renderPaginationControls(data);
                return;
            }
            data.transactions.forEach(transaction => {
                tbody.appendChild(createTransactionRow(transaction));
            });
            renderPaginationControls(data);
        })
        .catch(error => {
            tbody.innerHTML = '';
            tbody.appendChild(messageRow(`Error loading transactions: ${error.message}`, 'var(--dn)'));
            renderPaginationControls(null);
        });
}

function renderPaginationControls(data) {
    const container = document.getElementById('transactionsPagination');
    if (!container) return;
    container.innerHTML = '';

    if (!data || !data.total_pages || data.total_pages <= 1) return;

    const firstBtn = document.createElement('button');
    firstBtn.type = 'button';
    firstBtn.className = 'btn-glass btn-glass-secondary';
    firstBtn.textContent = 'First';
    firstBtn.disabled = data.page <= 1;
    firstBtn.addEventListener('click', () => loadTransactions(1));

    const prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'btn-glass btn-glass-secondary';
    prevBtn.textContent = 'Previous';
    prevBtn.disabled = data.page <= 1;
    prevBtn.addEventListener('click', () => loadTransactions(data.page - 1));

    const info = document.createElement('span');
    info.className = 'pagination-info';
    info.textContent = `Page ${data.page} of ${data.total_pages} (${data.total} transaction${data.total !== 1 ? 's' : ''})`;

    const nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'btn-glass btn-glass-secondary';
    nextBtn.textContent = 'Next';
    nextBtn.disabled = data.page >= data.total_pages;
    nextBtn.addEventListener('click', () => loadTransactions(data.page + 1));

    const lastBtn = document.createElement('button');
    lastBtn.type = 'button';
    lastBtn.className = 'btn-glass btn-glass-secondary';
    lastBtn.textContent = 'Last';
    lastBtn.disabled = data.page >= data.total_pages;
    lastBtn.addEventListener('click', () => loadTransactions(data.total_pages));

    const jumpForm = document.createElement('form');
    jumpForm.className = 'pagination-jump';
    const jumpInput = document.createElement('input');
    jumpInput.type = 'number';
    jumpInput.className = 'glass-input pagination-jump-input';
    jumpInput.min = 1;
    jumpInput.max = data.total_pages;
    jumpInput.placeholder = 'Page';
    jumpInput.setAttribute('aria-label', 'Jump to page');
    const jumpBtn = document.createElement('button');
    jumpBtn.type = 'submit';
    jumpBtn.className = 'btn-glass btn-glass-secondary';
    jumpBtn.textContent = 'Go';
    jumpForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const target = parseInt(jumpInput.value, 10);
        if (!isNaN(target) && target >= 1 && target <= data.total_pages) loadTransactions(target);
    });
    jumpForm.appendChild(jumpInput);
    jumpForm.appendChild(jumpBtn);

    container.appendChild(firstBtn);
    container.appendChild(prevBtn);
    container.appendChild(info);
    container.appendChild(nextBtn);
    container.appendChild(lastBtn);
    container.appendChild(jumpForm);
}

function messageRow(text, color) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.className = 'text-center py-5';
    td.style.color = color;
    const p = document.createElement('p');
    p.className = 'mb-0';
    p.textContent = text;
    td.appendChild(p);
    tr.appendChild(td);
    return tr;
}

function createTransactionRow(transaction) {
    const tr = document.createElement('tr');

    const dateTd = document.createElement('td');
    dateTd.textContent = transaction.transaction_date;

    const typeTd = document.createElement('td');
    const typeBadge = document.createElement('span');
    if (transaction.is_transfer) {
        // Include Transfers is on — a transfer's own type is just its
        // accounting direction (debit/credit leg), not meaningful real
        // income/expense, so it gets its own badge instead of Income/Expense.
        typeBadge.className = 'glass-badge';
        typeBadge.textContent = 'Transfer';
    } else {
        typeBadge.className = transaction.type === 'income' ? 'glass-badge badge-income' : 'glass-badge badge-expense';
        typeBadge.textContent = transaction.type === 'income' ? 'Income' : 'Expense';
    }
    typeTd.appendChild(typeBadge);

    const categoryTd = document.createElement('td');
    if (transaction.category_name) {
        categoryTd.textContent = transaction.category_name;
    } else {
        const em = document.createElement('em');
        em.style.color = 'var(--th)';
        em.textContent = 'Uncategorized';
        categoryTd.appendChild(em);
    }

    const descTd = document.createElement('td');
    if (transaction.description) {
        descTd.textContent = transaction.description;
    } else {
        const em = document.createElement('em');
        em.className = 'text-muted';
        em.textContent = 'No description';
        descTd.appendChild(em);
    }

    const amountTd = document.createElement('td');
    const strong = document.createElement('strong');
    const amountSpan = document.createElement('span');
    amountSpan.className = transaction.type === 'income' ? 'amount-positive' : 'amount-negative';
    const sign = transaction.type === 'income' ? '+' : '-';
    amountSpan.textContent = `${sign}${formatMoney(parseFloat(transaction.amount), transaction.currency)}`;
    strong.appendChild(amountSpan);
    amountTd.appendChild(strong);

    const actionsTd = document.createElement('td');
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-sm btn-secondary';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', () => editTransaction(transaction.id));

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn btn-sm btn-secondary';
    delBtn.textContent = 'Delete';
    delBtn.style.marginLeft = '6px';
    delBtn.addEventListener('click', () => deleteTransaction(transaction.id));

    actionsTd.appendChild(editBtn);
    actionsTd.appendChild(delBtn);

    tr.appendChild(dateTd);
    tr.appendChild(typeTd);
    tr.appendChild(categoryTd);
    tr.appendChild(descTd);
    tr.appendChild(amountTd);
    tr.appendChild(actionsTd);

    return tr;
}

function saveTransaction() {
    const form = document.getElementById('addTransactionForm');
    const formData = new FormData(form);

    // category_id is now a hidden input (ENH-10) — HTML5 `required` doesn't
    // apply to type="hidden", so this check replaces the native validation
    // the old <select required> used to give for free.
    if (!formData.get('category_id')) {
        Swal.fire({icon: 'error', title: 'Error!', text: 'Please select a category.'});
        return;
    }

    const saveBtn = document.getElementById('saveTransactionBtn');
    const editingId = saveBtn.getAttribute('data-editing-id');

    const data = {
        category_id: formData.get('category_id'),
        account_id: formData.get('account_id') || null,
        loan_id: formData.get('loan_id') || null,
        type: formData.get('type'),
        amount: formData.get('amount'),
        description: formData.get('description'),
        transaction_date: formData.get('transaction_date'),
    };

    saveBtn.disabled = true;
    const originalText = saveBtn.textContent;
    saveBtn.textContent = 'Saving...';

    const url = editingId ? `/api/transactions/${editingId}/update` : '/api/transactions/create';

    fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const message = editingId ? 'Transaction Updated!' : 'Transaction Created!';
            Swal.fire({icon: 'success', title: message, text: data.message, timer: 2000, showConfirmButton: false});
            bootstrap.Modal.getInstance(document.getElementById('addTransactionModal')).hide();
            resetTransactionModal();
            loadTransactions();
        } else {
            Swal.fire({icon: 'error', title: 'Error!', text: data.message});
        }
    })
    .catch(error => {
        Swal.fire({icon: 'error', title: 'Error!', text: 'Failed to save transaction: ' + error.message});
    })
    .finally(() => {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    });
}

function resetTransactionModal() {
    const form = document.getElementById('addTransactionForm');
    const saveBtn = document.getElementById('saveTransactionBtn');

    form.reset();
    document.getElementById('transaction_date').valueAsDate = new Date();

    document.getElementById('addTransactionModalLabel').textContent = 'Add New Transaction';
    saveBtn.textContent = 'Save Transaction';
    saveBtn.removeAttribute('data-editing-id');
}

function editTransaction(transactionId) {
    fetch(`/api/transactions/${transactionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const transaction = data.transaction;

                document.getElementById('saveTransactionBtn').setAttribute('data-editing-id', transactionId);
                document.getElementById('addTransactionModalLabel').textContent = 'Edit Transaction';
                document.getElementById('saveTransactionBtn').textContent = 'Update Transaction';

                document.getElementById('amount').value = transaction.amount;
                document.getElementById('description').value = transaction.description || '';
                document.getElementById('transaction_date').value = transaction.transaction_date;

                if (transaction.type === 'income') {
                    document.getElementById('typeIncome').checked = true;
                } else {
                    document.getElementById('typeExpense').checked = true;
                }

                loadCategories().then(() => {
                    if (transaction.category_id) {
                        document.getElementById('category_id').value = transaction.category_id;
                        document.getElementById('categorySearchInput').value = transaction.category_name || '';
                    }
                });

                loadAccounts().then(() => {
                    document.getElementById('account_id').value = transaction.account_id || '';
                });

                loadLoans().then(() => {
                    document.getElementById('loan_id').value = transaction.loan_id || '';
                });

                new bootstrap.Modal(document.getElementById('addTransactionModal')).show();
            } else {
                Swal.fire({icon: 'error', title: 'Error!', text: 'Failed to load transaction: ' + data.message});
            }
        })
        .catch(error => {
            Swal.fire({icon: 'error', title: 'Error!', text: 'Failed to fetch transaction: ' + error.message});
        });
}

function deleteTransaction(transactionId) {
    Swal.fire({
        title: 'Delete Transaction?',
        text: 'Are you sure you want to delete this transaction? This action cannot be undone!',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            performDeleteTransaction(transactionId);
        }
    });
}

function performDeleteTransaction(transactionId) {
    Swal.fire({title: 'Deleting...', allowOutsideClick: false, didOpen: () => Swal.showLoading()});

    fetch(`/api/transactions/${transactionId}/delete`, {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Deleted!', text: data.message, timer: 2000, showConfirmButton: false});
                loadTransactions();
            } else {
                Swal.fire({icon: 'error', title: 'Error!', text: data.message});
            }
        })
        .catch(error => {
            Swal.fire({icon: 'error', title: 'Error!', text: 'Failed to delete transaction: ' + error.message});
        });
}
