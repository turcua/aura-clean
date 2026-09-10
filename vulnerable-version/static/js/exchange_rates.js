/**
 * Aura Financial Tracker - Vulnerable Version
 * Exchange Rates page controller (WITH INTENTIONAL VULNERABILITIES)
 * Sprint 17: Multi-Currency (static rates)
 */

document.addEventListener('DOMContentLoaded', function() {
    loadRates();
    document.getElementById('addRateBtn').addEventListener('click', addRate);
    document.getElementById('calcConvertBtn').addEventListener('click', runCalculator);
});

function loadRates() {
    fetch('/api/exchange-rates/list')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('ratesTableBody');
            tbody.innerHTML = '';
            if (!data.success) return;
            data.rates.forEach(r => {
                // VULNERABILITY: currency_code rendered via innerHTML — a
                // malicious currency_code stored via the update endpoint
                // (VULN-066) executes here (stored XSS)
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${r.currency_code}</td>
                    <td>${r.is_base ? '1.000000 (base)' : `<input type="number" class="glass-input rate-input" style="max-width:160px;" step="0.000001" value="${r.rate_to_base}">`}</td>
                    <td>${r.updated_at || '—'}</td>
                    <td>${r.is_base ? '' : '<button type="button" class="btn btn-sm btn-secondary save-rate-btn">Save</button>'}</td>
                    <td>${r.is_base ? '' : '<button type="button" class="btn btn-sm btn-secondary delete-rate-btn">Delete</button>'}</td>
                `;
                if (!r.is_base) {
                    tr.querySelector('.save-rate-btn').addEventListener('click', () => {
                        const val = tr.querySelector('.rate-input').value;
                        saveRate(r.currency_code, val);
                    });
                    tr.querySelector('.delete-rate-btn').addEventListener('click', () => deleteRate(r.id, r.currency_code));
                }
                tbody.appendChild(tr);
            });
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
        const toOpt = fromOpt.cloneNode(true);
        toSel.appendChild(toOpt);
    });
    if (prevFrom) fromSel.value = prevFrom;
    if (prevTo) toSel.value = prevTo;
}

function deleteRate(rateId, currencyCode) {
    // VULNERABILITY: No confirmation needed server-side, no auth, no CSRF
    Swal.fire({
        title: 'Delete Rate?',
        text: `Delete this ${currencyCode} rate row? (Other rows for the same code, if any, are left alone.)`,
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (!result.isConfirmed) return;
        fetch(`/api/exchange-rates/${rateId}/delete`, {method: 'POST'})
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

    fetch(`/api/exchange-rates/convert?amount=${encodeURIComponent(amount)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`)
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

function addRate() {
    const code = document.getElementById('newCurrencyCode').value;
    const rate = document.getElementById('newRateValue').value;
    saveRate(code, rate);
}

function saveRate(currencyCode, rateValue) {
    // VULNERABILITY: No CSRF protection, no auth, no validation — negative/
    // zero/absurd rates and arbitrary currency codes are all accepted
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
