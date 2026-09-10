/**
 * Aura Financial Tracker - Secure Version
 * Loan Intelligence page controller
 * Sprint 30: Beast Breathing - Devour
 */

let currentLoanId = null;
let currentLoanMargin = null;
let loanMarginById = {};

const LOAN_PAGE_SIZE = 10;
let timelineItems = [];
let timelinePage = 1;
let paymentImpactItems = [];
let paymentImpactPage = 1;

function renderPaginationBar(containerId, page, totalPages, totalCount, onChange) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    if (totalPages <= 1) return;

    const firstBtn = document.createElement('button');
    firstBtn.type = 'button';
    firstBtn.className = 'btn-glass btn-glass-secondary';
    firstBtn.textContent = 'First';
    firstBtn.disabled = page <= 1;
    firstBtn.addEventListener('click', () => onChange(1));

    const prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'btn-glass btn-glass-secondary';
    prevBtn.textContent = 'Previous';
    prevBtn.disabled = page <= 1;
    prevBtn.addEventListener('click', () => onChange(page - 1));

    const info = document.createElement('span');
    info.className = 'pagination-info';
    info.textContent = `Page ${page} of ${totalPages} (${totalCount} item${totalCount !== 1 ? 's' : ''})`;

    const nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'btn-glass btn-glass-secondary';
    nextBtn.textContent = 'Next';
    nextBtn.disabled = page >= totalPages;
    nextBtn.addEventListener('click', () => onChange(page + 1));

    const lastBtn = document.createElement('button');
    lastBtn.type = 'button';
    lastBtn.className = 'btn-glass btn-glass-secondary';
    lastBtn.textContent = 'Last';
    lastBtn.disabled = page >= totalPages;
    lastBtn.addEventListener('click', () => onChange(totalPages));

    const jumpForm = document.createElement('form');
    jumpForm.className = 'pagination-jump';
    const jumpInput = document.createElement('input');
    jumpInput.type = 'number';
    jumpInput.className = 'glass-input pagination-jump-input';
    jumpInput.min = 1;
    jumpInput.max = totalPages;
    jumpInput.placeholder = 'Page';
    jumpInput.setAttribute('aria-label', 'Jump to page');
    const jumpBtn = document.createElement('button');
    jumpBtn.type = 'submit';
    jumpBtn.className = 'btn-glass btn-glass-secondary';
    jumpBtn.textContent = 'Go';
    jumpForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const target = parseInt(jumpInput.value, 10);
        if (!isNaN(target) && target >= 1 && target <= totalPages) onChange(target);
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

document.addEventListener('DOMContentLoaded', function () {
    loadLoans();
    loadLoanCurrencies();
    document.getElementById('eventType').addEventListener('change', toggleEventFields);
    document.getElementById('saveEventBtn').addEventListener('click', saveEvent);
    document.getElementById('eventDate').valueAsDate = new Date();
    document.getElementById('saveLoanBtn').addEventListener('click', saveLoan);
    document.getElementById('editLoanModal').addEventListener('show.bs.modal', populateEditLoanForm);
    document.getElementById('saveLoanEditBtn').addEventListener('click', saveLoanEdit);
    document.getElementById('deleteLoanBtn').addEventListener('click', deleteLoan);
    document.getElementById('interestPerRonUpdateBtn').addEventListener('click', () => loadInterestPerRon(currentLoanId));
    setupInterestPerRonPeriodBar();
    document.getElementById('whatIfSimulateBtn').addEventListener('click', runWhatIf);
    setupChartDropZone();
    initLoanCardMinimize();
    initLoanCardInfoPopovers();
});

// ── Card minimize / maximize (Sprint 33) ────────────────────────────────────
// Same interaction and icon as the Dashboard's widget minimize button, but
// these cards aren't backed by a dashboard_widgets row — there's nothing to
// persist state to server-side, so this uses localStorage instead, same
// pattern already used for sidebar-collapse and theme preference.
const LOAN_MINIMIZED_KEY = 'aura-loan-cards-minimized';

function getMinimizedLoanCards() {
    try {
        return JSON.parse(localStorage.getItem(LOAN_MINIMIZED_KEY)) || [];
    } catch (e) {
        return [];
    }
}

function setLoanCardMinimized(cardId, minimized) {
    let ids = getMinimizedLoanCards();
    if (minimized && !ids.includes(cardId)) ids.push(cardId);
    if (!minimized) ids = ids.filter(id => id !== cardId);
    localStorage.setItem(LOAN_MINIMIZED_KEY, JSON.stringify(ids));
}

function applyLoanCardMinimizedState(cardId, minimized) {
    const body = document.querySelector(`[data-card-body="${cardId}"]`);
    const btn = document.querySelector(`.loan-card-minimize-btn[data-card="${cardId}"]`);
    if (!body || !btn) return;
    body.classList.toggle('is-collapsed', minimized);
    const card = body.closest('.glass-card');
    if (card) card.classList.toggle('is-minimized', minimized);
    const poly = btn.querySelector('polyline');
    if (poly) poly.setAttribute('points', minimized ? '3,10 8,5 13,10' : '3,6 8,11 13,6');
}

function initLoanCardMinimize() {
    const minimizedIds = getMinimizedLoanCards();
    document.querySelectorAll('.loan-card-minimize-btn').forEach(btn => {
        const cardId = btn.dataset.card;
        applyLoanCardMinimizedState(cardId, minimizedIds.includes(cardId));
        btn.addEventListener('click', () => {
            const body = document.querySelector(`[data-card-body="${cardId}"]`);
            const willMinimize = !body.classList.contains('is-collapsed');
            applyLoanCardMinimizedState(cardId, willMinimize);
            setLoanCardMinimized(cardId, willMinimize);
        });
    });
}

// ── Card info popovers (Sprint 33 follow-up) ────────────────────────────────
// The per-card explanatory text used to sit inline in the card body, eating
// into the space available for the actual chart/data — moved behind an "i"
// button (Bootstrap Popover, focus-triggered so it works on touch, not just
// hover) so every card can dedicate its fixed 360px row height to content
// instead of prose.
function initLoanCardInfoPopovers() {
    document.querySelectorAll('.loan-card-info-btn').forEach(btn => {
        new bootstrap.Popover(btn, { trigger: 'focus' });
    });
}

function loadLoanCurrencies() {
    fetch('/api/currencies/list')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            // Populates both the Add Loan and Edit Loan (Sprint 51) currency
            // selects — same option list, two independent <select>s.
            ['addLoanCurrency', 'editLoanCurrency'].forEach(id => {
                const sel = document.getElementById(id);
                if (!sel) return;
                sel.innerHTML = '';
                data.currencies.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.code;
                    opt.textContent = c.code;
                    sel.appendChild(opt);
                });
            });
        })
        .catch(err => console.error(err));
}

function saveLoan() {
    const form = document.getElementById('addLoanForm');
    const fd = new FormData(form);

    const data = {
        name: fd.get('name'),
        principal: parseFloat(fd.get('principal')),
        currency: fd.get('currency'),
        margin_pct: parseFloat(fd.get('margin_pct')),
        initial_base_index_pct: parseFloat(fd.get('initial_base_index_pct')),
        start_date: fd.get('start_date'),
        original_term_months: parseInt(fd.get('original_term_months'), 10),
    };

    fetch('/api/loans/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                Swal.fire({icon: 'success', title: 'Loan Added!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('addLoanModal')).hide();
                form.reset();
                loadLoans();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: result.message});
            }
        })
        .catch(err => console.error(err));
}

// ── Edit / Delete Loan (Sprint 51, ENH-01) ──────────────────────────────────
function populateEditLoanForm() {
    if (!currentLoanId) return;
    fetch(`/api/loans/${currentLoanId}`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const form = document.getElementById('editLoanForm');
            form.querySelector('[name="name"]').value = data.loan.name;
            form.querySelector('[name="currency"]').value = data.loan.currency;
            form.querySelector('[name="margin_pct"]').value = data.loan.margin_pct;
        })
        .catch(err => console.error(err));
}

function saveLoanEdit() {
    if (!currentLoanId) return;
    const form = document.getElementById('editLoanForm');
    const fd = new FormData(form);

    const data = {
        name: fd.get('name'),
        currency: fd.get('currency'),
        margin_pct: parseFloat(fd.get('margin_pct')),
    };

    fetch(`/api/loans/${currentLoanId}/update`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                Swal.fire({icon: 'success', title: 'Loan Updated!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('editLoanModal')).hide();
                loadLoans();
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: result.message});
            }
        })
        .catch(err => console.error(err));
}

function deleteLoan() {
    if (!currentLoanId) return;
    Swal.fire({
        title: 'Delete Loan?',
        text: 'This deletes the loan and its event history. Transactions tagged to it are kept, just unlinked. This cannot be undone.',
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (!result.isConfirmed) return;
        fetch(`/api/loans/${currentLoanId}/delete`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    Swal.fire({icon: 'error', title: 'Error', text: data.message});
                    return;
                }
                Swal.fire({icon: 'success', title: 'Loan Deleted', timer: 1500, showConfirmButton: false});
                currentLoanId = null;
                loadLoans();
            })
            .catch(err => console.error(err));
    });
}

function runWhatIf() {
    if (!currentLoanId) return;
    const amount = parseFloat(document.getElementById('whatIfMonthlyAmount').value) || 0;
    if (amount <= 0) return;
    const startDate = document.getElementById('whatIfStartDate').value;

    let url = `/api/loans/${currentLoanId}/what-if?monthly_amount=${amount}`;
    if (startDate) url += `&start_date=${startDate}`;

    const btn = document.getElementById('whatIfSimulateBtn');
    btn.disabled = true;
    fetch(url)
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            if (!data.success) {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
                return;
            }
            renderWhatIfResult(data);
        })
        .catch(err => {
            btn.disabled = false;
            console.error(err);
        });
}

function renderWhatIfResult(data) {
    const container = document.getElementById('whatIfResult');
    container.innerHTML = '';

    const wrap = document.createElement('div');
    wrap.style.cssText = 'padding:14px 16px;border-radius:8px;background:rgba(13,148,136,0.08);';

    const payoffLine = document.createElement('div');
    payoffLine.style.cssText = 'font-size:1.15rem;font-weight:600;';
    if (data.new_payoff_date) {
        payoffLine.textContent = `New payoff date: ${data.new_payoff_date}`;
        if (data.term_saved_months != null) {
            payoffLine.textContent += ` (${data.term_saved_months} months sooner than ${data.actual_payoff_date})`;
        }
    } else {
        payoffLine.textContent = 'Payoff date unavailable for this scenario';
    }
    wrap.appendChild(payoffLine);

    const interestLine = document.createElement('div');
    interestLine.style.cssText = 'font-size:0.9rem;color:var(--ts);margin-top:4px;';
    interestLine.textContent = `Interest saved: ${formatMoney(data.interest_saved, 'RON')} (starting ${data.start_date})`;
    wrap.appendChild(interestLine);

    container.appendChild(wrap);
}

let interestPerRonChartInstance = null;
let interestPerRonPeriod = 'full';

function setupInterestPerRonPeriodBar() {
    document.querySelectorAll('#interestPerRonPeriods .period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#interestPerRonPeriods .period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            interestPerRonPeriod = btn.dataset.period;
            loadInterestPerRon(currentLoanId);
        });
    });
}

function loadInterestPerRon(loanId) {
    if (!loanId) return;
    const amount = parseFloat(document.getElementById('interestPerRonAmount').value) || 1000;
    fetch(`/api/loans/${loanId}/interest-per-ron?amount=${amount}&months=${interestPerRonPeriod}`)
        .then(r => r.json())
        .then(data => {
            // Render even on failure (with an empty curve) so the loading
            // spinner always gets dismissed — otherwise a failed request
            // leaves it spinning forever instead of just showing an empty chart.
            renderInterestPerRonChart(data.success ? data.curve : []);
        })
        .catch(err => console.error(err));
}

function renderInterestPerRonChart(curve) {
    document.getElementById('interestPerRonChartSpinner').style.display = 'none';
    document.getElementById('interestPerRonChart').style.display = '';
    const ctx = document.getElementById('interestPerRonChart').getContext('2d');
    if (interestPerRonChartInstance) {
        interestPerRonChartInstance.destroy();
    }
    interestPerRonChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: curve.map(c => c.date),
            datasets: [{
                label: 'Interest Saved (RON)',
                data: curve.map(c => c.interest_saved),
                borderColor: '#0d9488',
                backgroundColor: 'rgba(13, 148, 136, 0.15)',
                fill: true,
                tension: 0.2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        afterLabel: (context) => {
                            const point = curve[context.dataIndex];
                            return point.new_payoff_date ? `New payoff date: ${point.new_payoff_date}` : '';
                        },
                    },
                },
            },
            scales: {
                y: {beginAtZero: true},
                x: {ticks: {maxTicksLimit: 12, autoSkip: true}},
            },
        },
    });
}

function setupChartDropZone() {
    const dropZone = document.getElementById('chartDropZone');
    const fileInput = document.getElementById('chartFileInput');

    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) uploadChart(fileInput.files[0]);
    });
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--ac, #5b8def)';
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--gb)';
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--gb)';
        if (e.dataTransfer.files.length) uploadChart(e.dataTransfer.files[0]);
    });
}

function uploadChart(file) {
    if (!currentLoanId) return;
    const dropZoneText = document.querySelector('#chartDropZone p');
    const originalText = dropZoneText.textContent;
    dropZoneText.textContent = 'Reading PDF...';

    const fd = new FormData();
    fd.append('file', file);

    fetch(`/api/loans/${currentLoanId}/parse-chart`, {method: 'POST', body: fd})
        .then(r => r.json())
        .then(result => {
            dropZoneText.textContent = originalText;
            if (!result.success) {
                Swal.fire({icon: 'error', title: 'Could not read PDF', text: result.message});
                return;
            }

            // A real chart maps to a bank_snapshot event, not a rate change
            document.getElementById('eventType').value = 'bank_snapshot';
            toggleEventFields();

            const g = result.guessed;
            if (g.remaining_principal != null) document.querySelector('[name="remaining_principal"]').value = g.remaining_principal;
            if (g.remaining_term_months != null) document.querySelector('[name="remaining_term_months"]').value = g.remaining_term_months;
            if (g.current_rate_pct != null) document.querySelector('[name="current_rate_pct"]').value = g.current_rate_pct;
            if (g.remaining_interest_total != null) document.querySelector('[name="remaining_interest_total"]').value = g.remaining_interest_total;
            if (g.reported_installment != null) document.querySelector('[name="reported_installment"]').value = g.reported_installment;
            if (g.effective_date != null) {
                document.getElementById('eventDate').value = g.effective_date;
            } else {
                // Unlike the numeric fields above, this input defaults to
                // today's date on page load — leaving it untouched here would
                // make a failed extraction look like a real, deliberately-
                // entered value instead of a visibly-empty field the user
                // would notice and fill in, the way the other guessed fields
                // already behave on failure.
                document.getElementById('eventDate').value = '';
            }

            document.getElementById('chartRawText').textContent = result.raw_text;
            document.getElementById('chartRawTextWrap').style.display = 'block';

            if (g.effective_date == null) {
                Swal.fire({icon: 'warning', title: 'Date not detected', text: 'Could not find this chart\'s date automatically — please enter the Effective Date manually before saving. Other fields were pre-filled where possible; review them too.'});
            } else {
                Swal.fire({icon: 'info', title: 'Fields pre-filled', text: 'Extraction is a best-effort guess — please review the values below before saving.', timer: 3000, showConfirmButton: false});
            }
        })
        .catch(err => {
            dropZoneText.textContent = originalText;
            console.error(err);
        });
}

function toggleEventFields() {
    const type = document.getElementById('eventType').value;
    document.getElementById('rateChangeFields').style.display = type === 'rate_change' ? 'block' : 'none';
    document.getElementById('bankSnapshotFields').style.display = type === 'bank_snapshot' ? 'block' : 'none';
}

function saveEvent() {
    if (!currentLoanId) return;
    const form = document.getElementById('logEventForm');
    const fd = new FormData(form);
    const eventType = fd.get('event_type');

    const payload = eventType === 'rate_change'
        ? {new_base_index_pct: parseFloat(fd.get('new_base_index_pct'))}
        : {
            remaining_principal: parseFloat(fd.get('remaining_principal')),
            remaining_term_months: parseInt(fd.get('remaining_term_months'), 10),
            current_rate_pct: parseFloat(fd.get('current_rate_pct')),
            // Optional — blank input parses to NaN, which JSON.stringify
            // serializes as null, matching this field's nullable handling
            // all the way through the backend and engine.
            remaining_interest_total: parseFloat(fd.get('remaining_interest_total')),
            reported_installment: parseFloat(fd.get('reported_installment')),
        };

    const data = {
        event_type: eventType,
        effective_date: fd.get('effective_date'),
        payload: payload,
    };

    fetch(`/api/loans/${currentLoanId}/events`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                Swal.fire({icon: 'success', title: 'Event Logged!', timer: 1500, showConfirmButton: false});
                bootstrap.Modal.getInstance(document.getElementById('logEventModal')).hide();
                form.reset();
                document.getElementById('eventDate').valueAsDate = new Date();
                toggleEventFields();
                document.getElementById('chartRawTextWrap').style.display = 'none';
                document.getElementById('chartFileInput').value = '';
                loadLoanData(currentLoanId);
            } else {
                Swal.fire({icon: 'error', title: 'Error', text: result.message});
            }
        })
        .catch(err => console.error(err));
}

function loadLoans() {
    fetch('/api/loans/list')
        .then(r => r.json())
        .then(data => {
            const emptyState = document.getElementById('loanEmptyState');
            const content = document.getElementById('loanContent');
            const logEventBtn = document.getElementById('logEventBtn');

            if (!data.success || data.loans.length === 0) {
                emptyState.style.display = 'block';
                content.style.display = 'none';
                logEventBtn.style.display = 'none';
                document.getElementById('loanActionsRow').style.display = 'none';
                return;
            }

            emptyState.style.display = 'none';
            content.style.display = 'block';
            logEventBtn.style.display = 'inline-block';
            document.getElementById('loanActionsRow').style.display = 'flex';

            const select = document.getElementById('loanSelect');
            select.innerHTML = '';
            loanMarginById = {};
            data.loans.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.id;
                opt.textContent = l.name;
                select.appendChild(opt);
                loanMarginById[l.id] = l.margin_pct;
            });

            document.getElementById('loanSelectRow').style.display = data.loans.length > 1 ? 'flex' : 'none';
            select.addEventListener('change', () => loadLoanData(select.value));

            loadLoanData(data.loans[0].id);
        })
        .catch(err => console.error(err));
}

function loadLoanData(loanId) {
    currentLoanId = loanId;
    currentLoanMargin = loanMarginById[loanId];
    loadStatus(loanId);
    loadTimeline(loanId);
    loadPaymentImpact(loanId);
    loadInterestPerRon(loanId);
    loadRecentlyDeleted(loanId);
    loadPaymentLedger(loanId);
}

// ── Payment Ledger (Sprint 51, ENH-13) ──────────────────────────────────────
function loadPaymentLedger(loanId) {
    fetch(`/api/loans/${loanId}/payment-ledger`)
        .then(r => r.json())
        .then(data => renderPaymentLedger((data.success && data.ledger) ? data.ledger : []))
        .catch(err => console.error(err));
}

function renderPaymentLedger(ledger) {
    const container = document.getElementById('paymentLedgerList');
    container.innerHTML = '';

    if (ledger.length === 0) {
        const empty = document.createElement('p');
        empty.style.cssText = 'text-align:center;color:var(--th);padding:24px 0;';
        empty.textContent = 'No payments tagged to this loan yet.';
        container.appendChild(empty);
        return;
    }

    ledger.forEach(entry => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:10px 20px;border-bottom:1px solid var(--gb);';

        const left = document.createElement('div');
        const dateEl = document.createElement('div');
        dateEl.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
        dateEl.textContent = entry.date;
        const detailEl = document.createElement('small');
        detailEl.style.cssText = 'color:var(--ts);';
        detailEl.textContent = entry.description || '';
        left.appendChild(dateEl);
        if (entry.description) left.appendChild(detailEl);

        const right = document.createElement('div');
        right.style.cssText = 'display:flex;align-items:center;gap:8px;';

        const badge = document.createElement('span');
        badge.className = entry.payment_type === 'scheduled' ? 'glass-badge' : 'glass-badge badge-income';
        badge.textContent = entry.payment_type === 'scheduled' ? 'Scheduled' : 'Extra';
        right.appendChild(badge);

        const amount = document.createElement('span');
        amount.style.fontVariantNumeric = 'tabular-nums';
        amount.textContent = formatMoney(entry.amount, 'RON');
        right.appendChild(amount);

        row.appendChild(left);
        row.appendChild(right);
        container.appendChild(row);
    });
}

// ── Recently Deleted / restore (Sprint 49) ──────────────────────────────────
function loadRecentlyDeleted(loanId) {
    fetch(`/api/loans/${loanId}/events/deleted`)
        .then(r => r.json())
        .then(data => renderRecentlyDeleted((data.success && data.events) ? data.events : []))
        .catch(err => console.error(err));
}

function renderRecentlyDeleted(events) {
    const wrap = document.getElementById('recentlyDeletedWrap');
    const container = document.getElementById('recentlyDeletedList');
    document.getElementById('recentlyDeletedCount').textContent = events.length;
    container.innerHTML = '';

    if (events.length === 0) {
        wrap.style.display = 'none';
        return;
    }
    wrap.style.display = '';
    events.forEach(e => container.appendChild(buildRecentlyDeletedRow(eventToTimelineItem(e))));
}

function buildRecentlyDeletedRow(item) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:10px 20px;border-bottom:1px solid var(--gb);opacity:0.75;';

    const left = document.createElement('div');
    const dateEl = document.createElement('div');
    dateEl.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
    dateEl.textContent = item.date;
    const detailEl = document.createElement('small');
    detailEl.style.cssText = 'color:var(--ts);font-variant-numeric:tabular-nums;';
    detailEl.textContent = item.detail;
    left.appendChild(dateEl);
    left.appendChild(detailEl);

    const right = document.createElement('div');
    right.style.cssText = 'display:flex;align-items:center;gap:8px;';

    const badge = document.createElement('span');
    badge.className = item.badgeClass;
    badge.style.fontVariantNumeric = 'tabular-nums';
    badge.textContent = item.badge;
    right.appendChild(badge);

    const restoreBtn = document.createElement('button');
    restoreBtn.type = 'button';
    restoreBtn.className = 'btn-glass btn-glass-secondary';
    restoreBtn.style.cssText = 'padding:4px 10px;font-size:0.75rem;';
    restoreBtn.textContent = 'Restore';
    restoreBtn.addEventListener('click', () => restoreEvent(item.eventId));
    right.appendChild(restoreBtn);

    row.appendChild(left);
    row.appendChild(right);
    return row;
}

function restoreEvent(eventId) {
    const loanId = currentLoanId;
    fetch(`/api/loans/${loanId}/events/${eventId}/restore`, {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
                return;
            }
            if (loanId === currentLoanId) loadLoanData(currentLoanId);
        })
        .catch(err => console.error(err));
}

let efficiencyTrendChartInstance = null;

function loadPaymentImpact(loanId) {
    fetch(`/api/loans/${loanId}/payment-impact`)
        .then(r => r.json())
        .then(data => {
            paymentImpactItems = (data.success && data.payments) ? data.payments : [];
            paymentImpactPage = 1;
            renderPaymentImpactPage();
            renderEfficiencyTrendChart((data.success && data.efficiency_trend) ? data.efficiency_trend : []);
        })
        .catch(err => console.error(err));
}

function renderEfficiencyTrendChart(trend) {
    document.getElementById('efficiencyTrendChartSpinner').style.display = 'none';
    document.getElementById('efficiencyTrendChart').style.display = '';
    const ctx = document.getElementById('efficiencyTrendChart').getContext('2d');
    if (efficiencyTrendChartInstance) {
        efficiencyTrendChartInstance.destroy();
        efficiencyTrendChartInstance = null;
    }
    if (trend.length === 0) return;

    efficiencyTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.map(t => t.date),
            datasets: [
                {
                    label: 'Efficiency (%)',
                    data: trend.map(t => t.efficiency_pct),
                    borderColor: '#0d9488',
                    backgroundColor: 'transparent',
                    pointRadius: 2,
                    tension: 0.2,
                },
                {
                    label: '3-Payment Moving Average (%)',
                    data: trend.map(t => t.moving_avg_pct),
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {legend: {display: true, labels: {boxWidth: 12, font: {size: 10}}}},
            scales: {y: {beginAtZero: true}},
        },
    });
}

function renderPaymentImpactPage() {
    const container = document.getElementById('paymentImpactList');
    container.innerHTML = '';

    if (paymentImpactItems.length === 0) {
        container.appendChild(emptyMsg('No extra payments logged yet.'));
        document.getElementById('paymentImpactPagination').innerHTML = '';
        return;
    }

    const totalPages = Math.max(Math.ceil(paymentImpactItems.length / LOAN_PAGE_SIZE), 1);
    paymentImpactPage = Math.min(Math.max(paymentImpactPage, 1), totalPages);
    const start = (paymentImpactPage - 1) * LOAN_PAGE_SIZE;
    paymentImpactItems.slice(start, start + LOAN_PAGE_SIZE).forEach(p => container.appendChild(buildPaymentImpactRow(p)));

    renderPaginationBar('paymentImpactPagination', paymentImpactPage, totalPages, paymentImpactItems.length, (page) => {
        paymentImpactPage = page;
        renderPaymentImpactPage();
    });
}

function buildPaymentImpactRow(p) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-bottom:1px solid var(--gb);';

    const left = document.createElement('div');
    const dateEl = document.createElement('div');
    dateEl.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
    dateEl.textContent = `${p.date} — ${formatMoney(p.amount, 'RON')}`;
    const detailEl = document.createElement('small');
    detailEl.style.cssText = 'color:var(--ts);font-variant-numeric:tabular-nums;';
    let detailText = p.term_impact_months != null
        ? `Payoff ${p.term_impact_months} month${p.term_impact_months === 1 ? '' : 's'} sooner`
        : 'Term impact unavailable';
    if (p.efficiency_pct != null) detailText += ` · Efficiency: ${p.efficiency_pct}%`;
    if (p.ron_per_month_saved != null) detailText += ` · ${formatMoney(p.ron_per_month_saved, 'RON')}/month`;
    detailEl.textContent = detailText;
    left.appendChild(dateEl);
    left.appendChild(detailEl);

    const impact = document.createElement('span');
    impact.className = 'glass-badge badge-income';
    impact.style.fontVariantNumeric = 'tabular-nums';
    impact.textContent = `${formatMoney(p.interest_impact, 'RON')} saved`;

    row.appendChild(left);
    row.appendChild(impact);
    return row;
}

function loadStatus(loanId) {
    fetch(`/api/loans/${loanId}/status`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            document.getElementById('currentBalanceDisplay').textContent =
                data.current_balance != null ? formatMoney(data.current_balance, 'RON') : '—';
            document.getElementById('currentInstallmentDisplay').textContent =
                data.current_installment != null ? formatMoney(data.current_installment, 'RON') : '—';
            document.getElementById('payoffDateDisplay').textContent = data.payoff_date || '—';

            const headline = document.getElementById('savingsHeadline');
            if (data.years_saved != null && data.interest_saved != null) {
                headline.textContent = `${data.years_saved} years (${data.months_saved} months) and ${formatMoney(data.interest_saved, 'RON')} saved so far`;
            } else {
                headline.textContent = 'Not enough data yet to estimate savings';
            }

            document.getElementById('savingsBaselinePayoff').textContent = data.baseline_payoff_date || '—';
            document.getElementById('savingsYearsRemaining').textContent =
                data.years_remaining != null ? `${data.years_remaining} years (${data.months_remaining} months)` : '—';
        })
        .catch(err => console.error(err));
}

function loadTimeline(loanId) {
    Promise.all([
        fetch(`/api/loans/${loanId}/events`).then(r => r.json()),
        fetch(`/api/transactions/list?loan_id=${loanId}`).then(r => r.json()),
    ])
        .then(([eventsData, txData]) => {
            const items = [];
            if (eventsData.success) {
                eventsData.events.forEach(e => items.push(eventToTimelineItem(e)));
            }
            if (txData.success) {
                txData.transactions.forEach(t => items.push(transactionToTimelineItem(t)));
            }
            items.sort((a, b) => b.date.localeCompare(a.date));
            timelineItems = items;
            timelinePage = 1;
            renderTimelinePage();
        })
        .catch(err => console.error(err));
}

function renderTimelinePage() {
    const container = document.getElementById('timelineList');
    container.innerHTML = '';

    if (timelineItems.length === 0) {
        const empty = document.createElement('p');
        empty.style.cssText = 'text-align:center;color:var(--th);padding:24px 0;';
        empty.textContent = 'No events logged yet.';
        container.appendChild(empty);
        document.getElementById('timelinePagination').innerHTML = '';
        return;
    }

    const totalPages = Math.max(Math.ceil(timelineItems.length / LOAN_PAGE_SIZE), 1);
    timelinePage = Math.min(Math.max(timelinePage, 1), totalPages);
    const start = (timelinePage - 1) * LOAN_PAGE_SIZE;
    timelineItems.slice(start, start + LOAN_PAGE_SIZE).forEach(item => container.appendChild(buildTimelineRow(item)));

    renderPaginationBar('timelinePagination', timelinePage, totalPages, timelineItems.length, (page) => {
        timelinePage = page;
        renderTimelinePage();
    });
}

function eventToTimelineItem(e) {
    let badge = e.event_type;
    let detail = '';
    if (e.event_type === 'rate_change') {
        badge = 'Rate Change';
        const baseIndex = parseFloat(e.payload.new_base_index_pct);
        const totalRate = currentLoanMargin != null ? (baseIndex + parseFloat(currentLoanMargin)).toFixed(3) : null;
        detail = totalRate != null
            ? `Base index: ${baseIndex}% + ${currentLoanMargin}% margin = ${totalRate}% total rate`
            : `New base index: ${baseIndex}%`;
    } else if (e.event_type === 'bank_snapshot') {
        badge = 'Bank Snapshot';
        detail = `Balance: ${formatMoney(e.payload.remaining_principal, 'RON')} · Rate: ${e.payload.current_rate_pct}% · ${e.payload.remaining_term_months} months remaining`;
    } else if (e.event_type === 'refinance') {
        badge = 'Refinance';
        detail = JSON.stringify(e.payload);
    } else if (e.event_type === 'closure') {
        badge = 'Closure';
        detail = JSON.stringify(e.payload);
    }
    return {date: e.effective_date, badge, detail, badgeClass: 'glass-badge', eventId: e.id};
}

function transactionToTimelineItem(t) {
    return {
        date: t.transaction_date,
        badge: 'Extra Payment',
        detail: `${formatMoney(t.amount, t.currency || 'RON')}${t.description ? ' — ' + t.description : ''}`,
        badgeClass: 'glass-badge badge-income',
    };
}

function buildTimelineRow(item) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-bottom:1px solid var(--gb);';

    const left = document.createElement('div');
    const dateEl = document.createElement('div');
    dateEl.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
    dateEl.textContent = item.date;
    const detailEl = document.createElement('small');
    detailEl.style.cssText = 'color:var(--ts);font-variant-numeric:tabular-nums;';
    detailEl.textContent = item.detail;
    left.appendChild(dateEl);
    left.appendChild(detailEl);

    const right = document.createElement('div');
    right.style.cssText = 'display:flex;align-items:center;gap:8px;';

    const badge = document.createElement('span');
    badge.className = item.badgeClass;
    badge.style.fontVariantNumeric = 'tabular-nums';
    badge.textContent = item.badge;
    right.appendChild(badge);

    // Only real loan_events rows are deletable here — the "Extra Payment"
    // items on this same timeline are ordinary Transactions (see
    // transactionToTimelineItem, which sets no eventId), and go through the
    // existing transaction edit/delete flow instead, not this one.
    if (item.eventId != null) {
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'btn-glass btn-glass-secondary';
        delBtn.style.cssText = 'padding:4px 10px;font-size:0.75rem;';
        delBtn.textContent = 'Delete';
        delBtn.addEventListener('click', () => deleteEvent(item.eventId));
        right.appendChild(delBtn);
    }

    row.appendChild(left);
    row.appendChild(right);
    return row;
}

function deleteEvent(eventId) {
    Swal.fire({
        title: 'Delete Event?',
        text: 'Delete this loan event? This will change every projection that replays past this point. You\'ll have a few seconds to undo right after.',
        icon: 'warning', showCancelButton: true,
        confirmButtonColor: '#dc3545', confirmButtonText: 'Delete'
    }).then(result => {
        if (result.isConfirmed) {
            showUndoableEventDelete(eventId);
        }
    });
}

// ── Undo-able delete (Sprint 33) ────────────────────────────────────────────
// Not implemented via Swal's own timer+showCancelButton combo — vulnerable-
// version's custom Swal reimplementation (theme-switcher.js) doesn't support
// a timer alongside a cancel button, only secure-version's real SweetAlert2
// does, so relying on it would make this feature work on one version and not
// the other. This bar is fully self-built instead: nothing is actually
// deleted server-side until the undo window passes, so a mistaken delete
// costs nothing but a few seconds if caught in time.
const UNDO_DELETE_WINDOW_MS = 5000;
let undoDeleteTimer = null;

function showUndoableEventDelete(eventId) {
    const loanId = currentLoanId; // captured now, in case the user switches loans before the window elapses
    clearTimeout(undoDeleteTimer);
    const existingBar = document.getElementById('undoDeleteBar');
    if (existingBar) existingBar.remove();

    timelineItems = timelineItems.filter(item => item.eventId !== eventId);
    renderTimelinePage();

    const bar = document.createElement('div');
    bar.className = 'undo-delete-bar';
    bar.id = 'undoDeleteBar';
    bar.innerHTML = `
        <span>Event deleted.</span>
        <button type="button" class="btn-glass btn-glass-secondary" id="undoDeleteBtn">Undo</button>
    `;
    document.body.appendChild(bar);

    document.getElementById('undoDeleteBtn').addEventListener('click', () => {
        clearTimeout(undoDeleteTimer);
        bar.remove();
        if (loanId === currentLoanId) loadLoanData(currentLoanId);
    });

    undoDeleteTimer = setTimeout(() => {
        bar.remove();
        commitEventDelete(loanId, eventId);
    }, UNDO_DELETE_WINDOW_MS);
}

function commitEventDelete(loanId, eventId) {
    fetch(`/api/loans/${loanId}/events/${eventId}`, {method: 'DELETE'})
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                Swal.fire({icon: 'error', title: 'Error', text: data.message});
            }
            if (loanId === currentLoanId) loadLoanData(currentLoanId);
        })
        .catch(err => console.error(err));
}
