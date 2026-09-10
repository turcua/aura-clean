/**
 * Aura Financial Tracker - Secure Version
 * Reports & Export page controller
 * Sprint 14: Export/Import + Reports + Multi-Dashboard System
 *
 * Loaded as an external <script src> (CSP script-src 'self' — no inline
 * scripts/onclick, see categories.js for the full rationale). No user_id
 * anywhere — every request relies on the session cookie, and the category
 * table (the one place user-controlled category names are rendered) is
 * built with createElement/textContent rather than innerHTML.
 */

let categoryChartInst = null, monthChartInst = null, accountChartInst = null;

function cssVar(name) {
    return getComputedStyle(document.getElementById('app') || document.documentElement)
        .getPropertyValue(name).trim();
}

document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = cssVar('--ts');
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
    document.getElementById('filterFrom').value = firstDay;
    document.getElementById('filterTo').value = lastDay;

    document.getElementById('generateBtn').addEventListener('click', loadReports);
    document.getElementById('exportCsvBtn').addEventListener('click', () => exportData('csv'));
    document.getElementById('exportPdfBtn').addEventListener('click', () => exportData('pdf'));
    document.getElementById('exportExcelBtn').addEventListener('click', () => exportData('excel'));
    document.getElementById('importFile').addEventListener('change', onImportFileChange);
    document.getElementById('importBtn').addEventListener('click', importFile);

    loadReports();
});

// OFX/QIF statements are tied to one account (Sprint 18) — CSV import has no
// such requirement, so the account selector only appears when it's needed.
function detectImportFormat(filename) {
    const lower = filename.toLowerCase();
    if (lower.endsWith('.ofx') || lower.endsWith('.qfx')) return 'ofx';
    if (lower.endsWith('.qif')) return 'qif';
    if (lower.endsWith('.csv') || lower.endsWith('.txt')) return 'csv';
    return null;
}

function onImportFileChange() {
    const file = document.getElementById('importFile').files[0];
    const accountSelect = document.getElementById('importAccount');
    const format = file ? detectImportFormat(file.name) : null;

    if (format === 'ofx' || format === 'qif') {
        accountSelect.style.display = '';
        if (!accountSelect.dataset.loaded) loadAccountsForImport();
    } else {
        accountSelect.style.display = 'none';
    }
}

function loadAccountsForImport() {
    const accountSelect = document.getElementById('importAccount');
    fetch('/api/accounts/list')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            data.accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = account.name;
                accountSelect.appendChild(option);
            });
            accountSelect.dataset.loaded = '1';
        });
}

function buildParams() {
    const params = new URLSearchParams();
    const from = document.getElementById('filterFrom').value;
    const to = document.getElementById('filterTo').value;
    const type = document.getElementById('filterType').value;
    if (from) params.append('date_from', from);
    if (to) params.append('date_to', to);
    if (type) params.append('type', type);
    return params.toString();
}

function exportData(format) {
    const params = buildParams();
    window.location.href = `/api/export/${format}?${params}`;
}

function importFile() {
    const file = document.getElementById('importFile').files[0];
    const resultDiv = document.getElementById('importResult');
    if (!file) { Swal.fire({ icon: 'warning', title: 'No file selected' }); return; }

    const format = detectImportFormat(file.name);
    if (!format) {
        Swal.fire({ icon: 'warning', title: 'Unsupported file type', text: 'Use .csv, .txt, .ofx, .qfx or .qif' });
        return;
    }

    const fd = new FormData();
    fd.append('file', file);

    let endpoint = '/api/export/import/csv';
    if (format === 'ofx' || format === 'qif') {
        endpoint = `/api/export/import/${format}`;
        const accountId = document.getElementById('importAccount').value;
        if (!accountId) {
            Swal.fire({ icon: 'warning', title: 'Select a destination account' });
            return;
        }
        fd.append('account_id', accountId);
    }

    Swal.fire({ title: 'Importing...', didOpen: () => Swal.showLoading(), allowOutsideClick: false });

    fetch(endpoint, { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            Swal.close();
            resultDiv.innerHTML = '';
            const alert = document.createElement('div');
            alert.className = `alert alert-${data.success ? 'success' : 'danger'}`;
            if (data.success) {
                const summary = document.createElement('div');
                let summaryText = `Imported ${data.imported} transactions.`;
                if (typeof data.skipped_duplicate === 'number') {
                    summaryText += ` ${data.skipped_duplicate} duplicates skipped.`;
                }
                summary.textContent = summaryText;
                alert.appendChild(summary);
                if (data.errors && data.errors.length > 0) {
                    const errHead = document.createElement('strong');
                    errHead.textContent = `${data.errors.length} errors:`;
                    alert.appendChild(document.createElement('br'));
                    alert.appendChild(errHead);
                    data.errors.forEach(e => {
                        alert.appendChild(document.createElement('br'));
                        const span = document.createElement('span');
                        span.textContent = e;
                        alert.appendChild(span);
                    });
                }
            } else {
                alert.textContent = data.message;
            }
            resultDiv.appendChild(alert);
        })
        .catch(err => {
            Swal.close();
            resultDiv.innerHTML = '';
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger';
            alert.textContent = `Error: ${err.message}`;
            resultDiv.appendChild(alert);
        });
}

function loadReports() {
    Chart.defaults.color = cssVar('--ts');
    const params = new URLSearchParams({
        date_from: document.getElementById('filterFrom').value,
        date_to: document.getElementById('filterTo').value
    });

    fetch(`/api/export/reports/summary?${params.toString()}`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            document.getElementById('reportCharts').style.display = '';
            renderCategoryChart(data.by_category);
            renderMonthChart(data.by_month);
            renderAccountChart(data.by_account);
            renderCategoryTable(data.by_category);
        });
}

function renderCategoryChart(data) {
    const expenses = data.filter(d => d.type === 'expense');
    const ctx = document.getElementById('categoryChart').getContext('2d');
    if (categoryChartInst) categoryChartInst.destroy();
    const ac = cssVar('--ac');
    const ac2 = cssVar('--ac2');
    const palette = [ac, ac2,
        'rgba(255,255,255,0.45)', 'rgba(255,255,255,0.30)',
        'rgba(255,255,255,0.20)', 'rgba(255,255,255,0.15)',
        'rgba(255,255,255,0.10)', 'rgba(255,255,255,0.08)'];
    categoryChartInst = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: expenses.map(d => d.category),
            datasets: [{
                data: expenses.map(d => d.total),
                backgroundColor: palette,
                borderColor: cssVar('--rim'),
                borderWidth: 1
            }]
        },
        options: { plugins: { legend: { labels: { color: cssVar('--ts') } } } }
    });
}

function renderMonthChart(data) {
    const ctx = document.getElementById('monthChart').getContext('2d');
    if (monthChartInst) monthChartInst.destroy();
    const upColor = cssVar('--up');
    const dnColor = cssVar('--dn');
    monthChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.month),
            datasets: [
                { label: 'Income', data: data.map(d => d.income), backgroundColor: upColor + '55', borderColor: upColor, borderWidth: 1 },
                { label: 'Expenses', data: data.map(d => d.expenses), backgroundColor: dnColor + '55', borderColor: dnColor, borderWidth: 1 }
            ]
        },
        options: {
            plugins: { legend: { labels: { color: cssVar('--ts') } } },
            scales: {
                x: { ticks: { color: cssVar('--ts') }, grid: { color: cssVar('--th') } },
                y: { ticks: { color: cssVar('--ts') }, grid: { color: cssVar('--th') } }
            }
        }
    });
}

function renderAccountChart(data) {
    const ctx = document.getElementById('accountChart').getContext('2d');
    if (accountChartInst) accountChartInst.destroy();
    const upColor = cssVar('--up');
    const dnColor = cssVar('--dn');
    accountChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.account),
            datasets: [
                { label: 'Income', data: data.map(d => d.income), backgroundColor: upColor + '55', borderColor: upColor, borderWidth: 1 },
                { label: 'Expenses', data: data.map(d => d.expenses), backgroundColor: dnColor + '55', borderColor: dnColor, borderWidth: 1 }
            ]
        },
        options: {
            indexAxis: 'y',
            plugins: { legend: { labels: { color: cssVar('--ts') } } },
            scales: {
                x: { ticks: { color: cssVar('--ts') }, grid: { color: cssVar('--th') } },
                y: { ticks: { color: cssVar('--ts') }, grid: { color: cssVar('--th') } }
            }
        }
    });
}

function renderCategoryTable(data) {
    const tbody = document.getElementById('categoryTableBody');
    tbody.innerHTML = '';
    data.forEach(d => {
        const tr = document.createElement('tr');

        const catTd = document.createElement('td');
        catTd.textContent = d.category;

        const typeTd = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `glass-badge ${d.type === 'income' ? 'badge-income' : 'badge-expense'}`;
        badge.textContent = d.type;
        typeTd.appendChild(badge);

        const totalTd = document.createElement('td');
        totalTd.textContent = `RON ${d.total.toFixed(2)}`;

        const countTd = document.createElement('td');
        countTd.textContent = d.count;

        tr.appendChild(catTd);
        tr.appendChild(typeTd);
        tr.appendChild(totalTd);
        tr.appendChild(countTd);
        tbody.appendChild(tr);
    });
}
