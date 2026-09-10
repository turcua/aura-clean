/**
 * Aura Financial Tracker - Secure Version
 * Exchange Rates page controller
 * Sprint 17: Multi-Currency (static rates)
 *
 * Loaded as an external <script src> (CSP script-src 'self' — no inline
 * scripts/onclick). Every dynamic node is built with document.createElement
 * / textContent — no innerHTML on server-supplied data.
 */

document.addEventListener('DOMContentLoaded', function() {
    loadRates();
    document.getElementById('calcConvertBtn').addEventListener('click', runCalculator);
    document.getElementById('addCurrencyBtn').addEventListener('click', addCurrency);
});

function loadRates() {
    fetch('/api/exchange-rates/list')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('ratesTableBody');
            tbody.innerHTML = '';
            if (!data.success) {
                const tr = document.createElement('tr');
                const td = document.createElement('td');
                td.colSpan = 5;
                td.textContent = 'Failed to load exchange rates.';
                tr.appendChild(td);
                tbody.appendChild(tr);
                return;
            }
            data.rates.forEach(r => tbody.appendChild(buildRateRow(r)));
            populateCalculatorOptions(data.rates);
        })
        .catch(() => {});
}

function populateCalculatorOptions(rates) {
    const fromSel = document.getElementById('calcFrom');
    const toSel = document.getElementById('calcTo');
    const prevFrom = fromSel.value;
    const prevTo = toSel.value;
    fromSel.innerHTML = '';
    toSel.innerHTML = '';
    rates.forEach(r => {
        const fromOpt = document.createElement('option');
        fromOpt.value = r.currency_code;
        fromOpt.textContent = r.currency_code;
        fromSel.appendChild(fromOpt);
        toSel.appendChild(fromOpt.cloneNode(true));
    });
    if (prevFrom) fromSel.value = prevFrom;
    if (prevTo) toSel.value = prevTo;
    else if (toSel.querySelector('option[value="USD"]')) toSel.value = 'USD';
}

function addCurrency() {
    const code = document.getElementById('newCurrencyCode').value.trim().toUpperCase();
    const rate = document.getElementById('newRateValue').value;

    fetch('/api/currencies/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code, initial_rate_to_base: rate})
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Currency Added', timer: 1200, showConfirmButton: false});
                document.getElementById('newCurrencyCode').value = '';
                document.getElementById('newRateValue').value = '';
                loadRates();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function buildRateRow(r) {
    const tr = document.createElement('tr');

    const codeTd = document.createElement('td');
    codeTd.textContent = r.currency_code;
    tr.appendChild(codeTd);

    const rateTd = document.createElement('td');
    if (r.is_base) {
        rateTd.textContent = '1.000000 (base)';
        tr.appendChild(rateTd);
        const updatedTd = document.createElement('td');
        updatedTd.textContent = '—';
        tr.appendChild(updatedTd);
        tr.appendChild(document.createElement('td'));
        tr.appendChild(document.createElement('td'));
        return tr;
    }

    const input = document.createElement('input');
    input.type = 'number';
    input.className = 'glass-input';
    input.style.maxWidth = '160px';
    input.step = '0.000001';
    input.min = '0.000001';
    input.value = r.rate_to_base;
    rateTd.appendChild(input);
    tr.appendChild(rateTd);

    const updatedTd = document.createElement('td');
    updatedTd.textContent = r.updated_at || '—';
    tr.appendChild(updatedTd);

    const actionTd = document.createElement('td');
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn btn-sm btn-secondary';
    saveBtn.textContent = 'Save';
    saveBtn.addEventListener('click', () => saveRate(r.currency_code, input.value));
    actionTd.appendChild(saveBtn);
    tr.appendChild(actionTd);

    const deleteTd = document.createElement('td');
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-sm btn-secondary';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', () => deleteRate(r.currency_code));
    deleteTd.appendChild(deleteBtn);
    tr.appendChild(deleteTd);

    return tr;
}

function deleteRate(currencyCode) {
    Swal.fire({
        title: 'Delete Rate?',
        text: `Delete the ${currencyCode} exchange rate? Accounts in ${currencyCode} will no longer convert into RON totals until a new rate is added.`,
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (!result.isConfirmed) return;
        fetch(`/api/exchange-rates/${currencyCode}/delete`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({icon: 'success', title: 'Deleted', timer: 1200, showConfirmButton: false});
                    loadRates();
                } else {
                    Swal.fire({icon: 'error', title: 'Error', text: data.message});
                }
            });
    });
}

function runCalculator() {
    const amount = document.getElementById('calcAmount').value;
    const from = document.getElementById('calcFrom').value;
    const to = document.getElementById('calcTo').value;
    const resultEl = document.getElementById('calcResult');

    fetch(`/api/exchange-rates/convert?amount=${encodeURIComponent(amount)}&from=${from}&to=${to}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                resultEl.textContent = `${amount} ${from} = ${data.result} ${to}`;
            } else {
                resultEl.textContent = '';
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}

function saveRate(currencyCode, rateValue) {
    fetch(`/api/exchange-rates/${currencyCode}/update`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rate_to_base: rateValue})
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                Swal.fire({icon: 'success', title: 'Rate Updated', timer: 1200, showConfirmButton: false});
                loadRates();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
        });
}
