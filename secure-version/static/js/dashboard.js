// =============================================================================
// Aura Dashboard — Multi-Dashboard System (Secure Version)
// Sprint 14: Export/Import + Reports + Multi-Dashboard System
//
// Security properties (contrast with vulnerable-version/static/js/dashboard.js):
// - No user_id anywhere — every fetch relies on the session cookie; the
//   backend derives the caller from session['user_id']
// - Every string that can contain user-entered data (dashboard name,
//   custom_title, category/account names, transaction descriptions, savings
//   goal names) is rendered with textContent or set via createElement, never
//   interpolated into an innerHTML template — vulnerable's version renders
//   several of these via innerHTML (stored XSS, VULN-047/056 for custom_title
//   and dashboard name)
// - Every dynamically-created interactive element is wired with
//   addEventListener — no inline onclick="..." attributes, which the page's
//   CSP (script-src 'self', no 'unsafe-inline') silently drops anyway (see
//   categories.js for the full history of that bug)
// - Delete/remove confirmations use Swal's `text` option (rendered via
//   textContent by the custom glass Swal shim — see theme-switcher.js) rather
//   than `html`, which the shim doesn't even support
// =============================================================================

'use strict';

let dashboards = [];
let activeDash = null;
let chartInstances = {};

function css(prop) {
    return getComputedStyle(document.documentElement).getPropertyValue(prop).trim();
}

function applyChartDefaults() {
    Chart.defaults.color = css('--ts');
    Chart.defaults.borderColor = css('--gb');
    Chart.defaults.font.family = css('--fb').replace(/'/g, '');
}

const PALETTE = () => ({
    income: css('--up'),
    expense: css('--dn'),
    savings: '#4338ca',
    neutral: css('--gb'),
    glass: css('--gl'),
    series: ['#4338ca', '#0d9488', '#7c3aed', '#be185d', '#f59e0b', '#10b981', '#ef4444', '#3b82f6'],
});

function fmtCurrency(n) {
    return (n == null ? 0 : n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtMonth(ym) {
    if (!ym) return '';
    const [y, m] = ym.split('-');
    return new Date(y, m - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

const CHART_TYPE_OPTIONS = {
    income_expense_bar: ['bar', 'line'],
    expense_donut: ['donut', 'bar'],
    top_categories_trend: ['line', 'bar'],
    fixed_vs_variable: ['bar', 'line'],
    obligations_monthly: ['bar', 'line'],
    spending_trend: ['line', 'bar'],
};

const CHART_TYPE_LABELS = { bar: 'Bar Chart', line: 'Line Chart', donut: 'Donut Chart' };

const FILTER_SUPPORT = {
    income_expense_bar: { categories: true, accounts: true },
    expense_donut: { categories: true, accounts: false },
    recent_transactions: { categories: true, accounts: true },
    potential_to_save: { categories: false, accounts: true },
    category_heatmap: { categories: true, accounts: false },
    top_categories_trend: { categories: true, accounts: false },
    budget_vs_actual: { categories: true, accounts: false },
    spending_trend: { categories: true, accounts: true },
    loan_summary: { categories: false, accounts: false, loans: true },
    loan_trajectory: { categories: false, accounts: false, loans: true },
    debt_reduction_impact: { categories: false, accounts: false, loans: true },
    interest_overview: { categories: false, accounts: false, loans: true },
};

// Sprint 20: per-widget-type list of customizable chart series. `default`
// is a function (not a static value) so it always reflects the current
// theme even before any override has been saved. Widgets whose series are
// dynamic/per-category (expense_donut, category_heatmap, top_categories_trend)
// aren't listed here — those already have per-category colors via the
// Categories page, and a fixed slot list doesn't fit a variable series count.
const COLOR_SLOTS = {
    income_expense_bar: [
        { key: 'income', label: 'Income', default: () => PALETTE().income },
        { key: 'expense', label: 'Expenses', default: () => PALETTE().expense },
        { key: 'net', label: 'Net', default: () => PALETTE().savings },
    ],
    spending_trend: [
        { key: 'spend', label: 'Spend', default: () => PALETTE().expense },
        { key: 'moving_avg', label: '3-Month Average', default: () => '#f59e0b' },
    ],
    yoy_category_comparison: [
        { key: 'this_year', label: 'This Year', default: () => PALETTE().income },
        { key: 'last_year', label: 'Last Year', default: () => PALETTE().neutral },
    ],
    fixed_vs_variable: [
        { key: 'fixed', label: 'Fixed', default: () => PALETTE().expense },
        { key: 'variable', label: 'Variable', default: () => PALETTE().savings },
    ],
    obligations_monthly: [
        { key: 'obligations', label: 'Obligations', default: () => PALETTE().expense },
    ],
    budget_vs_actual: [
        { key: 'budget', label: 'Budget', default: () => PALETTE().income },
        { key: 'actual_ok', label: 'Actual (under budget)', default: () => PALETTE().savings },
        { key: 'actual_over', label: 'Actual (over budget)', default: () => PALETTE().expense },
    ],
    potential_to_save: [
        { key: 'net', label: 'Net', default: () => PALETTE().savings },
        { key: 'cumulative', label: 'Cumulative', default: () => PALETTE().income },
    ],
    loan_trajectory: [
        { key: 'actual', label: 'Actual Balance', default: () => PALETTE().income },
        { key: 'baseline', label: 'Baseline Balance', default: () => PALETTE().neutral },
    ],
};

function widgetColor(colors, key, fallbackFn) {
    return (colors && colors[key]) || fallbackFn();
}

const WIDGET_REGISTRY = {
    income_expense_bar: { render: renderIncomeExpenseBar, mini: d => `Net: RON ${fmtCurrency(d.total_income - d.total_expense)}` },
    expense_donut: { render: renderExpenseDonut, mini: d => `Total: RON ${fmtCurrency(d.total)}` },
    recent_transactions: { render: renderRecentTransactions, mini: () => 'Recent activity' },
    savings_goals_progress: { render: renderSavingsGoals, mini: d => `${d.goals.length} active goal${d.goals.length !== 1 ? 's' : ''}` },
    budget_vs_actual: { render: renderBudgetVsActual, mini: d => d.budget_name ? `Budget: ${d.budget_name}` : 'No active budget' },
    potential_to_save: { render: renderPotentialToSave, mini: d => `Net: RON ${fmtCurrency(d.current_net)}` },
    category_heatmap: { render: renderCategoryHeatmap, mini: d => `${d.categories ? d.categories.length : 0} categories` },
    top_categories_trend: { render: renderTopCategoriesTrend, mini: d => `Top ${d.series ? d.series.length : 0} categories` },
    fixed_vs_variable: { render: renderFixedVsVariable, mini: d => `${d.months ? d.months.length : 0} months` },
    obligations_monthly: { render: renderObligationsMonthly, mini: d => `YTD: RON ${fmtCurrency(d.ytd)}` },
    extra_repayments_ytd: { render: renderExtraRepaymentsYtd, mini: d => `Extra: RON ${fmtCurrency(d.extra_ytd)}` },
    debt_payments_metric: { render: renderDebtPaymentsMetric, mini: d => `Total: RON ${fmtCurrency(d.ytd)}` },
    spending_trend: {
        render: renderSpendingTrend,
        mini: d => (d.anomalies || []).length
            ? `${d.anomalies.length} anomal${d.anomalies.length === 1 ? 'y' : 'ies'} flagged`
            : 'No anomalies',
    },
    loan_summary: {
        render: renderLoanSummary,
        mini: d => d.no_loans ? 'No loans yet' : `RON ${fmtCurrency(d.current_balance)}`,
    },
    loans_overview: {
        render: renderLoansOverview,
        mini: d => d.no_loans || !d.loans ? 'No loans yet' : `${d.loans.length} loan${d.loans.length !== 1 ? 's' : ''} tracked`,
    },
    loan_trajectory: {
        render: renderLoanTrajectory,
        mini: d => d.no_loans ? 'No loans yet' : 'Baseline vs Actual',
    },
    debt_reduction_impact: {
        render: renderDebtReductionImpact,
        mini: d => d.no_loans || d.debt_reduction_vs_baseline == null ? 'No loans yet' : `RON ${fmtCurrency(d.debt_reduction_vs_baseline)} less than baseline`,
    },
    interest_overview: {
        render: renderInterestOverview,
        mini: d => d.no_loans || d.current_total_dobanda == null ? 'No bank snapshot yet' : `RON ${fmtCurrency(d.current_total_dobanda)} remaining`,
    },
    budget_accounts: {
        render: renderBudgetAccounts,
        mini: d => !d.accounts || d.accounts.length === 0 ? 'No accounts in budget' : `${d.accounts.length} account${d.accounts.length !== 1 ? 's' : ''}`,
    },
    yoy_category_comparison: {
        render: renderYoyComparison,
        mini: d => {
            const cats = d.categories || [];
            const ty = cats.reduce((s, c) => s + c.this_year, 0);
            const ly = cats.reduce((s, c) => s + c.last_year, 0);
            if (!ly) return 'No prior-year data';
            const pct = ((ty - ly) / ly * 100).toFixed(1);
            return `YoY: ${pct >= 0 ? '+' : ''}${pct}%`;
        },
    },
};

// ── Initialisation ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    applyChartDefaults();
    await applyStatCardOrder();
    await loadGlobalStats();
    await initDashboards();
    setupCustomizePanel();
    setupDashboardModal();
    setupWidgetSettingsModal();
    initSortables();
    initStatCardSortable();
});

/* DISABLED (Release 7 paused) — Abyss-only per user decision. This
   listener can never fire now (the event was only ever dispatched by the
   theme-switcher UI, itself disabled in theme-switcher.js), preserved for
   reference / future revival: docs/releases/release-07-plan.md

// ── Theme switch (Sprint 34) ────────────────────────────────────────────────
// Chart.js reads --ts/--gb once at chart-creation time via applyChartDefaults()
// (called above, on page load); switching themes afterward changes the CSS
// custom properties but doesn't retroactively repaint already-drawn canvases.
// Re-apply the (now current) defaults and rebuild every chart for the active
// dashboard so they pick up the new theme's colors immediately.
window.addEventListener('aura:theme-changed', () => {
    applyChartDefaults();
    if (activeDash) loadDashboard(activeDash.id);
});
*/

// ── Drag-and-drop reordering (Sprint 19) ─────────────────────────────────────
// Sortable.create() is called once per container here — it tracks the
// container's current children live, so it survives loadDashboard()/
// renderTabs() clearing and repopulating the DOM without needing to be
// re-initialized on every render.
function initSortables() {
    Sortable.create(document.getElementById('widgetGrid'), {
        handle: '.widget-drag-handle',
        animation: 150,
        onEnd: onWidgetReorder,
    });
    Sortable.create(document.getElementById('dashboardTabs'), {
        animation: 150,
        onEnd: onDashboardReorder,
    });
}

function onWidgetReorder() {
    if (!activeDash) return;
    const grid = document.getElementById('widgetGrid');
    const order = Array.from(grid.children)
        .map(el => parseInt(el.dataset.id, 10))
        .filter(id => !isNaN(id));
    if (!order.length) return;

    fetch(`/api/dashboards/${activeDash.id}/widgets/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order })
    })
        .then(r => r.json())
        .then(j => {
            if (!j.success) {
                Swal.fire({ icon: 'error', title: 'Could not save widget order', text: j.message });
                loadDashboard(activeDash.id);
            }
        })
        .catch(() => loadDashboard(activeDash.id));
}

// ── Stat card reordering (Sprint 53, UI-02) ──────────────────────────────────
// Order persists server-side per user (first server-persisted UI preference
// in either version — theme/sidebar-collapsed are localStorage-only).
async function applyStatCardOrder() {
    try {
        const r = await fetch('/api/users/stat-card-order');
        const j = await r.json();
        if (!j.success || !j.order) return;
        const grid = document.getElementById('statCards');
        const byKey = new Map(Array.from(grid.children).map(el => [el.dataset.cardKey, el]));
        j.order.forEach(key => {
            const el = byKey.get(key);
            if (el) grid.appendChild(el);
        });
    } catch (e) {
        console.error('Stat card order error:', e);
    }
}

function initStatCardSortable() {
    Sortable.create(document.getElementById('statCards'), {
        handle: '.stat-card-drag-handle',
        animation: 150,
        onEnd: onStatCardReorder,
    });
}

function onStatCardReorder() {
    const grid = document.getElementById('statCards');
    const order = Array.from(grid.children).map(el => el.dataset.cardKey).filter(Boolean);
    if (!order.length) return;

    fetch('/api/users/stat-card-order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order})
    })
        .then(r => r.json())
        .then(j => {
            if (!j.success) {
                Swal.fire({icon: 'error', title: 'Could not save card order', text: j.message});
            }
        })
        .catch(() => {});
}

function onDashboardReorder() {
    const container = document.getElementById('dashboardTabs');
    const order = Array.from(container.children)
        .map(el => parseInt(el.dataset.id, 10))
        .filter(id => !isNaN(id));
    if (!order.length) return;

    fetch('/api/dashboards/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order })
    })
        .then(r => r.json())
        .then(j => {
            if (j.success) {
                const byId = new Map(dashboards.map(d => [d.id, d]));
                dashboards = order.map(id => byId.get(id)).filter(Boolean);
            } else {
                Swal.fire({ icon: 'error', title: 'Could not save dashboard order', text: j.message });
                renderTabs();
            }
        })
        .catch(() => renderTabs());
}

// ── Global stat cards ────────────────────────────────────────────────────────
async function loadGlobalStats() {
    try {
        const r = await fetch('/api/transactions/summary');
        const j = await r.json();
        if (!j.success) return;
        const s = j.summary;
        setAmountText('statTotalIncome', s.total_income, true);
        setAmountText('statTotalExpenses', s.total_expenses, false);
        const bal = s.balance;
        setAmountText('statBalance', bal, bal >= 0);
    } catch (e) {
        console.error('Stats error:', e);
    }

    try {
        const r = await fetch('/api/accounts/summary');
        const j = await r.json();
        if (!j.success) return;
        setAmountText('statBudgetBalance', j.budget_balance, j.budget_balance >= 0);
    } catch (e) {
        console.error('Budget balance error:', e);
    }
}

function setAmountText(elId, amount, positive) {
    const el = document.getElementById(elId);
    el.innerHTML = '';
    const span = document.createElement('span');
    span.className = positive ? 'amount-positive' : 'amount-negative';
    span.textContent = `RON ${fmtCurrency(amount)}`;
    el.appendChild(span);
}

/* DISABLED (Release 7 paused) — Abyss-only per user decision. Hero card
   (Sprint 36/37, Wisteria+Tempest only) preserved below for reference /
   future revival: docs/releases/release-07-plan.md

// ── Hero card (Sprint 36 Wisteria, made dashboard-aware Sprint 37 TE-005..008) ──
// The hero card replaces the classic stat cards under Wisteria/Tempest. Which
// stats it shows depends on the active dashboard *tab* (dashboards are tabs
// within this one page, not separate templates), so this is called from
// loadDashboard() — already re-run on initial load, every tab switch, and
// every theme change — rather than only once at page load like loadGlobalStats().
const HERO_RING_CIRCUMFERENCE = 188.4; // 2 * PI * r(30), matches the SVG circle's stroke-dasharray

function setHeroRing(pct) {
    const clamped = Math.max(0, Math.min(100, pct || 0));
    document.getElementById('heroRingFill').style.strokeDashoffset = HERO_RING_CIRCUMFERENCE * (1 - clamped / 100);
    document.getElementById('heroRingVal').textContent = Math.round(clamped) + '%';
}

function setHeroPill(valueId, value, colorClass) {
    const el = document.getElementById(valueId);
    el.textContent = value;
    el.classList.remove('income', 'expense');
    if (colorClass) el.classList.add(colorClass);
}

async function loadHeroCard() {
    if (!document.getElementById('heroIncome')) return;
    const dashName = activeDash ? activeDash.name : 'Monthly Overview';
    try {
        if (dashName === 'Savings & Goals') {
            await loadHeroSavingsGoals();
        } else if (dashName === 'Spending Analysis') {
            await loadHeroSpendingAnalysis();
        } else if (dashName === 'Loan & Obligations') {
            await loadHeroLoanObligations();
        } else {
            await loadHeroMonthlyOverview();
        }
    } catch (e) {
        console.error('Hero card error:', e);
    }
}

async function loadHeroMonthlyOverview() {
    const r = await fetch('/api/transactions/summary');
    const j = await r.json();
    if (!j.success) return;
    const s = j.summary;
    const bal = s.balance;

    document.getElementById('heroLabel').textContent = 'Current Balance';
    setAmountText('heroBalance', bal, bal >= 0);
    document.getElementById('heroRingLbl').textContent = 'Saved';
    document.getElementById('heroStat1Label').textContent = 'Income';
    document.getElementById('heroStat2Label').textContent = 'Expenses';
    setHeroPill('heroIncome', 'RON ' + fmtCurrency(s.total_income), 'income');
    setHeroPill('heroExpense', 'RON ' + fmtCurrency(s.total_expenses), 'expense');

    setHeroRing(s.total_income > 0 ? (bal / s.total_income) * 100 : 0);
}

async function loadHeroSavingsGoals() {
    const r = await fetch('/api/reports-data/savings-goals');
    const j = await r.json();
    const goals = j.success ? (j.data.goals || []) : [];

    const totalCurrent   = goals.reduce((sum, g) => sum + g.current_amount, 0);
    const totalTarget    = goals.reduce((sum, g) => sum + g.target_amount, 0);
    const totalRemaining = goals.reduce((sum, g) => sum + g.remaining, 0);

    document.getElementById('heroLabel').textContent = 'Total Saved';
    setAmountText('heroBalance', totalCurrent, true);
    document.getElementById('heroRingLbl').textContent = 'Funded';
    document.getElementById('heroStat1Label').textContent = 'Active Goals';
    document.getElementById('heroStat2Label').textContent = 'Remaining';
    setHeroPill('heroIncome', String(goals.length));
    setHeroPill('heroExpense', 'RON ' + fmtCurrency(totalRemaining));

    setHeroRing(totalTarget > 0 ? (totalCurrent / totalTarget) * 100 : 0);
}

async function loadHeroSpendingAnalysis() {
    const r = await fetch('/api/reports-data/expense-distribution?period=1M');
    const j = await r.json();
    const categories = j.success ? (j.data.categories || []) : [];
    const grandTotal  = j.success ? j.data.total : 0;
    const top = categories[0] || null;

    document.getElementById('heroLabel').textContent = 'Expenses (This Month)';
    setAmountText('heroBalance', grandTotal, false);
    document.getElementById('heroRingLbl').textContent = 'Top Cat';
    document.getElementById('heroStat1Label').textContent = 'Top Category';
    document.getElementById('heroStat2Label').textContent = 'Category Total';
    setHeroPill('heroIncome', top ? top.name : '—');
    setHeroPill('heroExpense', top ? 'RON ' + fmtCurrency(top.total) : '—', 'expense');

    setHeroRing(top ? top.pct : 0);
}

async function loadHeroLoanObligations() {
    const loansRes = await fetch('/api/loans/list');
    const loansJson = await loansRes.json();
    const loans = loansJson.success ? loansJson.loans : [];

    document.getElementById('heroLabel').textContent = 'Remaining Balance';
    document.getElementById('heroRingLbl').textContent = 'Paid';
    document.getElementById('heroStat1Label').textContent = 'Years Left';
    document.getElementById('heroStat2Label').textContent = 'Interest Saved';

    if (loans.length === 0) {
        document.getElementById('heroBalance').textContent = 'No loans tracked';
        setHeroPill('heroIncome', '—');
        setHeroPill('heroExpense', '—');
        setHeroRing(0);
        return;
    }

    const loan = loans[0];
    const statusRes = await fetch(`/api/loans/${loan.id}/status`);
    const status = await statusRes.json();
    if (!status.success) return;

    setAmountText('heroBalance', status.current_balance, false);
    setHeroPill('heroIncome', status.years_remaining != null ? status.years_remaining : '—');
    setHeroPill('heroExpense', status.interest_saved != null ? 'RON ' + fmtCurrency(status.interest_saved) : '—', 'income');

    setHeroRing(loan.principal > 0 ? ((loan.principal - status.current_balance) / loan.principal) * 100 : 0);
}
*/

// ── Dashboard tabs ───────────────────────────────────────────────────────────
async function initDashboards() {
    try {
        const r = await fetch('/api/dashboards/list');
        const j = await r.json();
        if (!j.success) return;
        dashboards = j.dashboards;
        renderTabs();
        activeDash = dashboards.find(d => d.is_active) || dashboards[0];
        if (activeDash) await loadDashboard(activeDash.id);
    } catch (e) {
        console.error('Dashboard init error:', e);
    }
}

function renderTabs() {
    const container = document.getElementById('dashboardTabs');
    container.innerHTML = '';
    dashboards.forEach(d => {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:inline-flex;align-items:center;gap:2px;';
        wrap.dataset.id = d.id;

        const btn = document.createElement('button');
        btn.className = 'dashboard-tab' + (d.is_active ? ' active' : '');
        btn.dataset.id = d.id;
        btn.textContent = d.name;
        btn.addEventListener('click', () => switchDashboard(d.id));
        wrap.appendChild(btn);

        if (d.is_active) {
            const editBtn = document.createElement('button');
            editBtn.className = 'tab-ctrl-btn';
            editBtn.title = 'Rename dashboard';
            editBtn.textContent = '✏';
            editBtn.addEventListener('click', e => { e.stopPropagation(); openEditDashboardModal(d.id); });

            const delBtn = document.createElement('button');
            delBtn.className = 'tab-ctrl-btn danger';
            delBtn.title = 'Delete dashboard';
            delBtn.textContent = '🗑';
            delBtn.addEventListener('click', e => { e.stopPropagation(); confirmDeleteDashboard(d.id); });

            wrap.appendChild(editBtn);
            wrap.appendChild(delBtn);
        }

        container.appendChild(wrap);
    });
}

async function switchDashboard(dashboardId) {
    if (activeDash && activeDash.id === dashboardId) return;

    dashboards.forEach(d => d.is_active = (d.id === dashboardId));
    activeDash = dashboards.find(d => d.id === dashboardId);
    renderTabs();

    fetch(`/api/dashboards/${dashboardId}/activate`, { method: 'POST' }).catch(() => {});

    await loadDashboard(dashboardId);
}

// ── Widget grid ──────────────────────────────────────────────────────────────
async function loadDashboard(dashboardId) {
    // loadHeroCard() was called here (Release 7); disabled above along
    // with the hero-card feature it drove. See docs/releases/release-07-plan.md.

    const grid = document.getElementById('widgetGrid');
    grid.innerHTML = '';
    grid.appendChild(loadingBlock('Loading widgets…'));

    Object.values(chartInstances).forEach(c => c && c.destroy && c.destroy());
    chartInstances = {};

    try {
        const r = await fetch(`/api/dashboards/${dashboardId}/widgets`);
        const j = await r.json();
        if (!j.success) return;

        const widgets = j.widgets;
        grid.innerHTML = '';

        if (widgets.length === 0) {
            // BUG-07 fix (2026-09-02): this early `return` used to skip
            // refreshCustomizePanel(widgets) entirely whenever a dashboard
            // had zero widgets (always true right after creating a new
            // one) — the Customize panel kept showing whichever dashboard
            // was loaded *before* this one, including its checkboxes as
            // pre-selected, since nothing ever told it to reset. Marked
            // with an id so addWidgetToDashboard() can reliably remove
            // this message once a widget is actually added (see there).
            const empty = emptyBlock('No widgets configured for this dashboard.');
            empty.id = 'widgetGridEmptyState';
            grid.appendChild(empty);
            refreshCustomizePanel(widgets);
            return;
        }

        for (const w of widgets) {
            const card = buildWidgetShell(w);
            grid.appendChild(card);
            if (w.is_enabled) loadWidgetData(w);
        }

        refreshCustomizePanel(widgets);
    } catch (e) {
        console.error('Load dashboard error:', e);
    }
}

function loadingBlock(msg) {
    const div = document.createElement('div');
    div.style.cssText = 'grid-column:1/-1;text-align:center;padding:60px 0;';
    const spinner = document.createElement('div');
    spinner.className = 'glass-spinner';
    spinner.style.margin = '0 auto 12px';
    const span = document.createElement('span');
    span.style.cssText = 'color:var(--th);font-size:0.875rem;';
    span.textContent = msg;
    div.appendChild(spinner);
    div.appendChild(span);
    return div;
}

function emptyBlock(msg) {
    const div = document.createElement('div');
    div.style.cssText = 'grid-column:1/-1;text-align:center;padding:60px 0;color:var(--th);';
    div.textContent = msg;
    return div;
}

// ── Widget shell ─────────────────────────────────────────────────────────────
function buildWidgetShell(w) {
    const card = document.createElement('div');
    card.className = 'glass-card no-hover widget-card';
    card.id = `widget-${w.id}`;
    card.dataset.id = w.id;
    card.dataset.type = w.widget_type;
    if (!w.is_enabled) card.style.display = 'none';
    if (w.is_minimized) card.classList.add('is-minimized');

    const displayTitle = w.custom_title || w.title;

    const header = document.createElement('div');
    header.className = 'widget-header';

    const titleWrap = document.createElement('div');
    titleWrap.className = 'widget-title-wrap';

    const dragHandle = document.createElement('span');
    dragHandle.className = 'widget-drag-handle';
    dragHandle.title = 'Drag to reorder';
    dragHandle.textContent = '⠿';
    titleWrap.appendChild(dragHandle);

    const titleSpan = document.createElement('span');
    titleSpan.className = 'widget-title';
    titleSpan.textContent = displayTitle;
    titleWrap.appendChild(titleSpan);

    header.appendChild(titleWrap);

    const controls = document.createElement('div');
    controls.className = 'widget-controls';

    const periodBar = document.createElement('div');
    periodBar.className = 'period-bar';
    periodBar.id = `periods-${w.id}`;
    ['1M', '3M', '6M', '1Y', 'ALL'].forEach(p => {
        const btn = document.createElement('button');
        btn.className = 'period-btn' + (w.time_period === p ? ' active' : '');
        btn.dataset.period = p;
        btn.textContent = p;
        btn.addEventListener('click', () => changePeriod(w.id, p));
        periodBar.appendChild(btn);
    });
    controls.appendChild(periodBar);

    const minBtn = document.createElement('button');
    minBtn.className = 'widget-minimize-btn';
    minBtn.title = 'Minimize / Expand';
    minBtn.appendChild(minimizeIconSvg(w.id, w.is_minimized));
    minBtn.addEventListener('click', () => toggleMinimize(w.id));
    controls.appendChild(minBtn);

    const settingsBtn = document.createElement('button');
    settingsBtn.className = 'widget-settings-btn';
    settingsBtn.title = 'Widget settings';
    settingsBtn.textContent = '⚙';
    settingsBtn.addEventListener('click', () => openWidgetSettingsModal(w.id));
    controls.appendChild(settingsBtn);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'widget-remove-btn';
    removeBtn.title = 'Remove widget permanently';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => confirmRemoveWidget(w.id, displayTitle));
    controls.appendChild(removeBtn);

    header.appendChild(controls);
    card.appendChild(header);

    const body = document.createElement('div');
    body.className = 'widget-body';
    body.id = `wbody-${w.id}`;
    if (w.is_minimized) body.style.display = 'none';
    const spinnerWrap = document.createElement('div');
    spinnerWrap.style.cssText = 'text-align:center;padding:32px 0;';
    const spinner = document.createElement('div');
    spinner.className = 'glass-spinner';
    spinner.style.margin = '0 auto 10px';
    const loadingSpan = document.createElement('span');
    loadingSpan.style.cssText = 'font-size:0.8rem;color:var(--th);';
    loadingSpan.textContent = 'Loading…';
    spinnerWrap.appendChild(spinner);
    spinnerWrap.appendChild(loadingSpan);
    body.appendChild(spinnerWrap);
    card.appendChild(body);

    const mini = document.createElement('div');
    mini.className = 'widget-mini';
    mini.id = `wmini-${w.id}`;
    if (!w.is_minimized) mini.style.display = 'none';
    const metric = document.createElement('span');
    metric.className = 'widget-mini-metric';
    metric.id = `wmetric-${w.id}`;
    metric.textContent = '—';
    mini.appendChild(metric);
    card.appendChild(mini);

    return card;
}

function minimizeIconSvg(widgetId, isMinimized) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('id', `minIcon-${widgetId}`);
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('viewBox', '0 0 16 16');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    poly.setAttribute('points', isMinimized ? '3,10 8,5 13,10' : '3,6 8,11 13,6');
    svg.appendChild(poly);
    return svg;
}

// Shared by every loan-scoped widget (loan_summary, loan_trajectory) —
// resolves filter_config.loan_id against the caller's own loan list, falling
// back to the first loan if unset or if the configured loan no longer exists
// (e.g. deleted since the widget was configured).
function resolveTargetLoan(loans, filterConfig) {
    const configuredId = filterConfig?.loan_id;
    return (configuredId != null && loans.find(l => l.id === configuredId)) || loans[0];
}

// ── Widget data loading ──────────────────────────────────────────────────────
async function loadWidgetData(w) {
    const body = document.getElementById(`wbody-${w.id}`);
    if (!body) return;

    const reg = WIDGET_REGISTRY[w.widget_type];
    if (!reg) {
        body.innerHTML = '';
        body.appendChild(errorBlock(`Widget type "${w.widget_type}" is not supported yet.`));
        return;
    }

    try {
        const filterConfig = w.filter_config || {};
        const categoryIds = (filterConfig.category_ids || []).join(',');
        const accountIds = (filterConfig.account_ids || []).join(',');
        const effectiveType = w.chart_type || null;

        let data;
        if (w.widget_type === 'recent_transactions') {
            let txUrl = '/api/transactions/list?limit=10';
            if (w.time_period && w.time_period !== 'ALL') {
                const daysMap = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365 };
                const cutoff = new Date();
                cutoff.setDate(cutoff.getDate() - (daysMap[w.time_period] || 30));
                txUrl += `&date_from=${cutoff.toISOString().split('T')[0]}`;
            }
            if (categoryIds) txUrl += `&category_id=${encodeURIComponent(categoryIds)}`;
            if (accountIds) txUrl += `&account_id=${encodeURIComponent(accountIds)}`;
            const r = await fetch(txUrl);
            const j = await r.json();
            data = j.success ? j.transactions : [];
        } else if (w.widget_type === 'loan_summary') {
            const loansRes = await fetch('/api/loans/list');
            const loansJson = await loansRes.json();
            if (!loansJson.success || loansJson.loans.length === 0) {
                data = { no_loans: true };
            } else {
                const targetLoan = resolveTargetLoan(loansJson.loans, w.filter_config);
                // /project is fetched alongside /status purely for the
                // reconciliation-drift indicator — principal/start_date come
                // from targetLoan itself (already returned by /list), so no
                // third fetch is needed for those.
                const [statusRes, projectRes] = await Promise.all([
                    fetch(`/api/loans/${targetLoan.id}/status`),
                    fetch(`/api/loans/${targetLoan.id}/project`),
                ]);
                const statusJson = await statusRes.json();
                const projectJson = await projectRes.json();
                data = statusJson.success ? {
                    ...statusJson,
                    principal: targetLoan.principal,
                    start_date: targetLoan.start_date,
                    reconciliation: projectJson.success ? projectJson.reconciliation : [],
                } : null;
            }
        } else if (w.widget_type === 'loan_trajectory') {
            const loansRes = await fetch('/api/loans/list');
            const loansJson = await loansRes.json();
            if (!loansJson.success || loansJson.loans.length === 0) {
                data = { no_loans: true };
            } else {
                const targetLoan = resolveTargetLoan(loansJson.loans, w.filter_config);
                const projectRes = await fetch(`/api/loans/${targetLoan.id}/project`);
                const projectJson = await projectRes.json();
                data = projectJson.success ? {
                    loan_name: targetLoan.name,
                    actual_periods: projectJson.actual.periods,
                    baseline_periods: projectJson.baseline.periods,
                } : null;
            }
        } else if (w.widget_type === 'debt_reduction_impact') {
            const loansRes = await fetch('/api/loans/list');
            const loansJson = await loansRes.json();
            if (!loansJson.success || loansJson.loans.length === 0) {
                data = { no_loans: true };
            } else {
                const targetLoan = resolveTargetLoan(loansJson.loans, w.filter_config);
                const statusRes = await fetch(`/api/loans/${targetLoan.id}/status`);
                const statusJson = await statusRes.json();
                data = statusJson.success ? statusJson : null;
            }
        } else if (w.widget_type === 'interest_overview') {
            const loansRes = await fetch('/api/loans/list');
            const loansJson = await loansRes.json();
            if (!loansJson.success || loansJson.loans.length === 0) {
                data = { no_loans: true };
            } else {
                const targetLoan = resolveTargetLoan(loansJson.loans, w.filter_config);
                const statusRes = await fetch(`/api/loans/${targetLoan.id}/status`);
                const statusJson = await statusRes.json();
                data = statusJson.success ? statusJson : null;
            }
        } else if (w.widget_type === 'loans_overview') {
            const loansRes = await fetch('/api/loans/list');
            const loansJson = await loansRes.json();
            if (!loansJson.success || loansJson.loans.length === 0) {
                data = { no_loans: true };
            } else {
                const statuses = await Promise.all(
                    loansJson.loans.map(l => fetch(`/api/loans/${l.id}/status`).then(r => r.json()))
                );
                data = { loans: statuses.filter(s => s.success) };
            }
        } else if (w.widget_type === 'budget_accounts') {
            const r = await fetch('/api/accounts/list');
            const j = await r.json();
            const included = j.success ? j.accounts.filter(a => a.include_in_budget) : [];
            data = { accounts: included };
        } else {
            let url = `${w.endpoint}?period=${encodeURIComponent(w.time_period)}`;
            if (categoryIds) url += `&category_ids=${encodeURIComponent(categoryIds)}`;
            if (accountIds) url += `&account_ids=${encodeURIComponent(accountIds)}`;
            const r = await fetch(url);
            const j = await r.json();
            data = j.success ? j.data : null;
        }

        if (data == null) {
            body.innerHTML = '';
            body.appendChild(errorBlock('Failed to load data.'));
            return;
        }

        const metricEl = document.getElementById(`wmetric-${w.id}`);
        if (metricEl) {
            try { metricEl.textContent = reg.mini(data); } catch (_) {}
        }

        reg.render(w.id, data, effectiveType, w.chart_colors);
    } catch (e) {
        console.error(`Widget ${w.id} load error:`, e);
        if (body) {
            body.innerHTML = '';
            body.appendChild(errorBlock('Error loading widget data.'));
        }
    }
}

function errorBlock(msg) {
    const p = document.createElement('p');
    p.style.cssText = 'color:var(--dn);text-align:center;padding:20px 0;font-size:0.85rem;';
    p.textContent = msg;
    return p;
}

function emptyMsg(msg) {
    const p = document.createElement('p');
    p.style.cssText = 'text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;';
    p.textContent = msg;
    return p;
}

// ── Period change ────────────────────────────────────────────────────────────
async function changePeriod(widgetId, period) {
    document.querySelectorAll(`#periods-${widgetId} .period-btn`).forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });

    await fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_period: period })
    });

    const w = await getWidgetState(widgetId, period);
    if (w) loadWidgetData(w);
}

async function getWidgetState(widgetId, overridePeriod) {
    const card = document.getElementById(`widget-${widgetId}`);
    if (!card) return null;
    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const j = await r.json();
    if (!j.success) return null;
    const w = j.widgets.find(x => x.id === widgetId);
    if (w && overridePeriod) w.time_period = overridePeriod;
    return w || null;
}

// ── Minimize / maximize ──────────────────────────────────────────────────────
async function toggleMinimize(widgetId) {
    const body = document.getElementById(`wbody-${widgetId}`);
    const mini = document.getElementById(`wmini-${widgetId}`);
    const iconSvg = document.getElementById(`minIcon-${widgetId}`);
    if (!body || !mini) return;

    const isNowMin = body.style.display !== 'none';
    const card = document.getElementById(`widget-${widgetId}`);

    body.style.display = isNowMin ? 'none' : '';
    mini.style.display = isNowMin ? '' : 'none';
    if (card) card.classList.toggle('is-minimized', isNowMin);

    if (iconSvg) {
        const poly = iconSvg.querySelector('polyline');
        if (poly) poly.setAttribute('points', isNowMin ? '3,10 8,5 13,10' : '3,6 8,11 13,6');
    }

    fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_minimized: isNowMin })
    }).catch(() => {});
}

// ── Customize panel ──────────────────────────────────────────────────────────
function setupCustomizePanel() {
    document.getElementById('customizeBtn').addEventListener('click', () => {
        const panel = document.getElementById('customizePanel');
        panel.style.display = panel.style.display === 'none' ? '' : 'none';
    });
    document.getElementById('closePanelBtn').addEventListener('click', () => {
        document.getElementById('customizePanel').style.display = 'none';
    });
}

const ALL_WIDGET_META = [
    { type: 'income_expense_bar', title: 'Income vs Expenses', desc: 'Monthly income & expense grouped bar chart' },
    { type: 'expense_donut', title: 'Expense Distribution', desc: 'Spending breakdown by category — donut chart' },
    { type: 'recent_transactions', title: 'Recent Transactions', desc: 'Latest 10 transactions — table view' },
    { type: 'savings_goals_progress', title: 'Savings Goals Progress', desc: 'Progress bars for each active savings goal' },
    { type: 'budget_vs_actual', title: 'Budget vs Actual', desc: 'Budget limit vs actual spend per category' },
    { type: 'potential_to_save', title: 'Potential to Save', desc: 'Income minus expenses — metric + trend line' },
    { type: 'category_heatmap', title: 'Category Heatmap', desc: 'Month × category spending intensity grid' },
    { type: 'top_categories_trend', title: 'Top Categories Trend', desc: 'Top 5 spending categories over time' },
    { type: 'fixed_vs_variable', title: 'Fixed vs Variable', desc: 'Fixed vs variable cost split — stacked bar' },
    { type: 'obligations_monthly', title: 'Obligations Monthly', desc: 'Financial obligation payments per month' },
    { type: 'extra_repayments_ytd', title: 'Extra Repayments YTD', desc: 'Extra debt repayments year-to-date' },
    { type: 'debt_payments_metric', title: 'Total Debt Payments', desc: 'Total debt payment metric card' },
    { type: 'spending_trend', title: 'Spending Trend & Anomalies', desc: 'Monthly spend with a moving-average line, plus categories flagged as unusually high' },
    { type: 'yoy_category_comparison', title: 'Year-over-Year Comparison', desc: 'This year vs last year totals, per category' },
    { type: 'loan_summary', title: 'Loan Summary', desc: 'Current balance, installment, payoff date, and savings so far for one loan — pick which one in the widget\'s settings' },
    { type: 'loans_overview', title: 'All Loans Overview', desc: 'Balance, payoff date, and savings so far for every loan you\'re tracking, at a glance' },
    { type: 'loan_trajectory', title: 'Payoff Trajectory', desc: 'Actual vs Baseline balance over the life of one loan — pick which one in the widget\'s settings' },
    { type: 'debt_reduction_impact', title: 'Debt Reduction Impact', desc: 'How much lower your balance is today vs the original plan, plus total extra principal paid, for one loan' },
    { type: 'interest_overview', title: 'Interest Overview', desc: 'Bank-confirmed remaining interest ("Dobanda"), current rate, and estimated interest saved for one loan' },
    { type: 'budget_accounts', title: 'Accounts Included in Budget', desc: 'Balance of every account currently counted toward your budget total' },
];

function refreshCustomizePanel(widgets) {
    const list = document.getElementById('customizeWidgetList');
    list.innerHTML = '';

    const sec1 = document.createElement('div');
    sec1.className = 'customize-section-title';
    sec1.textContent = 'Widgets on this dashboard';
    list.appendChild(sec1);

    if (widgets.length === 0) {
        const empty = document.createElement('p');
        empty.style.cssText = 'font-size:0.82rem;color:var(--th);margin-bottom:4px;';
        empty.textContent = 'No widgets yet. Use "Add widget" below to get started.';
        list.appendChild(empty);
    } else {
        const toggles = document.createElement('div');
        toggles.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px;margin-bottom:4px;';
        widgets.forEach(w => {
            const pill = document.createElement('label');
            pill.className = 'customize-pill';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = w.is_enabled;
            cb.addEventListener('change', () => toggleWidgetEnabled(w.id, cb.checked));
            const span = document.createElement('span');
            span.textContent = w.custom_title || w.title;
            pill.appendChild(cb);
            pill.appendChild(span);
            toggles.appendChild(pill);
        });
        list.appendChild(toggles);
    }

    const sec2 = document.createElement('div');
    sec2.className = 'customize-section-title';
    sec2.textContent = 'Add widget';
    list.appendChild(sec2);

    const existingTypes = new Set(widgets.map(w => w.widget_type));
    const addGrid = document.createElement('div');
    addGrid.className = 'add-widget-list';

    ALL_WIDGET_META.forEach(meta => {
        const added = existingTypes.has(meta.type);
        const card = document.createElement('div');
        card.className = 'add-widget-card' + (added ? ' already-added' : '');

        const info = document.createElement('div');
        info.style.minWidth = '0';
        const name = document.createElement('div');
        name.className = 'add-widget-card-name';
        name.textContent = meta.title;
        const desc = document.createElement('div');
        desc.style.cssText = 'font-size:0.74rem;color:var(--th);margin-top:2px;';
        desc.textContent = meta.desc;
        info.appendChild(name);
        info.appendChild(desc);

        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary';
        btn.style.cssText = 'font-size:0.74rem;padding:4px 10px;white-space:nowrap;';
        btn.disabled = added;
        btn.textContent = added ? 'Added' : 'Add';
        btn.addEventListener('click', () => addWidgetToDashboard(meta.type));

        card.appendChild(info);
        card.appendChild(btn);
        addGrid.appendChild(card);
    });
    list.appendChild(addGrid);
}

async function toggleWidgetEnabled(widgetId, enabled) {
    const card = document.getElementById(`widget-${widgetId}`);
    if (card) card.style.display = enabled ? '' : 'none';

    fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_enabled: enabled })
    }).catch(() => {});
}

// =============================================================================
// Widget renderers — all chart labels/data go through Chart.js, which draws
// them on <canvas> rather than via the DOM, so category/account names and
// other user-controlled strings passed to Chart.js configs are not an XSS
// vector. Only renderRecentTransactions, renderSavingsGoals, and
// renderCategoryHeatmap put user-controlled strings into the DOM directly —
// those three use createElement/textContent exclusively.
// =============================================================================

function renderIncomeExpenseBar(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = `<canvas id="chart-${wid}" height="120"></canvas>`;
    const p = PALETTE();
    const cIncome = widgetColor(colors, 'income', () => p.income);
    const cExpense = widgetColor(colors, 'expense', () => p.expense);
    const cNet = widgetColor(colors, 'net', () => p.savings);
    const labels = (data.months || []).map(fmtMonth);
    if (chartInstances[wid]) chartInstances[wid].destroy();

    if (chartType === 'line') {
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Income', data: data.income || [], borderColor: cIncome, backgroundColor: cIncome + '22', tension: 0.4, fill: false, borderWidth: 2 },
                    { label: 'Expenses', data: data.expense || [], borderColor: cExpense, backgroundColor: cExpense + '22', tension: 0.4, fill: false, borderWidth: 2 },
                    { label: 'Net', data: data.net || [], borderColor: cNet, backgroundColor: cNet + '22', tension: 0.4, fill: false, borderWidth: 2, borderDash: [4, 4] },
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    } else {
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Income', data: data.income || [], backgroundColor: cIncome + '66', borderColor: cIncome, borderWidth: 1.5, borderRadius: 5 },
                    { label: 'Expenses', data: data.expense || [], backgroundColor: cExpense + '66', borderColor: cExpense, borderWidth: 1.5, borderRadius: 5 },
                    { label: 'Net', data: data.net || [], backgroundColor: cNet + '66', borderColor: cNet, borderWidth: 1.5, borderRadius: 5, type: 'line', tension: 0.4, fill: false },
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    }
}

function renderExpenseDonut(wid, data, chartType) {
    const body = document.getElementById(`wbody-${wid}`);
    if (chartInstances[wid]) chartInstances[wid].destroy();
    const cats = data.categories || [];
    const p = PALETTE();

    if (chartType === 'bar') {
        body.innerHTML = `<canvas id="chart-${wid}" height="140"></canvas>`;
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'bar',
            data: {
                labels: cats.map(c => c.name),
                datasets: [{ label: 'Spend', data: cats.map(c => c.total), backgroundColor: cats.map(c => c.color), borderRadius: 5, borderWidth: 0 }]
            },
            options: { ...chartOpts({ prefix: 'RON ' }), indexAxis: 'y' }
        });
    } else {
        body.innerHTML = `<div style="display:flex;justify-content:center;"><canvas id="chart-${wid}" style="max-height:260px;"></canvas></div>`;
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: cats.map(c => c.name),
                datasets: [{ data: cats.map(c => c.total), backgroundColor: cats.map(c => c.color), borderColor: p.glass, borderWidth: 2 }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 14, font: { size: 11 } } },
                    tooltip: { callbacks: { label: ctx => `${ctx.label}: RON ${fmtCurrency(ctx.parsed)} (${cats[ctx.dataIndex]?.pct ?? 0}%)` } }
                }
            }
        });
    }
}

function renderRecentTransactions(wid, transactions) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';
    if (!transactions || transactions.length === 0) {
        body.appendChild(emptyMsg('No recent transactions.'));
        return;
    }

    const wrap = document.createElement('div');
    wrap.style.overflowX = 'auto';
    const table = document.createElement('table');
    table.className = 'glass-table';
    const thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>Date</th><th>Type</th><th>Category</th><th>Description</th><th style="text-align:right;">Amount</th></tr>';
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    transactions.slice(0, 10).forEach(t => {
        const inc = t.type === 'income';
        const tr = document.createElement('tr');

        const dateTd = document.createElement('td');
        dateTd.style.cssText = 'font-size:0.8rem;color:var(--ts);';
        dateTd.textContent = t.transaction_date;

        const typeTd = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = inc ? 'glass-badge badge-income' : 'glass-badge badge-expense';
        badge.textContent = inc ? 'Income' : 'Expense';
        typeTd.appendChild(badge);

        const catTd = document.createElement('td');
        catTd.style.fontSize = '0.85rem';
        catTd.textContent = t.category_name || '—';

        const descTd = document.createElement('td');
        descTd.style.cssText = 'font-size:0.85rem;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        descTd.textContent = t.description || '—';

        const amountTd = document.createElement('td');
        amountTd.className = 'text-end';
        const strong = document.createElement('strong');
        strong.className = inc ? 'amount-positive' : 'amount-negative';
        strong.textContent = `${inc ? '+' : '-'}${formatMoney(t.amount, t.currency)}`;
        amountTd.appendChild(strong);

        tr.appendChild(dateTd);
        tr.appendChild(typeTd);
        tr.appendChild(catTd);
        tr.appendChild(descTd);
        tr.appendChild(amountTd);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    body.appendChild(wrap);

    const footer = document.createElement('div');
    footer.style.cssText = 'text-align:right;margin-top:10px;';
    const link = document.createElement('a');
    link.href = '/transactions';
    link.style.cssText = 'font-size:0.78rem;color:var(--ts);';
    link.textContent = 'View all transactions →';
    footer.appendChild(link);
    body.appendChild(footer);
}

function renderSavingsGoals(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';
    const goals = data.goals || [];
    if (goals.length === 0) {
        body.appendChild(emptyMsg('No active savings goals.'));
        return;
    }
    goals.forEach(g => {
        const wrap = document.createElement('div');
        wrap.style.marginBottom = '16px';

        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;margin-bottom:4px;';
        const name = document.createElement('span');
        name.style.cssText = 'font-size:0.88rem;font-weight:600;';
        name.textContent = g.name;
        const amounts = document.createElement('span');
        amounts.style.cssText = 'font-size:0.82rem;color:var(--ts);';
        amounts.textContent = `RON ${fmtCurrency(g.current_amount)} / RON ${fmtCurrency(g.target_amount)}`;
        row.appendChild(name);
        row.appendChild(amounts);

        const track = document.createElement('div');
        track.style.cssText = 'background:var(--gb);border-radius:6px;height:10px;overflow:hidden;';
        const bar = document.createElement('div');
        bar.style.cssText = `height:100%;width:${Math.min(g.pct, 100)}%;background:var(--up);border-radius:6px;transition:width 0.5s ease;`;
        track.appendChild(bar);

        const meta = document.createElement('div');
        meta.style.cssText = 'display:flex;justify-content:space-between;margin-top:3px;';
        const pctLabel = document.createElement('span');
        pctLabel.style.cssText = 'font-size:0.75rem;color:var(--th);';
        pctLabel.textContent = `${g.pct}% complete`;
        meta.appendChild(pctLabel);
        if (g.target_date) {
            const dateLabel = document.createElement('span');
            dateLabel.style.cssText = 'font-size:0.75rem;color:var(--th);';
            dateLabel.textContent = `Target: ${g.target_date}`;
            meta.appendChild(dateLabel);
        }

        wrap.appendChild(row);
        wrap.appendChild(track);
        wrap.appendChild(meta);
        body.appendChild(wrap);
    });
}

function renderBudgetVsActual(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const cats = data.categories || [];
    if (cats.length === 0) {
        body.innerHTML = '';
        body.appendChild(emptyMsg(data.budget_name ? 'No category limits set.' : 'No active budget.'));
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="140"></canvas>`;
    const p = PALETTE();
    const cBudget = widgetColor(colors, 'budget', () => p.income);
    const cActualOk = widgetColor(colors, 'actual_ok', () => p.savings);
    const cActualOver = widgetColor(colors, 'actual_over', () => p.expense);
    if (chartInstances[wid]) chartInstances[wid].destroy();
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type: 'bar',
        data: {
            labels: cats.map(c => c.name),
            datasets: [
                { label: 'Budget', data: cats.map(c => c.budget), backgroundColor: cBudget + '55', borderColor: cBudget, borderWidth: 1.5, borderRadius: 5 },
                {
                    label: 'Actual', data: cats.map(c => c.actual),
                    backgroundColor: cats.map(c => c.over ? cActualOver + '88' : cActualOk + '88'),
                    borderColor: cats.map(c => c.over ? cActualOver : cActualOk), borderWidth: 1.5, borderRadius: 5
                },
            ]
        },
        options: chartOpts({ prefix: 'RON ', title: data.budget_name || 'Budget vs Actual' })
    });
}

function renderPotentialToSave(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const net = data.current_net || 0;
    const pos = net >= 0;
    const months = (data.months || []).map(fmtMonth);
    const cumulative = data.cumulative || [];
    const latestCumulative = cumulative.length ? cumulative[cumulative.length - 1] : 0;
    const cumPos = latestCumulative >= 0;

    // Compact stat chips instead of one oversized number — matches the
    // Spending Trend widget's style, and leaves more room for the chart.
    body.innerHTML = '';
    const statRow = document.createElement('div');
    statRow.className = 'chip-row';

    const netChip = document.createElement('span');
    netChip.className = `stat-chip ${pos ? 'stat-chip-positive' : 'stat-chip-negative'}`;
    netChip.textContent = `Net this period: ${pos ? '+' : ''}RON ${fmtCurrency(net)}`;
    statRow.appendChild(netChip);

    if (months.length > 1) {
        const cumChip = document.createElement('span');
        cumChip.className = `stat-chip ${cumPos ? 'stat-chip-positive' : 'stat-chip-negative'}`;
        cumChip.textContent = `Cumulative: ${cumPos ? '+' : ''}RON ${fmtCurrency(latestCumulative)}`;
        statRow.appendChild(cumChip);
    }
    body.appendChild(statRow);

    if (months.length > 1) {
        const canvas = document.createElement('canvas');
        canvas.id = `chart-${wid}`;
        canvas.height = 90;
        body.appendChild(canvas);

        const p = PALETTE();
        const cNet = widgetColor(colors, 'net', () => p.savings);
        const cCumulative = widgetColor(colors, 'cumulative', () => p.income);
        if (chartInstances[wid]) chartInstances[wid].destroy();
        chartInstances[wid] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    { label: 'Net', data: data.net || [], borderColor: cNet, backgroundColor: cNet + '22', tension: 0.4, fill: true },
                    { label: 'Cumulative', data: data.cumulative || [], borderColor: cCumulative, backgroundColor: 'transparent', tension: 0.4, borderDash: [4, 4] }
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    }
}

function renderCategoryHeatmap(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    const months = data.months || [];
    const cats = data.categories || [];
    const matrix = data.matrix || {};
    const maxVal = data.max_value || 1;

    body.innerHTML = '';
    if (cats.length === 0 || months.length === 0) {
        body.appendChild(emptyMsg('No data for heatmap.'));
        return;
    }

    // BUG-06 fix (2026-09-02), attempt 9 — the dissolve-overlay idea
    // (attempts 5-8) never looked right regardless of how it was
    // structured. Simplified per explicit user direction: drop the
    // overlay/veil entirely and just style the category column with this
    // app's own existing "Customize" button recipe (glass.css .btn /
    // .btn-secondary) — var(--gl) background, var(--blur) (the stronger
    // card/button blur, not --blur-sidebar) backdrop-filter, a real
    // border and box-shadow for visual definition — since that
    // combination already reads clearly as "a solid surface" everywhere
    // else in this app without needing any special fade effect. Square
    // corners (border-radius: 0) on the category cells specifically, per
    // explicit request, deviating from the button's own rounded corners.
    const CAT_W = 140;
    const DATA_W = 90;
    const CAT_STYLE = 'background:var(--gl);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border:1px solid rgba(255,255,255,0.12);box-shadow:var(--sh);border-radius:0;';
    const totalWidth = CAT_W + months.length * DATA_W;

    const wrap = document.createElement('div');
    wrap.style.cssText = 'overflow-x:auto;overflow-y:auto;max-height:340px;';
    const table = document.createElement('table');
    table.style.cssText = `border-collapse:separate;border-spacing:2px;table-layout:fixed;width:${totalWidth}px;`;

    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    const cornerTh = document.createElement('th');
    cornerTh.style.cssText = `position:sticky;left:0;z-index:3;width:${CAT_W}px;${CAT_STYLE}`;
    headRow.appendChild(cornerTh);
    months.forEach(m => {
        const th = document.createElement('th');
        th.style.cssText = `width:${DATA_W}px;font-size:0.7rem;padding:4px 6px;color:var(--th);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;`;
        th.textContent = fmtMonth(m);
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    cats.forEach(cat => {
        const tr = document.createElement('tr');
        const nameTd = document.createElement('td');
        nameTd.style.cssText = `font-size:0.78rem;padding:4px 8px;white-space:nowrap;color:var(--tp);font-weight:500;position:sticky;left:0;z-index:3;width:${CAT_W}px;overflow:hidden;text-overflow:ellipsis;${CAT_STYLE}`;
        nameTd.title = cat;
        nameTd.textContent = cat;
        tr.appendChild(nameTd);

        months.forEach((_, i) => {
            const val = (matrix[cat] || [])[i] || 0;
            const opacity = val > 0 ? 0.15 + (val / maxVal) * 0.75 : 0;
            const td = document.createElement('td');
            td.style.cssText = `width:${DATA_W}px;text-align:right;padding:4px 8px;font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:rgba(124,58,237,${opacity.toFixed(2)});border-radius:3px;`;
            td.textContent = val > 0 ? 'RON ' + fmtCurrency(val) : '—';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    body.appendChild(wrap);
}

function renderTopCategoriesTrend(wid, data, chartType) {
    const body = document.getElementById(`wbody-${wid}`);
    const series = data.series || [];
    if (series.length === 0) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('No data available.'));
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="130"></canvas>`;
    if (chartInstances[wid]) chartInstances[wid].destroy();
    const type = chartType === 'bar' ? 'bar' : 'line';
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type,
        data: {
            labels: (data.months || []).map(fmtMonth),
            datasets: series.map((s, i) => ({
                label: s.name,
                data: s.data,
                borderColor: s.color || PALETTE().series[i % 8],
                backgroundColor: (s.color || PALETTE().series[i % 8]) + (type === 'bar' ? '88' : '22'),
                tension: 0.4,
                fill: false,
                borderWidth: 2,
                borderRadius: type === 'bar' ? 4 : 0,
            }))
        },
        options: chartOpts({ prefix: 'RON ' })
    });
}

function renderFixedVsVariable(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data.months || data.months.length === 0) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('No data available.'));
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="120"></canvas>`;
    const p = PALETTE();
    const cFixed = widgetColor(colors, 'fixed', () => p.expense);
    const cVariable = widgetColor(colors, 'variable', () => p.savings);
    if (chartInstances[wid]) chartInstances[wid].destroy();

    if (chartType === 'line') {
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'line',
            data: {
                labels: data.months.map(fmtMonth),
                datasets: [
                    { label: 'Fixed', data: data.fixed || [], borderColor: cFixed, backgroundColor: cFixed + '22', tension: 0.4, fill: false, borderWidth: 2 },
                    { label: 'Variable', data: data.variable || [], borderColor: cVariable, backgroundColor: cVariable + '22', tension: 0.4, fill: false, borderWidth: 2 },
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    } else {
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.months.map(fmtMonth),
                datasets: [
                    { label: 'Fixed', data: data.fixed || [], backgroundColor: cFixed + '88', borderColor: cFixed, borderWidth: 1.5, borderRadius: 4, stack: 's' },
                    { label: 'Variable', data: data.variable || [], backgroundColor: cVariable + '88', borderColor: cVariable, borderWidth: 1.5, borderRadius: 4, stack: 's' },
                ]
            },
            options: { ...chartOpts({ prefix: 'RON ' }), scales: { x: { stacked: true, grid: { color: p.neutral } }, y: { stacked: true, grid: { color: p.neutral }, beginAtZero: true, ticks: { callback: v => 'RON ' + v } } } }
        });
    }
}

function renderObligationsMonthly(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data.months || data.months.length === 0) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('No obligation transactions found.'));
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="120"></canvas>`;
    const p = PALETTE();
    const cObligations = widgetColor(colors, 'obligations', () => p.expense);
    const type = chartType === 'line' ? 'line' : 'bar';
    if (chartInstances[wid]) chartInstances[wid].destroy();
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type,
        data: {
            labels: data.months.map(fmtMonth),
            datasets: [{
                label: 'Obligations',
                data: data.totals || [],
                backgroundColor: type === 'line' ? cObligations + '22' : cObligations + '77',
                borderColor: cObligations,
                borderWidth: type === 'line' ? 2 : 1.5,
                borderRadius: type === 'bar' ? 5 : 0,
                tension: 0.4,
                fill: type === 'line',
            }]
        },
        options: chartOpts({ prefix: 'RON ' })
    });
}

function renderExtraRepaymentsYtd(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    const extra = data.extra_ytd || 0;
    const ytd = data.ytd || 0;
    const avg = data.avg_monthly || 0;
    const pct = ytd > 0 ? Math.min((extra / ytd) * 100, 100) : 0;

    body.innerHTML = `
        <div style="padding:12px 0;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-size:0.85rem;font-weight:600;">Extra Repayments YTD</span>
                <span style="font-size:0.85rem;color:var(--up);">RON ${fmtCurrency(extra)}</span>
            </div>
            <div style="background:var(--gb);border-radius:6px;height:10px;overflow:hidden;">
                <div style="height:100%;width:${pct.toFixed(1)}%;background:var(--up);border-radius:6px;transition:width 0.5s ease;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:6px;">
                <span style="font-size:0.75rem;color:var(--th);">${pct.toFixed(1)}% of total obligations</span>
                <span style="font-size:0.75rem;color:var(--th);">Avg/mo: RON ${fmtCurrency(avg)}</span>
            </div>
            <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--rim);">
                <div style="font-size:0.8rem;color:var(--th);">Total obligations YTD</div>
                <div style="font-size:1.4rem;font-weight:700;color:var(--dn);">RON ${fmtCurrency(ytd)}</div>
            </div>
        </div>`;
}

function renderDebtPaymentsMetric(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    const ytd = data.ytd || 0;
    const avg = data.avg_monthly || 0;
    const months = (data.months || []).length;
    body.innerHTML = `
        <div style="text-align:center;padding:20px 0;">
            <div style="font-size:0.8rem;color:var(--th);margin-bottom:6px;">Total Debt Payments YTD</div>
            <div style="font-size:2.4rem;font-weight:700;color:var(--dn);">RON ${fmtCurrency(ytd)}</div>
            <div style="display:flex;gap:24px;justify-content:center;margin-top:20px;">
                <div>
                    <div style="font-size:0.75rem;color:var(--th);">Avg / Month</div>
                    <div style="font-size:1.2rem;font-weight:600;color:var(--tp);">RON ${fmtCurrency(avg)}</div>
                </div>
                <div>
                    <div style="font-size:0.75rem;color:var(--th);">Months Tracked</div>
                    <div style="font-size:1.2rem;font-weight:600;color:var(--tp);">${months}</div>
                </div>
            </div>
        </div>`;
}

// Below this RON drift threshold, a bank snapshot is treated as "reconciled"
// rather than flagged — replaying past events is exact arithmetic, but a
// snapshot's own reported balance can still carry bank-side rounding, so a
// sub-1-RON gap isn't a real discrepancy worth alarming over.
const LOAN_RECONCILIATION_TOLERANCE = 1;

function buildReconciliationBadge(reconciliation) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:6px;margin-top:12px;font-size:0.8rem;';

    const dot = document.createElement('span');
    dot.style.cssText = 'width:8px;height:8px;border-radius:50%;flex-shrink:0;';

    const text = document.createElement('span');
    text.style.color = 'var(--ts)';

    const latest = reconciliation && reconciliation.length ? reconciliation[reconciliation.length - 1] : null;
    if (!latest) {
        dot.style.background = 'var(--gb)';
        text.textContent = 'No bank snapshot yet';
    } else if (Math.abs(latest.delta) < LOAN_RECONCILIATION_TOLERANCE) {
        dot.style.background = 'var(--up)';
        text.textContent = `Reconciled as of ${latest.date}`;
    } else {
        dot.style.background = 'var(--ac2)';
        const sign = latest.delta > 0 ? '+' : '';
        text.textContent = `Drift: ${sign}RON ${fmtCurrency(latest.delta)} (as of ${latest.date})`;
    }

    row.appendChild(dot);
    row.appendChild(text);
    return row;
}

function buildPrincipalProgress(principal, currentBalance) {
    const paidPct = Math.max(0, Math.min(100, (1 - currentBalance / principal) * 100));

    const section = document.createElement('div');
    section.style.cssText = 'margin-top:14px;';

    const labelRow = document.createElement('div');
    labelRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.75rem;color:var(--ts);margin-bottom:4px;';
    const left = document.createElement('span');
    left.textContent = `${paidPct.toFixed(1)}% of principal paid off`;
    const right = document.createElement('span');
    right.textContent = `RON ${fmtCurrency(principal)} original`;
    labelRow.appendChild(left);
    labelRow.appendChild(right);
    section.appendChild(labelRow);

    const track = document.createElement('div');
    track.className = 'progress';
    track.style.height = '8px';
    const fill = document.createElement('div');
    fill.className = 'progress-bar';
    fill.style.width = `${paidPct}%`;
    track.appendChild(fill);
    section.appendChild(track);

    return section;
}

function buildPayoffDeltaBar(startDate, baselinePayoffDate, payoffDate, yearsSaved, monthsSaved) {
    const start = new Date(startDate);
    const baselineEnd = new Date(baselinePayoffDate);
    const actualEnd = new Date(payoffDate);
    const baselineDays = (baselineEnd - start) / 86400000;
    const actualDays = (actualEnd - start) / 86400000;
    if (!(baselineDays > 0)) return null;
    const actualPct = Math.max(0, Math.min(100, (actualDays / baselineDays) * 100));

    const section = document.createElement('div');
    section.style.cssText = 'margin-top:14px;';

    const labelRow = document.createElement('div');
    labelRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.75rem;color:var(--ts);margin-bottom:4px;';
    const left = document.createElement('span');
    left.textContent = `Payoff: ${payoffDate}`;
    const right = document.createElement('span');
    right.textContent = yearsSaved != null ? `${yearsSaved} yrs (${monthsSaved} mo) sooner than baseline` : `Baseline: ${baselinePayoffDate}`;
    labelRow.appendChild(left);
    labelRow.appendChild(right);
    section.appendChild(labelRow);

    // Track represents the full Baseline timeline (start → baseline payoff);
    // the fill stops at the Actual payoff instead — the muted gap left over
    // in the track is visually "how much sooner", without needing two
    // overlapping bars to convey the same baseline-vs-actual contrast.
    const track = document.createElement('div');
    track.className = 'progress';
    track.style.height = '8px';
    const fill = document.createElement('div');
    fill.className = 'progress-bar bg-success';
    fill.style.width = `${actualPct}%`;
    track.appendChild(fill);
    section.appendChild(track);

    return section;
}

function renderLoanTrajectory(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);

    if (!data || data.no_loans) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('No loans tracked yet.'));
        return;
    }

    const actualPeriods = data.actual_periods || [];
    const baselinePeriods = data.baseline_periods || [];
    if (!actualPeriods.length && !baselinePeriods.length) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('Not enough data yet to project a trajectory.'));
        return;
    }

    body.innerHTML = `<canvas id="chart-${wid}" height="140"></canvas>`;

    // Actual and Baseline pay off at different times, so their period arrays
    // have different lengths — sharing one labels axis (the longer of the
    // two) and padding the shorter dataset with null lets Chart.js draw
    // exactly that: the Actual line stops at its own payoff instead of
    // being forced to continue (or the axis being cut short).
    const longer = actualPeriods.length >= baselinePeriods.length ? actualPeriods : baselinePeriods;
    const labels = longer.map(p => p.date);
    const actualData = labels.map((_, i) => (actualPeriods[i] ? actualPeriods[i].balance_end : null));
    const baselineData = labels.map((_, i) => (baselinePeriods[i] ? baselinePeriods[i].balance_end : null));

    const p = PALETTE();
    const cActual = widgetColor(colors, 'actual', () => p.income);
    const cBaseline = widgetColor(colors, 'baseline', () => p.neutral);

    if (chartInstances[wid]) chartInstances[wid].destroy();
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Actual', data: actualData, borderColor: cActual, backgroundColor: cActual + '22', borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false },
                { label: 'Baseline', data: baselineData, borderColor: cBaseline, backgroundColor: cBaseline + '22', borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: false, borderDash: [4, 4] },
            ],
        },
        options: chartOpts({ prefix: 'RON ' }),
    });
}

function renderDebtReductionImpact(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    if (!data || data.no_loans) {
        body.appendChild(emptyMsg('No loans tracked yet.'));
        return;
    }

    const wrap = document.createElement('div');
    wrap.style.cssText = 'padding:4px 0;text-align:center;';

    // loan_name is user-entered data — createElement/textContent, never
    // innerHTML, matching this file's established security property.
    const label = document.createElement('div');
    label.style.cssText = 'font-size:0.8rem;color:var(--th);margin-bottom:6px;';
    label.textContent = data.loan_name || 'Loan';
    wrap.appendChild(label);

    const headline = document.createElement('div');
    headline.style.cssText = 'font-size:2rem;font-weight:700;color:var(--up);';
    headline.textContent = data.debt_reduction_vs_baseline != null
        ? `RON ${fmtCurrency(data.debt_reduction_vs_baseline)}`
        : '—';
    wrap.appendChild(headline);

    const headlineSub = document.createElement('div');
    headlineSub.style.cssText = 'font-size:0.85rem;color:var(--ts);margin-top:2px;';
    headlineSub.textContent = 'less debt than the original plan, as of today';
    wrap.appendChild(headlineSub);

    if (data.baseline_balance_today != null && data.current_balance != null) {
        const compareRow = document.createElement('div');
        compareRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.78rem;color:var(--ts);margin-top:16px;padding-top:12px;border-top:1px solid var(--gb);';
        const baselineSpan = document.createElement('span');
        baselineSpan.textContent = `Baseline today: RON ${fmtCurrency(data.baseline_balance_today)}`;
        const actualSpan = document.createElement('span');
        actualSpan.textContent = `Actual today: RON ${fmtCurrency(data.current_balance)}`;
        compareRow.appendChild(baselineSpan);
        compareRow.appendChild(actualSpan);
        wrap.appendChild(compareRow);
    }

    const extraPaidRow = document.createElement('div');
    extraPaidRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.85rem;margin-top:10px;';
    const extraLabel = document.createElement('span');
    extraLabel.style.color = 'var(--ts)';
    extraLabel.textContent = 'Total extra paid';
    const extraValue = document.createElement('strong');
    extraValue.style.fontVariantNumeric = 'tabular-nums';
    extraValue.textContent = `RON ${fmtCurrency(data.total_extra_paid || 0)}`;
    extraPaidRow.appendChild(extraLabel);
    extraPaidRow.appendChild(extraValue);
    wrap.appendChild(extraPaidRow);

    const link = document.createElement('a');
    link.href = '/loans';
    link.style.cssText = 'display:inline-block;margin-top:14px;font-size:0.8rem;';
    link.textContent = 'View Details →';
    wrap.appendChild(link);

    body.appendChild(wrap);
}

function renderInterestOverview(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    if (!data || data.no_loans) {
        body.appendChild(emptyMsg('No loans tracked yet.'));
        return;
    }

    const wrap = document.createElement('div');
    wrap.style.cssText = 'padding:4px 0;text-align:center;';

    // loan_name is user-entered data — createElement/textContent, never
    // innerHTML, matching this file's established security property.
    const label = document.createElement('div');
    label.style.cssText = 'font-size:0.8rem;color:var(--th);margin-bottom:6px;';
    label.textContent = data.loan_name || 'Loan';
    wrap.appendChild(label);

    const headline = document.createElement('div');
    headline.style.cssText = 'font-size:2rem;font-weight:700;color:var(--tp);';
    headline.textContent = data.current_total_dobanda != null
        ? `RON ${fmtCurrency(data.current_total_dobanda)}`
        : '—';
    wrap.appendChild(headline);

    const headlineSub = document.createElement('div');
    headlineSub.style.cssText = 'font-size:0.85rem;color:var(--ts);margin-top:2px;';
    headlineSub.textContent = data.current_total_dobanda != null
        ? `total interest remaining, per bank snapshot on ${data.dobanda_snapshot_date}`
        : 'Log a bank snapshot with "Remaining Total Interest" filled in to see this';
    wrap.appendChild(headlineSub);

    if (data.current_rate_pct != null) {
        const rateRow = document.createElement('div');
        rateRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.85rem;margin-top:16px;padding-top:12px;border-top:1px solid var(--gb);';
        const rateLabel = document.createElement('span');
        rateLabel.style.color = 'var(--ts)';
        rateLabel.textContent = 'Current rate';
        const rateValue = document.createElement('strong');
        rateValue.style.fontVariantNumeric = 'tabular-nums';
        rateValue.textContent = `${data.current_rate_pct}%`;
        rateRow.appendChild(rateLabel);
        rateRow.appendChild(rateValue);
        wrap.appendChild(rateRow);
    }

    if (data.dobanda_saved_estimate != null) {
        const savedRow = document.createElement('div');
        savedRow.style.cssText = 'display:flex;justify-content:space-between;font-size:0.85rem;margin-top:10px;';
        const savedLabel = document.createElement('span');
        savedLabel.style.color = 'var(--ts)';
        savedLabel.textContent = 'Estimated interest saved';
        const savedValue = document.createElement('strong');
        savedValue.style.cssText = 'font-variant-numeric:tabular-nums;color:var(--up);';
        savedValue.textContent = `RON ${fmtCurrency(data.dobanda_saved_estimate)}`;
        savedRow.appendChild(savedLabel);
        savedRow.appendChild(savedValue);
        wrap.appendChild(savedRow);
    }

    const link = document.createElement('a');
    link.href = '/loans';
    link.style.cssText = 'display:inline-block;margin-top:14px;font-size:0.8rem;';
    link.textContent = 'View Details →';
    wrap.appendChild(link);

    body.appendChild(wrap);
}

function renderBudgetAccounts(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    if (!data || !data.accounts || data.accounts.length === 0) {
        body.appendChild(emptyMsg('No accounts are currently included in the budget.'));
        return;
    }

    const list = document.createElement('div');
    data.accounts.forEach(acc => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--gb);';

        const left = document.createElement('div');
        // account name is user-entered data — createElement/textContent,
        // never innerHTML, matching this file's established security property.
        const nameEl = document.createElement('div');
        nameEl.style.cssText = 'font-weight:600;font-size:0.9rem;';
        nameEl.textContent = acc.name;
        const typeEl = document.createElement('small');
        typeEl.style.cssText = 'color:var(--ts);text-transform:capitalize;';
        typeEl.textContent = (acc.type || '').replace('_', ' ');
        left.appendChild(nameEl);
        left.appendChild(typeEl);

        const balEl = document.createElement('div');
        const positive = acc.current_balance >= 0;
        balEl.style.cssText = `font-weight:700;font-variant-numeric:tabular-nums;color:${positive ? 'var(--up)' : 'var(--dn)'};`;
        balEl.textContent = `${acc.currency} ${fmtCurrency(acc.current_balance)}`;

        row.appendChild(left);
        row.appendChild(balEl);
        list.appendChild(row);
    });
    body.appendChild(list);

    const link = document.createElement('a');
    link.href = '/accounts';
    link.style.cssText = 'display:inline-block;margin-top:12px;font-size:0.8rem;';
    link.textContent = 'View Accounts →';
    body.appendChild(link);
}

function renderLoanSummary(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    if (!data || data.no_loans) {
        body.appendChild(emptyMsg('No loans tracked yet.'));
        return;
    }

    const wrap = document.createElement('div');
    wrap.style.cssText = 'padding:4px 0;text-align:center;';

    // loan_name is user-entered data — createElement/textContent, never
    // innerHTML, matching this file's established security property.
    const label = document.createElement('div');
    label.style.cssText = 'font-size:0.8rem;color:var(--th);margin-bottom:6px;';
    label.textContent = data.loan_name || 'Loan';
    wrap.appendChild(label);

    const balance = document.createElement('div');
    balance.style.cssText = 'font-size:2.2rem;font-weight:700;color:var(--tp);';
    balance.textContent = data.current_balance != null ? `RON ${fmtCurrency(data.current_balance)}` : '—';
    wrap.appendChild(balance);

    if (data.years_saved != null && data.interest_saved != null) {
        const saved = document.createElement('div');
        saved.style.cssText = 'font-size:0.85rem;color:var(--up);margin-top:6px;';
        saved.textContent = `${data.years_saved} yrs (${data.months_saved} mo) / RON ${fmtCurrency(data.interest_saved)} saved`;
        wrap.appendChild(saved);
    }

    wrap.appendChild(buildReconciliationBadge(data.reconciliation || []));

    if (data.principal && data.current_balance != null) {
        wrap.appendChild(buildPrincipalProgress(data.principal, data.current_balance));
    }

    if (data.start_date && data.baseline_payoff_date && data.payoff_date) {
        const deltaBar = buildPayoffDeltaBar(data.start_date, data.baseline_payoff_date, data.payoff_date, data.years_saved, data.months_saved);
        if (deltaBar) wrap.appendChild(deltaBar);
    }

    const link = document.createElement('a');
    link.href = '/loans';
    link.style.cssText = 'display:inline-block;margin-top:14px;font-size:0.8rem;';
    link.textContent = 'View Details →';
    wrap.appendChild(link);

    body.appendChild(wrap);
}

function renderLoansOverview(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    if (!data || data.no_loans || !data.loans || data.loans.length === 0) {
        body.appendChild(emptyMsg('No loans tracked yet.'));
        return;
    }

    const list = document.createElement('div');
    data.loans.forEach(loan => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--gb);';

        const left = document.createElement('div');
        // loan_name is user-entered data — createElement/textContent, never
        // innerHTML, matching this file's established security property.
        const nameEl = document.createElement('div');
        nameEl.style.cssText = 'font-weight:600;font-size:0.9rem;';
        nameEl.textContent = loan.loan_name || 'Loan';
        const subEl = document.createElement('small');
        subEl.style.cssText = 'color:var(--ts);';
        subEl.textContent = loan.payoff_date ? `Payoff: ${loan.payoff_date}` : 'Payoff date unavailable';
        left.appendChild(nameEl);
        left.appendChild(subEl);

        const right = document.createElement('div');
        right.style.cssText = 'text-align:right;';
        const balEl = document.createElement('div');
        balEl.style.cssText = 'font-weight:700;font-variant-numeric:tabular-nums;';
        balEl.textContent = loan.current_balance != null ? `RON ${fmtCurrency(loan.current_balance)}` : '—';
        right.appendChild(balEl);
        if (loan.years_saved != null && loan.interest_saved != null) {
            const savedEl = document.createElement('small');
            savedEl.style.cssText = 'color:var(--up);font-variant-numeric:tabular-nums;';
            savedEl.textContent = `${loan.years_saved} yrs (${loan.months_saved} mo) saved`;
            right.appendChild(savedEl);
        }

        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
    });
    body.appendChild(list);

    const link = document.createElement('a');
    link.href = '/loans';
    link.style.cssText = 'display:inline-block;margin-top:12px;font-size:0.8rem;';
    link.textContent = 'View Details →';
    body.appendChild(link);
}

function renderSpendingTrend(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = '';

    // Anomaly alerts shown first, as compact wrapped chips, so they're
    // visible without scrolling the widget (moved above the chart — was
    // previously below it and easy to miss on a fixed-height card).
    // Always global (server-side, ignores this widget's own filter) —
    // built with createElement/textContent since category names are
    // user-controlled data (Sprint 20 scope decision 1).
    const anomalies = data.anomalies || [];
    const alertRow = document.createElement('div');
    alertRow.className = 'chip-row';
    if (anomalies.length) {
        anomalies.forEach(a => {
            const chip = document.createElement('span');
            chip.className = 'anomaly-chip';
            chip.textContent = `${a.category} +${a.pct_above}%`;
            chip.title = `RON ${fmtCurrency(a.current)} vs 3-month avg RON ${fmtCurrency(a.average)}`;
            alertRow.appendChild(chip);
        });
    } else {
        const chip = document.createElement('span');
        chip.className = 'anomaly-chip anomaly-chip-clear';
        chip.textContent = 'No anomalies';
        alertRow.appendChild(chip);
    }
    body.appendChild(alertRow);

    const canvas = document.createElement('canvas');
    canvas.id = `chart-${wid}`;
    canvas.height = 120;
    body.appendChild(canvas);

    const p = PALETTE();
    const cSpend = widgetColor(colors, 'spend', () => p.expense);
    const cAvg = widgetColor(colors, 'moving_avg', () => '#f59e0b');
    const labels = (data.months || []).map(fmtMonth);
    if (chartInstances[wid]) chartInstances[wid].destroy();

    const type = chartType === 'bar' ? 'bar' : 'line';
    const totalsDataset = type === 'bar'
        ? { label: 'Spend', data: data.totals || [], backgroundColor: cSpend + '77', borderColor: cSpend, borderWidth: 1.5, borderRadius: 5 }
        : { label: 'Spend', data: data.totals || [], borderColor: cSpend, backgroundColor: cSpend + '22', tension: 0.4, fill: false, borderWidth: 2 };
    const avgDataset = {
        label: '3-Month Average', data: data.moving_avg || [], borderColor: cAvg,
        backgroundColor: 'transparent', borderDash: [4, 4], tension: 0.4, fill: false, borderWidth: 2, type: 'line', spanGaps: true,
    };

    chartInstances[wid] = new Chart(canvas.getContext('2d'), {
        type,
        data: { labels, datasets: [totalsDataset, avgDataset] },
        options: chartOpts({ prefix: 'RON ' })
    });
}

function renderYoyComparison(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const cats = data.categories || [];
    if (cats.length === 0) {
        body.innerHTML = '';
        body.appendChild(emptyMsg('No expense data yet for this year or last year.'));
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="140"></canvas>`;
    const p = PALETTE();
    const cThisYear = widgetColor(colors, 'this_year', () => p.income);
    const cLastYear = widgetColor(colors, 'last_year', () => p.neutral);
    if (chartInstances[wid]) chartInstances[wid].destroy();
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type: 'bar',
        data: {
            labels: cats.map(c => c.name),
            datasets: [
                { label: 'Last Year', data: cats.map(c => c.last_year), backgroundColor: cLastYear + '55', borderColor: cLastYear, borderWidth: 1.5, borderRadius: 5 },
                { label: 'This Year', data: cats.map(c => c.this_year), backgroundColor: cThisYear + '88', borderColor: cThisYear, borderWidth: 1.5, borderRadius: 5 },
            ]
        },
        options: chartOpts({ prefix: 'RON ' })
    });
}

// ── Dashboard CRUD ───────────────────────────────────────────────────────────

function setupDashboardModal() {
    document.getElementById('newDashboardBtn').addEventListener('click', openCreateDashboardModal);
    document.getElementById('dashModalSave').addEventListener('click', saveDashboardModal);
    document.getElementById('dashModalName').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveDashboardModal();
    });
}

function openCreateDashboardModal() {
    document.getElementById('dashboardModalTitle').textContent = 'New Dashboard';
    document.getElementById('dashModalId').value = '';
    document.getElementById('dashModalName').value = '';
    document.getElementById('dashModalDesc').value = '';
    new bootstrap.Modal(document.getElementById('dashboardModal')).show();
    setTimeout(() => document.getElementById('dashModalName').focus(), 300);
}

function openEditDashboardModal(dashboardId) {
    const dash = dashboards.find(d => d.id === dashboardId);
    if (!dash) return;
    document.getElementById('dashboardModalTitle').textContent = 'Edit Dashboard';
    document.getElementById('dashModalId').value = dashboardId;
    document.getElementById('dashModalName').value = dash.name;
    document.getElementById('dashModalDesc').value = dash.description || '';
    new bootstrap.Modal(document.getElementById('dashboardModal')).show();
    setTimeout(() => document.getElementById('dashModalName').focus(), 300);
}

async function saveDashboardModal() {
    const id = document.getElementById('dashModalId').value;
    const name = document.getElementById('dashModalName').value.trim();
    const description = document.getElementById('dashModalDesc').value.trim();

    if (!name) {
        document.getElementById('dashModalName').classList.add('is-invalid');
        document.getElementById('dashModalName').focus();
        return;
    }
    document.getElementById('dashModalName').classList.remove('is-invalid');

    const modalEl = document.getElementById('dashboardModal');

    if (id) {
        const r = await fetch(`/api/dashboards/${id}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        const j = await r.json();
        if (j.success) {
            const dash = dashboards.find(d => d.id === parseInt(id));
            if (dash) { dash.name = name; dash.description = description; }
            renderTabs();
            bootstrap.Modal.getInstance(modalEl).hide();
        } else {
            Swal.fire({ icon: 'error', title: 'Error', text: j.message });
        }
    } else {
        const r = await fetch('/api/dashboards/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        const j = await r.json();
        if (j.success) {
            bootstrap.Modal.getInstance(modalEl).hide();
            await initDashboards();
        } else {
            Swal.fire({ icon: 'error', title: 'Error', text: j.message });
        }
    }
}

async function confirmDeleteDashboard(dashboardId) {
    const dash = dashboards.find(d => d.id === dashboardId);
    if (!dash) return;

    let widgetCount = 0;
    try {
        const wr = await fetch(`/api/dashboards/${dashboardId}/widgets`);
        const wj = await wr.json();
        widgetCount = wj.success ? wj.widgets.length : 0;
    } catch (_) {}

    const result = await Swal.fire({
        title: 'Delete Dashboard?',
        text: `Delete "${dash.name}" and its ${widgetCount} widget${widgetCount !== 1 ? 's' : ''}? This cannot be undone.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#ef4444',
    });
    if (!result.isConfirmed) return;

    const r = await fetch(`/api/dashboards/${dashboardId}/delete`, { method: 'POST' });
    const j = await r.json();
    if (!j.success) return;

    dashboards = dashboards.filter(d => d.id !== dashboardId);
    const next = dashboards[0];
    if (next) {
        dashboards.forEach(d => d.is_active = (d.id === next.id));
        activeDash = next;
        renderTabs();
        await loadDashboard(next.id);
        fetch(`/api/dashboards/${next.id}/activate`, { method: 'POST' }).catch(() => {});
    } else {
        activeDash = null;
        renderTabs();
        const grid = document.getElementById('widgetGrid');
        grid.innerHTML = '';
        grid.appendChild(emptyBlock('No dashboards. Click + to create one.'));
        document.getElementById('customizeWidgetList').innerHTML = '';
    }
}

// ── Widget settings modal ────────────────────────────────────────────────────

function setupWidgetSettingsModal() {
    document.getElementById('wsModalSave').addEventListener('click', saveWidgetSettings);
}

async function openWidgetSettingsModal(widgetId) {
    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (!wj.success) return;
    const w = wj.widgets.find(x => x.id === widgetId);
    if (!w) return;

    document.getElementById('wsWidgetId').value = widgetId;
    document.getElementById('wsTitle').value = w.custom_title || '';

    const ctSection = document.getElementById('wsChartTypeSection');
    const ctPicker = document.getElementById('wsChartTypePicker');
    const typeOpts = CHART_TYPE_OPTIONS[w.widget_type];
    if (typeOpts) {
        ctSection.style.display = '';
        ctPicker.innerHTML = '';
        const activeType = w.chart_type || typeOpts[0];
        typeOpts.forEach(t => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chart-type-btn' + (t === activeType ? ' active' : '');
            btn.dataset.type = t;
            btn.textContent = CHART_TYPE_LABELS[t] || t;
            btn.addEventListener('click', () => {
                ctPicker.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
            ctPicker.appendChild(btn);
        });
    } else {
        ctSection.style.display = 'none';
    }

    const catSection = document.getElementById('wsCategorySection');
    const catList = document.getElementById('wsCategoryList');
    const filterSupport = FILTER_SUPPORT[w.widget_type] || {};
    if (filterSupport.categories) {
        catSection.style.display = '';
        catList.innerHTML = '';
        try {
            const cr = await fetch('/api/categories/list');
            const cj = await cr.json();
            const cats = cj.success ? cj.categories : [];
            const selectedIds = new Set((w.filter_config?.category_ids || []));
            cats.forEach(c => catList.appendChild(buildFilterCheckItem(c.id, c.name, selectedIds.has(c.id))));
        } catch (_) {
            catList.appendChild(errorBlock('Failed to load categories.'));
        }
    } else {
        catSection.style.display = 'none';
    }

    const accSection = document.getElementById('wsAccountSection');
    const accList = document.getElementById('wsAccountList');
    if (filterSupport.accounts) {
        accSection.style.display = '';
        accList.innerHTML = '';
        try {
            const ar = await fetch('/api/accounts/list');
            const aj = await ar.json();
            const accs = aj.success ? aj.accounts : [];
            const selectedIds = new Set((w.filter_config?.account_ids || []));
            accs.forEach(a => accList.appendChild(buildFilterCheckItem(a.id, a.name, selectedIds.has(a.id))));
        } catch (_) {
            accList.appendChild(errorBlock('Failed to load accounts.'));
        }
    } else {
        accSection.style.display = 'none';
    }

    const loanSection = document.getElementById('wsLoanSection');
    const loanSelect = document.getElementById('wsLoanSelect');
    if (filterSupport.loans) {
        loanSection.style.display = '';
        loanSelect.innerHTML = '';
        try {
            const lr = await fetch('/api/loans/list');
            const lj = await lr.json();
            const loans = lj.success ? lj.loans : [];
            const defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = loans.length ? 'First loan (default)' : 'No loans yet';
            loanSelect.appendChild(defaultOpt);
            const selectedId = w.filter_config?.loan_id;
            loans.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.id;
                opt.textContent = l.name;
                if (selectedId != null && String(l.id) === String(selectedId)) opt.selected = true;
                loanSelect.appendChild(opt);
            });
        } catch (_) {
            const errOpt = document.createElement('option');
            errOpt.textContent = 'Failed to load loans';
            loanSelect.appendChild(errOpt);
        }
    } else {
        loanSection.style.display = 'none';
    }

    const colorSection = document.getElementById('wsColorSection');
    const colorList = document.getElementById('wsColorList');
    const slots = COLOR_SLOTS[w.widget_type];
    if (slots) {
        colorSection.style.display = '';
        colorList.innerHTML = '';
        const overrides = w.chart_colors || {};
        slots.forEach(slot => {
            const defaultValue = slot.default();
            colorList.appendChild(
                buildColorPickerItem(slot.key, slot.label, overrides[slot.key] || defaultValue, defaultValue)
            );
        });
    } else {
        colorSection.style.display = 'none';
    }

    new bootstrap.Modal(document.getElementById('widgetSettingsModal')).show();
}

function buildColorPickerItem(key, label, value, defaultValue) {
    const row = document.createElement('div');
    row.className = 'color-picker-item';
    row.dataset.colorKey = key;
    row.dataset.defaultValue = defaultValue;

    const labelEl = document.createElement('span');
    labelEl.className = 'color-picker-item-label';
    labelEl.textContent = label;
    row.appendChild(labelEl);

    const controls = document.createElement('div');
    controls.className = 'color-picker-item-controls';

    const input = document.createElement('input');
    input.type = 'color';
    input.value = value;
    controls.appendChild(input);

    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'color-picker-reset-btn';
    resetBtn.textContent = 'Reset';
    resetBtn.addEventListener('click', () => { input.value = defaultValue; });
    controls.appendChild(resetBtn);

    row.appendChild(controls);
    return row;
}

function buildFilterCheckItem(id, name, checked) {
    const label = document.createElement('label');
    label.className = 'filter-check-item';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = id;
    cb.checked = checked;
    const span = document.createElement('span');
    span.textContent = name;
    label.appendChild(cb);
    label.appendChild(span);
    return label;
}

async function saveWidgetSettings() {
    const widgetId = parseInt(document.getElementById('wsWidgetId').value);

    const customTitle = document.getElementById('wsTitle').value.trim() || null;

    const activeCTBtn = document.querySelector('#wsChartTypePicker .chart-type-btn.active');
    const chartType = activeCTBtn ? activeCTBtn.dataset.type : null;

    const categoryIds = Array.from(document.querySelectorAll('#wsCategoryList input:checked')).map(cb => parseInt(cb.value));
    const accountIds = Array.from(document.querySelectorAll('#wsAccountList input:checked')).map(cb => parseInt(cb.value));
    const filterConfig = {};
    if (categoryIds.length) filterConfig.category_ids = categoryIds;
    if (accountIds.length) filterConfig.account_ids = accountIds;

    // Guarded by the section's own visibility (not just a truthy value) —
    // #wsLoanSelect is a single shared element across widget types, so its
    // .value can still hold a stale selection from a previously-open widget
    // that didn't support a loan filter at all.
    const loanSection = document.getElementById('wsLoanSection');
    const loanSelect = document.getElementById('wsLoanSelect');
    if (loanSection && loanSection.style.display !== 'none' && loanSelect && loanSelect.value) {
        filterConfig.loan_id = parseInt(loanSelect.value);
    }

    const filterConfigToSend = Object.keys(filterConfig).length ? filterConfig : null;

    // Only send colors that were actually changed from their default — an
    // untouched slot keeps following the theme instead of being frozen to
    // whatever the default happened to resolve to at save time.
    const chartColors = {};
    document.querySelectorAll('#wsColorList .color-picker-item').forEach(row => {
        const input = row.querySelector('input[type="color"]');
        const def = (row.dataset.defaultValue || '').toLowerCase();
        if (input && input.value.toLowerCase() !== def) {
            chartColors[row.dataset.colorKey] = input.value;
        }
    });
    const chartColorsToSend = Object.keys(chartColors).length ? chartColors : null;

    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            custom_title: customTitle,
            chart_type: chartType,
            filter_config: filterConfigToSend,
            chart_colors: chartColorsToSend,
        })
    });
    const j = await r.json();
    if (!j.success) return;

    bootstrap.Modal.getInstance(document.getElementById('widgetSettingsModal')).hide();

    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (!wj.success) return;
    const updatedW = wj.widgets.find(x => x.id === widgetId);
    if (!updatedW) return;

    const titleEl = document.querySelector(`#widget-${widgetId} .widget-title`);
    if (titleEl) titleEl.textContent = updatedW.custom_title || updatedW.title;

    if (updatedW.is_enabled) loadWidgetData(updatedW);
}

// ── Widget add / remove ──────────────────────────────────────────────────────

async function addWidgetToDashboard(widgetType) {
    if (!activeDash) return;

    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widget_type: widgetType })
    });
    const j = await r.json();
    if (j.success && j.widget) {
        const w = j.widget;
        // BUG-07 fix (2026-09-02): loadDashboard() leaves a "No widgets
        // configured" message in the grid when a dashboard starts empty
        // (a freshly-created one always does) — without removing it here,
        // adding the first widget appended a real card right alongside
        // that stale message instead of replacing it, easy to miss and
        // read as "nothing happened" until a page refresh cleared it.
        document.getElementById('widgetGridEmptyState')?.remove();
        const card = buildWidgetShell(w);
        document.getElementById('widgetGrid').appendChild(card);
        loadWidgetData(w);

        const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
        const wj = await wr.json();
        if (wj.success) refreshCustomizePanel(wj.widgets);
    } else {
        Swal.fire({ icon: 'error', title: 'Error', text: j.message });
    }
}

async function confirmRemoveWidget(widgetId, widgetTitle) {
    const result = await Swal.fire({
        title: 'Remove Widget?',
        text: `Remove "${widgetTitle}" from this dashboard? This cannot be undone.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Remove',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#ef4444',
    });
    if (!result.isConfirmed) return;

    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/remove`, { method: 'POST' });
    const j = await r.json();
    if (!j.success) return;

    const card = document.getElementById(`widget-${widgetId}`);
    if (card) card.remove();
    if (chartInstances[widgetId]) {
        chartInstances[widgetId].destroy();
        delete chartInstances[widgetId];
    }

    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (wj.success) refreshCustomizePanel(wj.widgets);
}

// ── Shared chart options ─────────────────────────────────────────────────────
function chartOpts({ prefix = '', title = '' } = {}) {
    const p = PALETTE();
    return {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { display: true, position: 'top', labels: { padding: 12, font: { size: 11 } } },
            title: title ? { display: true, text: title, font: { size: 12 } } : { display: false },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${prefix}${fmtCurrency(ctx.parsed.y ?? ctx.parsed)}` } }
        },
        scales: {
            x: { grid: { color: p.neutral } },
            y: { beginAtZero: true, grid: { color: p.neutral }, ticks: { callback: v => prefix + fmtCurrency(v) } }
        }
    };
}
