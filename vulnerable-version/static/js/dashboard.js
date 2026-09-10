// =============================================================================
// Aura Dashboard — Multi-Dashboard System
// Sprint 8: Flame Breathing — Eighth Form
// =============================================================================

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
let userId         = null;
let dashboards     = [];
let activeDash     = null;
let chartInstances = {};   // keyed by widget id

// ── Colour helpers ────────────────────────────────────────────────────────────
function css(prop) {
    return getComputedStyle(document.documentElement).getPropertyValue(prop).trim();
}

function applyChartDefaults() {
    Chart.defaults.color       = css('--ts');
    Chart.defaults.borderColor = css('--gb');
    Chart.defaults.font.family = css('--fb').replace(/'/g, '');
}

const PALETTE = () => ({
    income:   css('--up'),
    expense:  css('--dn'),
    savings:  '#4338ca',
    neutral:  css('--gb'),
    glass:    css('--gl'),
    series: ['#4338ca','#0d9488','#7c3aed','#be185d','#f59e0b','#10b981','#ef4444','#3b82f6'],
});

function fmtCurrency(n) {
    return (n == null ? 0 : n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtMonth(ym) {
    if (!ym) return '';
    const [y, m] = ym.split('-');
    return new Date(y, m - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

// ── Sprint 9b: widget configuration maps ──────────────────────────────────────

// Which widgets support chart type switching, and what types are available.
const CHART_TYPE_OPTIONS = {
    income_expense_bar:    ['bar', 'line'],
    expense_donut:         ['donut', 'bar'],
    top_categories_trend:  ['line', 'bar'],
    fixed_vs_variable:     ['bar', 'line'],
    obligations_monthly:   ['bar', 'line'],
    spending_trend:        ['line', 'bar'],
};

const CHART_TYPE_LABELS = {
    bar: 'Bar Chart', line: 'Line Chart', donut: 'Donut Chart',
};

// Which widgets support category / account filters.
const FILTER_SUPPORT = {
    income_expense_bar:     { categories: true,  accounts: true  },
    expense_donut:          { categories: true,  accounts: false },
    recent_transactions:    { categories: true,  accounts: true  },
    potential_to_save:      { categories: false, accounts: true  },
    category_heatmap:       { categories: true,  accounts: false },
    top_categories_trend:   { categories: true,  accounts: false },
    budget_vs_actual:       { categories: true,  accounts: false },
    spending_trend:         { categories: true,  accounts: true  },
    loan_summary:           { categories: false, accounts: false, loans: true },
    loan_trajectory:        { categories: false, accounts: false, loans: true },
    debt_reduction_impact:  { categories: false, accounts: false, loans: true },
    interest_overview:      { categories: false, accounts: false, loans: true },
};

// Sprint 20: per-widget-type list of customizable chart series. `default`
// is a function so it reflects the current theme until an override is
// saved. Dynamic/per-category widgets (expense_donut, category_heatmap,
// top_categories_trend) aren't listed — those already have per-category
// colors via the Categories page.
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

// ── Widget registry ───────────────────────────────────────────────────────────
// Maps widget_type → { title, renderFn, miniMetric }
const WIDGET_REGISTRY = {
    income_expense_bar:     { render: renderIncomeExpenseBar,    mini: d => `Net: RON ${fmtCurrency(d.total_income - d.total_expense)}` },
    expense_donut:          { render: renderExpenseDonut,        mini: d => `Total: RON ${fmtCurrency(d.total)}` },
    recent_transactions:    { render: renderRecentTransactions,  mini: () => 'Recent activity' },
    savings_goals_progress: { render: renderSavingsGoals,        mini: d => `${d.goals.length} active goal${d.goals.length !== 1 ? 's' : ''}` },
    budget_vs_actual:       { render: renderBudgetVsActual,      mini: d => d.budget_name ? `Budget: ${d.budget_name}` : 'No active budget' },
    potential_to_save:      { render: renderPotentialToSave,     mini: d => `Net: RON ${fmtCurrency(d.current_net)}` },
    category_heatmap:       { render: renderCategoryHeatmap,     mini: d => `${d.categories ? d.categories.length : 0} categories` },
    top_categories_trend:   { render: renderTopCategoriesTrend,  mini: d => `Top ${d.series ? d.series.length : 0} categories` },
    fixed_vs_variable:      { render: renderFixedVsVariable,     mini: d => `${d.months ? d.months.length : 0} months` },
    obligations_monthly:    { render: renderObligationsMonthly,  mini: d => `YTD: RON ${fmtCurrency(d.ytd)}` },
    extra_repayments_ytd:   { render: renderExtraRepaymentsYtd,  mini: d => `Extra: RON ${fmtCurrency(d.extra_ytd)}` },
    debt_payments_metric:   { render: renderDebtPaymentsMetric,  mini: d => `Total: RON ${fmtCurrency(d.ytd)}` },
    spending_trend: {
        render: renderSpendingTrend,
        mini: d => (d.anomalies || []).length
            ? `${d.anomalies.length} anomal${d.anomalies.length === 1 ? 'y' : 'ies'} flagged`
            : 'No anomalies',
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
};

// ── Initialisation ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    userId = window.DASHBOARD_USER_ID;
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
    const order = Array.from(grid.children).map(el => el.dataset.id).filter(Boolean);
    if (!order.length) return;

    // VULN: user_id/order trusted as-is server-side, no ownership check (VULN-070/071)
    fetch(`/api/dashboards/${activeDash.id}/widgets/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order, user_id: userId })
    }).catch(() => {});
}

function onDashboardReorder() {
    const container = document.getElementById('dashboardTabs');
    const order = Array.from(container.children).map(el => el.dataset.id).filter(Boolean);
    if (!order.length) return;

    // VULN: user_id/order trusted as-is server-side, no ownership check (VULN-070)
    fetch('/api/dashboards/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order, user_id: userId })
    }).catch(() => {});
}

// ── Stat card reordering (Sprint 53, UI-02, VULN-086) ────────────────────────
async function applyStatCardOrder() {
    try {
        const r = await fetch(`/api/users/stat-card-order?user_id=${userId}`);
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

    // VULN: user_id/order trusted as-is server-side, no ownership check (VULN-086)
    fetch('/api/users/stat-card-order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order, user_id: userId})
    }).catch(() => {});
}

// ── Global stat cards ──────────────────────────────────────────────────────────
async function loadGlobalStats() {
    try {
        const r = await fetch(`/api/transactions/summary?user_id=${userId}`);
        const j = await r.json();
        if (!j.success) return;
        const s = j.summary;
        document.getElementById('statTotalIncome').innerHTML =
            `<span class="amount-positive">RON ${fmtCurrency(s.total_income)}</span>`;
        document.getElementById('statTotalExpenses').innerHTML =
            `<span class="amount-negative">RON ${fmtCurrency(s.total_expenses)}</span>`;
        const bal = s.balance;
        document.getElementById('statBalance').innerHTML =
            `<span class="${bal >= 0 ? 'amount-positive' : 'amount-negative'}">RON ${fmtCurrency(bal)}</span>`;
    } catch (e) {
        console.error('Stats error:', e);
    }

    try {
        const r = await fetch(`/api/accounts/summary?user_id=${userId}`);
        const j = await r.json();
        if (!j.success) return;
        const bb = j.budget_balance;
        document.getElementById('statBudgetBalance').innerHTML =
            `<span class="${bb >= 0 ? 'amount-positive' : 'amount-negative'}">RON ${fmtCurrency(bb)}</span>`;
    } catch (e) {
        console.error('Budget balance error:', e);
    }
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
    const r = await fetch(`/api/transactions/summary?user_id=${userId}`);
    const j = await r.json();
    if (!j.success) return;
    const s = j.summary;
    const bal = s.balance;

    document.getElementById('heroLabel').textContent = 'Current Balance';
    document.getElementById('heroBalance').innerHTML =
        `<span class="${bal >= 0 ? 'amount-positive' : 'amount-negative'}">RON ${fmtCurrency(bal)}</span>`;
    document.getElementById('heroRingLbl').textContent = 'Saved';
    document.getElementById('heroStat1Label').textContent = 'Income';
    document.getElementById('heroStat2Label').textContent = 'Expenses';
    setHeroPill('heroIncome', 'RON ' + fmtCurrency(s.total_income), 'income');
    setHeroPill('heroExpense', 'RON ' + fmtCurrency(s.total_expenses), 'expense');

    setHeroRing(s.total_income > 0 ? (bal / s.total_income) * 100 : 0);
}

async function loadHeroSavingsGoals() {
    const r = await fetch(`/api/reports-data/savings-goals?user_id=${userId}`);
    const j = await r.json();
    const goals = j.success ? (j.data.goals || []) : [];

    const totalCurrent   = goals.reduce((sum, g) => sum + g.current_amount, 0);
    const totalTarget    = goals.reduce((sum, g) => sum + g.target_amount, 0);
    const totalRemaining = goals.reduce((sum, g) => sum + g.remaining, 0);

    document.getElementById('heroLabel').textContent = 'Total Saved';
    document.getElementById('heroBalance').innerHTML =
        `<span class="amount-positive">RON ${fmtCurrency(totalCurrent)}</span>`;
    document.getElementById('heroRingLbl').textContent = 'Funded';
    document.getElementById('heroStat1Label').textContent = 'Active Goals';
    document.getElementById('heroStat2Label').textContent = 'Remaining';
    setHeroPill('heroIncome', String(goals.length));
    setHeroPill('heroExpense', 'RON ' + fmtCurrency(totalRemaining));

    setHeroRing(totalTarget > 0 ? (totalCurrent / totalTarget) * 100 : 0);
}

async function loadHeroSpendingAnalysis() {
    const r = await fetch(`/api/reports-data/expense-distribution?user_id=${userId}&period=1M`);
    const j = await r.json();
    const categories = j.success ? (j.data.categories || []) : [];
    const grandTotal  = j.success ? j.data.total : 0;
    const top = categories[0] || null;

    document.getElementById('heroLabel').textContent = 'Expenses (This Month)';
    document.getElementById('heroBalance').innerHTML =
        `<span class="amount-negative">RON ${fmtCurrency(grandTotal)}</span>`;
    document.getElementById('heroRingLbl').textContent = 'Top Cat';
    document.getElementById('heroStat1Label').textContent = 'Top Category';
    document.getElementById('heroStat2Label').textContent = 'Category Total';
    setHeroPill('heroIncome', top ? top.name : '—');
    setHeroPill('heroExpense', top ? 'RON ' + fmtCurrency(top.total) : '—', 'expense');

    setHeroRing(top ? top.pct : 0);
}

async function loadHeroLoanObligations() {
    const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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

    document.getElementById('heroBalance').innerHTML =
        `<span class="amount-negative">RON ${fmtCurrency(status.current_balance)}</span>`;
    setHeroPill('heroIncome', status.years_remaining != null ? status.years_remaining : '—');
    setHeroPill('heroExpense', status.interest_saved != null ? 'RON ' + fmtCurrency(status.interest_saved) : '—', 'income');

    setHeroRing(loan.principal > 0 ? ((loan.principal - status.current_balance) / loan.principal) * 100 : 0);
}
*/

// ── Dashboard tabs ─────────────────────────────────────────────────────────────
async function initDashboards() {
    try {
        const r = await fetch(`/api/dashboards/list?user_id=${userId}`);
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
        // VULN: innerHTML — Stored XSS via dashboard name
        btn.innerHTML = d.name;
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

    // Update active state locally so the tab highlights immediately
    dashboards.forEach(d => d.is_active = (d.id === dashboardId));
    activeDash = dashboards.find(d => d.id === dashboardId);
    renderTabs();

    // Persist to server (fire-and-forget, VULN: no CSRF)
    fetch(`/api/dashboards/${dashboardId}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    }).catch(() => {});

    await loadDashboard(dashboardId);
}

// ── Widget grid ────────────────────────────────────────────────────────────────
async function loadDashboard(dashboardId) {
    // loadHeroCard() was called here (Release 7); disabled above along
    // with the hero-card feature it drove. See docs/releases/release-07-plan.md.

    const grid = document.getElementById('widgetGrid');
    grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px 0;">
            <div class="glass-spinner" style="margin:0 auto 12px;"></div>
            <span style="color:var(--th);font-size:0.875rem;">Loading widgets…</span>
        </div>`;

    // Destroy existing chart instances to avoid memory leaks
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
            grid.innerHTML = `<div id="widgetGridEmptyState" style="grid-column:1/-1;text-align:center;padding:60px 0;color:var(--th);">
                No widgets configured for this dashboard.</div>`;
            refreshCustomizePanel(widgets);
            return;
        }

        for (const w of widgets) {
            const card = buildWidgetShell(w);
            grid.appendChild(card);
            if (w.is_enabled) {
                loadWidgetData(w);
            }
        }

        refreshCustomizePanel(widgets);
    } catch (e) {
        console.error('Load dashboard error:', e);
    }
}

// ── Widget shell ───────────────────────────────────────────────────────────────
function buildWidgetShell(w) {
    const card = document.createElement('div');
    card.className  = 'glass-card no-hover widget-card';
    card.id         = `widget-${w.id}`;
    card.dataset.id = w.id;
    card.dataset.type = w.widget_type;
    if (!w.is_enabled) card.style.display = 'none';
    if (w.is_minimized) card.classList.add('is-minimized');

    // VULN: custom_title rendered via innerHTML — Stored XSS if title contains script tags
    const displayTitle = w.custom_title || w.title;

    card.innerHTML = `
        <div class="widget-header">
            <div class="widget-title-wrap">
                <span class="widget-drag-handle" title="Drag to reorder">⠿</span>
                <span class="widget-title">${displayTitle}</span>
            </div>
            <div class="widget-controls">
                <div class="period-bar" id="periods-${w.id}">
                    ${['1M','3M','6M','1Y','ALL'].map(p =>
                        `<button class="period-btn${w.time_period === p ? ' active' : ''}"
                                 data-period="${p}"
                                 onclick="changePeriod(${w.id},'${p}')">
                            ${p}
                        </button>`
                    ).join('')}
                </div>
                <button class="widget-minimize-btn" title="Minimize / Expand"
                        onclick="toggleMinimize(${w.id})">
                    <svg id="minIcon-${w.id}" width="14" height="14" viewBox="0 0 16 16" fill="none"
                         stroke="currentColor" stroke-width="2">
                        ${w.is_minimized
                            ? '<polyline points="3,10 8,5 13,10"/>'
                            : '<polyline points="3,6 8,11 13,6"/>'}
                    </svg>
                </button>
                <button class="widget-settings-btn" title="Widget settings"
                        onclick="openWidgetSettingsModal(${w.id})">
                    ⚙
                </button>
                <button class="widget-remove-btn" title="Remove widget permanently"
                        onclick="confirmRemoveWidget(${w.id}, '${w.title.replace(/'/g, "\\'")}')">
                    &times;
                </button>
            </div>
        </div>
        <div class="widget-body" id="wbody-${w.id}"
             style="${w.is_minimized ? 'display:none;' : ''}">
            <div style="text-align:center;padding:32px 0;">
                <div class="glass-spinner" style="margin:0 auto 10px;"></div>
                <span style="font-size:0.8rem;color:var(--th);">Loading…</span>
            </div>
        </div>
        <div class="widget-mini" id="wmini-${w.id}"
             style="${w.is_minimized ? '' : 'display:none;'}">
            <span class="widget-mini-metric" id="wmetric-${w.id}">—</span>
        </div>`;

    return card;
}

// Shared by every loan-scoped widget (loan_summary, loan_trajectory) —
// resolves filter_config.loan_id against the caller's own loan list, falling
// back to the first loan if unset or if the configured loan no longer exists
// (e.g. deleted since the widget was configured).
function resolveTargetLoan(loans, filterConfig) {
    const configuredId = filterConfig?.loan_id;
    return (configuredId != null && loans.find(l => l.id === configuredId)) || loans[0];
}

// ── Widget data loading ────────────────────────────────────────────────────────
async function loadWidgetData(w) {
    const body = document.getElementById(`wbody-${w.id}`);
    if (!body) return;

    const reg = WIDGET_REGISTRY[w.widget_type];
    if (!reg) {
        body.innerHTML = `<p style="color:var(--th);text-align:center;padding:20px 0;font-size:0.85rem;">
            Widget type "${w.widget_type}" is not supported yet.</p>`;
        return;
    }

    try {
        // Sprint 9b: extract filter config and effective chart type
        const filterConfig  = w.filter_config || {};
        const categoryIds   = (filterConfig.category_ids || []).join(',');
        const accountIds    = (filterConfig.account_ids  || []).join(',');
        const effectiveType = w.chart_type || null;

        let data;
        if (w.widget_type === 'recent_transactions') {
            let txUrl = `/api/transactions/list?user_id=${userId}&limit=10`;
            if (w.time_period && w.time_period !== 'ALL') {
                const daysMap = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365 };
                const cutoff = new Date();
                cutoff.setDate(cutoff.getDate() - (daysMap[w.time_period] || 30));
                txUrl += `&date_from=${cutoff.toISOString().split('T')[0]}`;
            }
            // VULN: filter IDs appended without encoding — SQL Injection
            if (categoryIds) txUrl += `&category_id=${categoryIds}`;
            if (accountIds)  txUrl += `&account_id=${accountIds}`;
            const r = await fetch(txUrl);
            const j = await r.json();
            data = j.success ? j.transactions : [];
        } else if (w.widget_type === 'loan_summary') {
            const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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
            const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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
            const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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
            const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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
            const loansRes = await fetch(`/api/loans/list?user_id=${userId}`);
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
            const r = await fetch(`/api/accounts/list?user_id=${userId}`);
            const j = await r.json();
            const included = j.success ? j.accounts.filter(a => a.include_in_budget) : [];
            data = { accounts: included };
        } else {
            let url = `${w.endpoint}?user_id=${userId}&period=${w.time_period}`;
            // VULN: filter IDs appended without encoding — SQL Injection
            if (categoryIds) url += `&category_ids=${categoryIds}`;
            if (accountIds)  url += `&account_ids=${accountIds}`;
            const r = await fetch(url);
            const j = await r.json();
            data = j.success ? j.data : null;
        }

        if (data == null) {
            body.innerHTML = errorHtml('Failed to load data.');
            return;
        }

        // Update mini metric
        const metricEl = document.getElementById(`wmetric-${w.id}`);
        if (metricEl) {
            try { metricEl.textContent = reg.mini(data); } catch (_) {}
        }

        reg.render(w.id, data, effectiveType, w.chart_colors);

    } catch (e) {
        console.error(`Widget ${w.id} load error:`, e);
        if (body) body.innerHTML = errorHtml('Error loading widget data.');
    }
}

function errorHtml(msg) {
    return `<p style="color:var(--dn);text-align:center;padding:20px 0;font-size:0.85rem;">${msg}</p>`;
}

// ── Period change ──────────────────────────────────────────────────────────────
async function changePeriod(widgetId, period) {
    // Update period button highlights
    document.querySelectorAll(`#periods-${widgetId} .period-btn`).forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });

    // Persist state
    await fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_period: period })
    });

    // Reload widget data with new period
    const w = await getWidgetState(widgetId, period);
    if (w) loadWidgetData(w);
}

async function getWidgetState(widgetId, overridePeriod) {
    // Build a lightweight widget descriptor from the current DOM state
    const card = document.getElementById(`widget-${widgetId}`);
    if (!card) return null;
    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const j = await r.json();
    if (!j.success) return null;
    const w = j.widgets.find(x => x.id === widgetId);
    if (w && overridePeriod) w.time_period = overridePeriod;
    return w || null;
}

// ── Minimize / maximize ────────────────────────────────────────────────────────
async function toggleMinimize(widgetId) {
    const body = document.getElementById(`wbody-${widgetId}`);
    const mini = document.getElementById(`wmini-${widgetId}`);
    const icon = document.getElementById(`minIcon-${widgetId}`);
    if (!body || !mini) return;

    const isNowMin = body.style.display !== 'none';   // about to minimize
    const card = document.getElementById(`widget-${widgetId}`);

    body.style.display = isNowMin ? 'none' : '';
    mini.style.display = isNowMin ? ''     : 'none';
    if (card) card.classList.toggle('is-minimized', isNowMin);

    if (icon) {
        icon.innerHTML = isNowMin
            ? '<polyline points="3,10 8,5 13,10"/>'
            : '<polyline points="3,6 8,11 13,6"/>';
    }

    // Persist
    fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_minimized: isNowMin })
    }).catch(() => {});
}

// ── Customize panel ────────────────────────────────────────────────────────────
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
    { type: 'income_expense_bar',     title: 'Income vs Expenses',     desc: 'Monthly income & expense grouped bar chart' },
    { type: 'expense_donut',          title: 'Expense Distribution',    desc: 'Spending breakdown by category — donut chart' },
    { type: 'recent_transactions',    title: 'Recent Transactions',     desc: 'Latest 10 transactions — table view' },
    { type: 'savings_goals_progress', title: 'Savings Goals Progress',  desc: 'Progress bars for each active savings goal' },
    { type: 'budget_vs_actual',       title: 'Budget vs Actual',        desc: 'Budget limit vs actual spend per category' },
    { type: 'potential_to_save',      title: 'Potential to Save',       desc: 'Income minus expenses — metric + trend line' },
    { type: 'category_heatmap',       title: 'Category Heatmap',        desc: 'Month × category spending intensity grid' },
    { type: 'top_categories_trend',   title: 'Top Categories Trend',    desc: 'Top 5 spending categories over time' },
    { type: 'fixed_vs_variable',      title: 'Fixed vs Variable',       desc: 'Fixed vs variable cost split — stacked bar' },
    { type: 'obligations_monthly',    title: 'Obligations Monthly',     desc: 'Financial obligation payments per month' },
    { type: 'extra_repayments_ytd',   title: 'Extra Repayments YTD',    desc: 'Extra debt repayments year-to-date' },
    { type: 'debt_payments_metric',   title: 'Total Debt Payments',     desc: 'Total debt payment metric card' },
    { type: 'spending_trend',         title: 'Spending Trend & Anomalies', desc: 'Monthly spend with a moving-average line, plus categories flagged as unusually high' },
    { type: 'yoy_category_comparison', title: 'Year-over-Year Comparison', desc: 'This year vs last year totals, per category' },
    { type: 'loan_summary',           title: 'Loan Summary',            desc: 'Current balance, installment, payoff date, and savings so far for one loan — pick which one in the widget\'s settings' },
    { type: 'loans_overview',         title: 'All Loans Overview',      desc: 'Balance, payoff date, and savings so far for every loan you\'re tracking, at a glance' },
    { type: 'loan_trajectory',        title: 'Payoff Trajectory',       desc: 'Actual vs Baseline balance over the life of one loan — pick which one in the widget\'s settings' },
    { type: 'debt_reduction_impact',  title: 'Debt Reduction Impact',   desc: 'How much lower your balance is today vs the original plan, plus total extra principal paid, for one loan' },
    { type: 'interest_overview',      title: 'Interest Overview',       desc: 'Bank-confirmed remaining interest ("Dobanda"), current rate, and estimated interest saved for one loan' },
    { type: 'budget_accounts',        title: 'Accounts Included in Budget', desc: 'Balance of every account currently counted toward your budget total' },
];

function refreshCustomizePanel(widgets) {
    const list = document.getElementById('customizeWidgetList');
    list.innerHTML = '';

    // Section 1: Toggle existing widgets
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
            pill.innerHTML = `
                <input type="checkbox" ${w.is_enabled ? 'checked' : ''}
                       onchange="toggleWidgetEnabled(${w.id}, this.checked)">
                <span>${w.title}</span>`;
            toggles.appendChild(pill);
        });
        list.appendChild(toggles);
    }

    // Section 2: Add widget
    const sec2 = document.createElement('div');
    sec2.className = 'customize-section-title';
    sec2.textContent = 'Add widget';
    list.appendChild(sec2);

    const existingTypes = new Set(widgets.map(w => w.widget_type));
    const addGrid = document.createElement('div');
    addGrid.className = 'add-widget-list';

    ALL_WIDGET_META.forEach(meta => {
        const added = existingTypes.has(meta.type);
        const card  = document.createElement('div');
        card.className = 'add-widget-card' + (added ? ' already-added' : '');
        card.innerHTML = `
            <div style="min-width:0;">
                <div class="add-widget-card-name">${meta.title}</div>
                <div style="font-size:0.74rem;color:var(--th);margin-top:2px;">${meta.desc}</div>
            </div>
            <button class="btn btn-secondary" style="font-size:0.74rem;padding:4px 10px;white-space:nowrap;"
                    ${added ? 'disabled' : ''}
                    onclick="addWidgetToDashboard('${meta.type}')">
                ${added ? 'Added' : 'Add'}
            </button>`;
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
// Widget renderers
// =============================================================================

// ── W1: Income vs Expenses bar ─────────────────────────────────────────────────
function renderIncomeExpenseBar(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    body.innerHTML = `<canvas id="chart-${wid}" height="120"></canvas>`;
    const p      = PALETTE();
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
                    { label: 'Income',   data: data.income  || [], borderColor: cIncome,  backgroundColor: cIncome  + '22', tension:0.4, fill:false, borderWidth:2 },
                    { label: 'Expenses', data: data.expense || [], borderColor: cExpense, backgroundColor: cExpense + '22', tension:0.4, fill:false, borderWidth:2 },
                    { label: 'Net',      data: data.net     || [], borderColor: cNet, backgroundColor: cNet + '22', tension:0.4, fill:false, borderWidth:2, borderDash:[4,4] },
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
                    { label: 'Income',   data: data.income  || [], backgroundColor: cIncome  + '66', borderColor: cIncome,  borderWidth:1.5, borderRadius:5 },
                    { label: 'Expenses', data: data.expense || [], backgroundColor: cExpense + '66', borderColor: cExpense, borderWidth:1.5, borderRadius:5 },
                    { label: 'Net',      data: data.net     || [], backgroundColor: cNet + '66', borderColor: cNet, borderWidth:1.5, borderRadius:5, type:'line', tension:0.4, fill:false },
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    }
}

// ── W2: Expense donut ──────────────────────────────────────────────────────────
function renderExpenseDonut(wid, data, chartType) {
    const body = document.getElementById(`wbody-${wid}`);
    if (chartInstances[wid]) chartInstances[wid].destroy();
    const cats = data.categories || [];
    const p    = PALETTE();

    if (chartType === 'bar') {
        body.innerHTML = `<canvas id="chart-${wid}" height="140"></canvas>`;
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'bar',
            data: {
                labels:   cats.map(c => c.name),
                datasets: [{ label: 'Spend', data: cats.map(c => c.total), backgroundColor: cats.map(c => c.color), borderRadius: 5, borderWidth: 0 }]
            },
            options: { ...chartOpts({ prefix: 'RON ' }), indexAxis: 'y' }
        });
    } else {
        body.innerHTML = `<div style="display:flex;justify-content:center;"><canvas id="chart-${wid}" style="max-height:260px;"></canvas></div>`;
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'doughnut',
            data: {
                labels:   cats.map(c => c.name),
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

// ── W3: Recent transactions table ─────────────────────────────────────────────
function renderRecentTransactions(wid, transactions) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!transactions || transactions.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No recent transactions.</p>`;
        return;
    }
    const rows = transactions.slice(0, 10).map(t => {
        const inc = t.type === 'income';
        return `<tr>
            <td style="font-size:0.8rem;color:var(--ts);">${t.transaction_date}</td>
            <td>${inc ? '<span class="glass-badge badge-income">Income</span>' : '<span class="glass-badge badge-expense">Expense</span>'}</td>
            <td style="font-size:0.85rem;">${t.category_name || '<em style="color:var(--th)">—</em>'}</td>
            <td style="font-size:0.85rem;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${t.description || '—'}</td>
            <td class="text-end"><strong class="${inc ? 'amount-positive' : 'amount-negative'}">${inc ? '+' : '-'}${formatMoney(t.amount, t.currency)}</strong></td>
        </tr>`;
    }).join('');
    body.innerHTML = `
        <div style="overflow-x:auto;">
            <table class="glass-table">
                <thead><tr><th>Date</th><th>Type</th><th>Category</th><th>Description</th><th style="text-align:right;">Amount</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        <div style="text-align:right;margin-top:10px;">
            <a href="/transactions" style="font-size:0.78rem;color:var(--ts);">View all transactions →</a>
        </div>`;
}

// ── W4: Savings goals progress ─────────────────────────────────────────────────
function renderSavingsGoals(wid, data) {
    const body  = document.getElementById(`wbody-${wid}`);
    const goals = data.goals || [];
    if (goals.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No active savings goals.</p>`;
        return;
    }
    body.innerHTML = goals.map(g => `
        <div style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:0.88rem;font-weight:600;">${g.name}</span>
                <span style="font-size:0.82rem;color:var(--ts);">RON ${fmtCurrency(g.current_amount)} / RON ${fmtCurrency(g.target_amount)}</span>
            </div>
            <div style="background:var(--gb);border-radius:6px;height:10px;overflow:hidden;">
                <div style="height:100%;width:${Math.min(g.pct,100)}%;background:var(--up);border-radius:6px;transition:width 0.5s ease;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:3px;">
                <span style="font-size:0.75rem;color:var(--th);">${g.pct}% complete</span>
                ${g.target_date ? `<span style="font-size:0.75rem;color:var(--th);">Target: ${g.target_date}</span>` : ''}
            </div>
        </div>`).join('');
}

// ── W5: Budget vs Actual ───────────────────────────────────────────────────────
function renderBudgetVsActual(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const cats = data.categories || [];
    if (cats.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">${data.budget_name ? 'No category limits set.' : 'No active budget.'}</p>`;
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
                { label: 'Budget',  data: cats.map(c => c.budget), backgroundColor: cBudget  + '55', borderColor: cBudget,  borderWidth:1.5, borderRadius:5 },
                { label: 'Actual',  data: cats.map(c => c.actual), backgroundColor: cats.map(c => c.over ? cActualOver + '88' : cActualOk + '88'),
                                    borderColor: cats.map(c => c.over ? cActualOver : cActualOk), borderWidth:1.5, borderRadius:5 },
            ]
        },
        options: chartOpts({ prefix: 'RON ', title: data.budget_name || 'Budget vs Actual' })
    });
}

// ── W6: Potential to save ──────────────────────────────────────────────────────
function renderPotentialToSave(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const net  = data.current_net || 0;
    const pos  = net >= 0;
    const months = (data.months || []).map(fmtMonth);
    const cumulative = data.cumulative || [];
    const latestCumulative = cumulative.length ? cumulative[cumulative.length - 1] : 0;
    const cumPos = latestCumulative >= 0;

    // Compact stat chips instead of one oversized number — matches the
    // Spending Trend widget's style, and leaves more room for the chart.
    const netChipHtml = `<span class="stat-chip ${pos ? 'stat-chip-positive' : 'stat-chip-negative'}">Net this period: ${pos ? '+' : ''}RON ${fmtCurrency(net)}</span>`;
    const cumChipHtml = months.length > 1
        ? `<span class="stat-chip ${cumPos ? 'stat-chip-positive' : 'stat-chip-negative'}">Cumulative: ${cumPos ? '+' : ''}RON ${fmtCurrency(latestCumulative)}</span>`
        : '';

    body.innerHTML = `
        <div class="chip-row">${netChipHtml}${cumChipHtml}</div>
        ${months.length > 1 ? `<canvas id="chart-${wid}" height="90"></canvas>` : ''}`;

    if (months.length > 1) {
        const p = PALETTE();
        const cNet = widgetColor(colors, 'net', () => p.savings);
        const cCumulative = widgetColor(colors, 'cumulative', () => p.income);
        if (chartInstances[wid]) chartInstances[wid].destroy();
        chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    { label: 'Net',        data: data.net || [],        borderColor: cNet, backgroundColor: cNet + '22', tension:0.4, fill:true },
                    { label: 'Cumulative', data: data.cumulative || [],  borderColor: cCumulative,  backgroundColor: 'transparent',    tension:0.4, borderDash:[4,4] }
                ]
            },
            options: chartOpts({ prefix: 'RON ' })
        });
    }
}

// ── W7: Category heatmap ───────────────────────────────────────────────────────
function renderCategoryHeatmap(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    const months = data.months || [];
    const cats   = data.categories || [];
    const matrix = data.matrix || {};
    const maxVal = data.max_value || 1;

    if (cats.length === 0 || months.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No data for heatmap.</p>`;
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
    // Category names still go through ${cat} unescaped into innerHTML —
    // same intentional stored-XSS surface as before, unchanged.
    const CAT_W = 140;
    const DATA_W = 90;
    const CAT_STYLE = 'background:var(--gl);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border:1px solid rgba(255,255,255,0.12);box-shadow:var(--sh);border-radius:0;';
    const totalWidth = CAT_W + months.length * DATA_W;
    const headerCells = months.map(m => `<th style="width:${DATA_W}px;font-size:0.7rem;padding:4px 6px;color:var(--th);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${fmtMonth(m)}</th>`).join('');
    const bodyRows = cats.map(cat => {
        const cells = months.map((_, i) => {
            const val     = (matrix[cat] || [])[i] || 0;
            const opacity = val > 0 ? 0.15 + (val / maxVal) * 0.75 : 0;
            return `<td style="width:${DATA_W}px;text-align:right;padding:4px 8px;font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                        background:rgba(124,58,237,${opacity.toFixed(2)});
                        border-radius:3px;">
                        ${val > 0 ? 'RON ' + fmtCurrency(val) : '—'}
                    </td>`;
        }).join('');
        return `<tr>
            <td title="${cat}" style="font-size:0.78rem;padding:4px 8px;white-space:nowrap;color:var(--tp);font-weight:500;position:sticky;left:0;z-index:3;width:${CAT_W}px;overflow:hidden;text-overflow:ellipsis;${CAT_STYLE}">${cat}</td>
            ${cells}
        </tr>`;
    }).join('');

    body.innerHTML = `
        <div style="overflow-x:auto;overflow-y:auto;max-height:340px;">
            <table style="border-collapse:separate;border-spacing:2px;table-layout:fixed;width:${totalWidth}px;">
                <thead><tr><th style="position:sticky;left:0;z-index:3;width:${CAT_W}px;${CAT_STYLE}"></th>${headerCells}</tr></thead>
                <tbody>${bodyRows}</tbody>
            </table>
        </div>`;
}

// ── W8: Top categories trend ───────────────────────────────────────────────────
function renderTopCategoriesTrend(wid, data, chartType) {
    const body = document.getElementById(`wbody-${wid}`);
    const series = data.series || [];
    if (series.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No data available.</p>`;
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
                label:           s.name,
                data:            s.data,
                borderColor:     s.color || PALETTE().series[i % 8],
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

// ── W9: Fixed vs Variable ──────────────────────────────────────────────────────
function renderFixedVsVariable(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data.months || data.months.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No data available.</p>`;
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
                    { label: 'Fixed',    data: data.fixed    || [], borderColor: cFixed, backgroundColor: cFixed + '22', tension:0.4, fill:false, borderWidth:2 },
                    { label: 'Variable', data: data.variable || [], borderColor: cVariable, backgroundColor: cVariable + '22', tension:0.4, fill:false, borderWidth:2 },
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
                    { label: 'Fixed',    data: data.fixed    || [], backgroundColor: cFixed + '88', borderColor: cFixed, borderWidth:1.5, borderRadius:4, stack:'s' },
                    { label: 'Variable', data: data.variable || [], backgroundColor: cVariable + '88', borderColor: cVariable, borderWidth:1.5, borderRadius:4, stack:'s' },
                ]
            },
            options: { ...chartOpts({ prefix: 'RON ' }), scales: { x: { stacked: true, grid: { color: p.neutral } }, y: { stacked: true, grid: { color: p.neutral }, beginAtZero: true, ticks: { callback: v => 'RON ' + v } } } }
        });
    }
}

// ── W10: Obligations monthly ───────────────────────────────────────────────────
function renderObligationsMonthly(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data.months || data.months.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No obligation transactions found.</p>`;
        return;
    }
    body.innerHTML = `<canvas id="chart-${wid}" height="120"></canvas>`;
    const p    = PALETTE();
    const cObligations = widgetColor(colors, 'obligations', () => p.expense);
    const type = chartType === 'line' ? 'line' : 'bar';
    if (chartInstances[wid]) chartInstances[wid].destroy();
    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type,
        data: {
            labels: data.months.map(fmtMonth),
            datasets: [{
                label: 'Obligations',
                data:  data.totals || [],
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

// ── W11: Extra repayments YTD ──────────────────────────────────────────────────
function renderExtraRepaymentsYtd(wid, data) {
    const body  = document.getElementById(`wbody-${wid}`);
    const extra = data.extra_ytd || 0;
    const ytd   = data.ytd || 0;
    const avg   = data.avg_monthly || 0;
    const pct   = ytd > 0 ? Math.min((extra / ytd) * 100, 100) : 0;
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

// ── W12: Debt payments metric ──────────────────────────────────────────────────
function renderDebtPaymentsMetric(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    const ytd  = data.ytd || 0;
    const avg  = data.avg_monthly || 0;
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

function reconciliationBadgeHtml(reconciliation) {
    const latest = reconciliation && reconciliation.length ? reconciliation[reconciliation.length - 1] : null;
    let dotColor, text;
    if (!latest) {
        dotColor = 'var(--gb)';
        text = 'No bank snapshot yet';
    } else if (Math.abs(latest.delta) < LOAN_RECONCILIATION_TOLERANCE) {
        dotColor = 'var(--up)';
        text = `Reconciled as of ${latest.date}`;
    } else {
        dotColor = 'var(--ac2)';
        const sign = latest.delta > 0 ? '+' : '';
        text = `Drift: ${sign}RON ${fmtCurrency(latest.delta)} (as of ${latest.date})`;
    }
    return `<div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:12px;font-size:0.8rem;">
        <span style="width:8px;height:8px;border-radius:50%;flex-shrink:0;background:${dotColor};"></span>
        <span style="color:var(--ts);">${text}</span>
    </div>`;
}

function principalProgressHtml(principal, currentBalance) {
    const paidPct = Math.max(0, Math.min(100, (1 - currentBalance / principal) * 100));
    return `<div style="margin-top:14px;text-align:left;">
        <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:var(--ts);margin-bottom:4px;">
            <span>${paidPct.toFixed(1)}% of principal paid off</span>
            <span>RON ${fmtCurrency(principal)} original</span>
        </div>
        <div class="progress" style="height:8px;">
            <div class="progress-bar" style="width:${paidPct}%;"></div>
        </div>
    </div>`;
}

function payoffDeltaBarHtml(startDate, baselinePayoffDate, payoffDate, yearsSaved, monthsSaved) {
    const start = new Date(startDate);
    const baselineEnd = new Date(baselinePayoffDate);
    const actualEnd = new Date(payoffDate);
    const baselineDays = (baselineEnd - start) / 86400000;
    const actualDays = (actualEnd - start) / 86400000;
    if (!(baselineDays > 0)) return '';
    const actualPct = Math.max(0, Math.min(100, (actualDays / baselineDays) * 100));
    const rightLabel = yearsSaved != null ? `${yearsSaved} yrs (${monthsSaved} mo) sooner than baseline` : `Baseline: ${baselinePayoffDate}`;
    // Track represents the full Baseline timeline (start → baseline payoff);
    // the fill stops at the Actual payoff instead — the muted gap left over
    // in the track is visually "how much sooner", without needing two
    // overlapping bars to convey the same baseline-vs-actual contrast.
    return `<div style="margin-top:14px;text-align:left;">
        <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:var(--ts);margin-bottom:4px;">
            <span>Payoff: ${payoffDate}</span>
            <span>${rightLabel}</span>
        </div>
        <div class="progress" style="height:8px;">
            <div class="progress-bar bg-success" style="width:${actualPct}%;"></div>
        </div>
    </div>`;
}

function renderLoanTrajectory(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);

    if (!data || data.no_loans) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No loans tracked yet.</p>`;
        return;
    }

    const actualPeriods = data.actual_periods || [];
    const baselinePeriods = data.baseline_periods || [];
    if (!actualPeriods.length && !baselinePeriods.length) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">Not enough data yet to project a trajectory.</p>`;
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
    if (!data || data.no_loans) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No loans tracked yet.</p>`;
        return;
    }

    const headline = data.debt_reduction_vs_baseline != null
        ? `RON ${fmtCurrency(data.debt_reduction_vs_baseline)}`
        : '—';

    const compareRow = (data.baseline_balance_today != null && data.current_balance != null)
        ? `<div style="display:flex;justify-content:space-between;font-size:0.78rem;color:var(--ts);margin-top:16px;padding-top:12px;border-top:1px solid var(--gb);">
            <span>Baseline today: RON ${fmtCurrency(data.baseline_balance_today)}</span>
            <span>Actual today: RON ${fmtCurrency(data.current_balance)}</span>
        </div>`
        : '';

    // VULN: loan_name (user-entered) interpolated via innerHTML, same
    // pattern as every other user-controlled string already rendered this
    // way in this file (category names, custom_title, etc.)
    body.innerHTML = `
        <div style="text-align:center;padding:4px 0;">
            <div style="font-size:0.8rem;color:var(--th);margin-bottom:6px;">${data.loan_name || 'Loan'}</div>
            <div style="font-size:2rem;font-weight:700;color:var(--up);">${headline}</div>
            <div style="font-size:0.85rem;color:var(--ts);margin-top:2px;">less debt than the original plan, as of today</div>
            ${compareRow}
            <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-top:10px;">
                <span style="color:var(--ts);">Total extra paid</span>
                <strong style="font-variant-numeric:tabular-nums;">RON ${fmtCurrency(data.total_extra_paid || 0)}</strong>
            </div>
            <a href="/loans" style="display:inline-block;margin-top:14px;font-size:0.8rem;">View Details →</a>
        </div>`;
}

function renderInterestOverview(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data || data.no_loans) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No loans tracked yet.</p>`;
        return;
    }

    const headline = data.current_total_dobanda != null
        ? `RON ${fmtCurrency(data.current_total_dobanda)}`
        : '—';
    const headlineSub = data.current_total_dobanda != null
        ? `total interest remaining, per bank snapshot on ${data.dobanda_snapshot_date}`
        : 'Log a bank snapshot with "Remaining Total Interest" filled in to see this';

    const rateRow = data.current_rate_pct != null
        ? `<div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-top:16px;padding-top:12px;border-top:1px solid var(--gb);">
            <span style="color:var(--ts);">Current rate</span>
            <strong style="font-variant-numeric:tabular-nums;">${data.current_rate_pct}%</strong>
        </div>`
        : '';

    const savedRow = data.dobanda_saved_estimate != null
        ? `<div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-top:10px;">
            <span style="color:var(--ts);">Estimated interest saved</span>
            <strong style="font-variant-numeric:tabular-nums;color:var(--up);">RON ${fmtCurrency(data.dobanda_saved_estimate)}</strong>
        </div>`
        : '';

    // VULN: loan_name (user-entered) interpolated via innerHTML, same
    // pattern as every other user-controlled string already rendered this
    // way in this file (category names, custom_title, etc.)
    body.innerHTML = `
        <div style="text-align:center;padding:4px 0;">
            <div style="font-size:0.8rem;color:var(--th);margin-bottom:6px;">${data.loan_name || 'Loan'}</div>
            <div style="font-size:2rem;font-weight:700;color:var(--tp);">${headline}</div>
            <div style="font-size:0.85rem;color:var(--ts);margin-top:2px;">${headlineSub}</div>
            ${rateRow}
            ${savedRow}
            <a href="/loans" style="display:inline-block;margin-top:14px;font-size:0.8rem;">View Details →</a>
        </div>`;
}

function renderBudgetAccounts(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data || !data.accounts || data.accounts.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No accounts are currently included in the budget.</p>`;
        return;
    }

    // VULN: account name (user-entered) interpolated via innerHTML, same
    // pattern as every other user-controlled string already rendered this
    // way in this file (category names, custom_title, etc.)
    const rows = data.accounts.map(acc => {
        const positive = acc.current_balance >= 0;
        return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--gb);">
            <div>
                <div style="font-weight:600;font-size:0.9rem;">${acc.name}</div>
                <small style="color:var(--ts);text-transform:capitalize;">${(acc.type || '').replace('_', ' ')}</small>
            </div>
            <div style="font-weight:700;font-variant-numeric:tabular-nums;color:${positive ? 'var(--up)' : 'var(--dn)'};">
                ${acc.currency} ${fmtCurrency(acc.current_balance)}
            </div>
        </div>`;
    }).join('');

    body.innerHTML = `${rows}<a href="/accounts" style="display:inline-block;margin-top:12px;font-size:0.8rem;">View Accounts →</a>`;
}

function renderLoanSummary(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data || data.no_loans) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No loans tracked yet.</p>`;
        return;
    }
    const savedLine = (data.years_saved != null && data.interest_saved != null)
        ? `<div style="font-size:0.85rem;color:var(--up);margin-top:6px;">${data.years_saved} yrs (${data.months_saved} mo) / RON ${fmtCurrency(data.interest_saved)} saved</div>`
        : '';
    const principalHtml = (data.principal && data.current_balance != null)
        ? principalProgressHtml(data.principal, data.current_balance) : '';
    const deltaBarHtml = (data.start_date && data.baseline_payoff_date && data.payoff_date)
        ? payoffDeltaBarHtml(data.start_date, data.baseline_payoff_date, data.payoff_date, data.years_saved, data.months_saved) : '';
    // VULN: loan_name (user-entered) interpolated via innerHTML, same
    // pattern as every other user-controlled string already rendered this
    // way in this file (category names, custom_title, etc.)
    body.innerHTML = `
        <div style="text-align:center;padding:4px 0;">
            <div style="font-size:0.8rem;color:var(--th);margin-bottom:6px;">${data.loan_name || 'Loan'}</div>
            <div style="font-size:2.2rem;font-weight:700;color:var(--tp);">${data.current_balance != null ? 'RON ' + fmtCurrency(data.current_balance) : '—'}</div>
            ${savedLine}
            ${reconciliationBadgeHtml(data.reconciliation || [])}
            ${principalHtml}
            ${deltaBarHtml}
            <a href="/loans" style="display:inline-block;margin-top:14px;font-size:0.8rem;">View Details →</a>
        </div>`;
}

function renderLoansOverview(wid, data) {
    const body = document.getElementById(`wbody-${wid}`);
    if (!data || data.no_loans || !data.loans || data.loans.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No loans tracked yet.</p>`;
        return;
    }
    // VULN: loan_name (user-entered) interpolated via innerHTML, same
    // pattern as renderLoanSummary and every other user-controlled string
    // already rendered this way in this file.
    const rows = data.loans.map(loan => {
        const savedLine = (loan.years_saved != null && loan.interest_saved != null)
            ? `<small style="color:var(--up);font-variant-numeric:tabular-nums;">${loan.years_saved} yrs (${loan.months_saved} mo) saved</small>`
            : '';
        return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--gb);">
            <div>
                <div style="font-weight:600;font-size:0.9rem;">${loan.loan_name || 'Loan'}</div>
                <small style="color:var(--ts);">${loan.payoff_date ? 'Payoff: ' + loan.payoff_date : 'Payoff date unavailable'}</small>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:700;font-variant-numeric:tabular-nums;">${loan.current_balance != null ? 'RON ' + fmtCurrency(loan.current_balance) : '—'}</div>
                ${savedLine}
            </div>
        </div>`;
    }).join('');
    body.innerHTML = `${rows}<a href="/loans" style="display:inline-block;margin-top:12px;font-size:0.8rem;">View Details →</a>`;
}

// ── W13: Spending trend & anomalies (Sprint 20) ────────────────────────────────
function renderSpendingTrend(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);

    // Anomaly alerts shown first (compact chips) so they're visible without
    // scrolling the widget — moved above the chart per user feedback.
    // VULN: category names from anomalies rendered via innerHTML — Stored XSS
    // (consistent with this version's existing pattern for custom_title etc.)
    const anomalies = data.anomalies || [];
    const alertHtml = anomalies.length
        ? anomalies.map(a => `<span class="anomaly-chip" title="RON ${fmtCurrency(a.current)} vs 3-month avg RON ${fmtCurrency(a.average)}">${a.category} +${a.pct_above}%</span>`).join('')
        : `<span class="anomaly-chip anomaly-chip-clear">No anomalies</span>`;
    body.innerHTML = `<div class="chip-row">${alertHtml}</div><canvas id="chart-${wid}" height="120"></canvas>`;

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

    chartInstances[wid] = new Chart(document.getElementById(`chart-${wid}`).getContext('2d'), {
        type,
        data: { labels, datasets: [totalsDataset, avgDataset] },
        options: chartOpts({ prefix: 'RON ' })
    });
}

// ── W14: Year-over-year comparison (Sprint 20) ─────────────────────────────────
function renderYoyComparison(wid, data, chartType, colors) {
    const body = document.getElementById(`wbody-${wid}`);
    const cats = data.categories || [];
    if (cats.length === 0) {
        body.innerHTML = `<p style="text-align:center;color:var(--th);padding:20px 0;font-size:0.85rem;">No expense data yet for this year or last year.</p>`;
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

// ── Dashboard CRUD ─────────────────────────────────────────────────────────────

function setupDashboardModal() {
    document.getElementById('newDashboardBtn').addEventListener('click', openCreateDashboardModal);
    document.getElementById('dashModalSave').addEventListener('click', saveDashboardModal);
    // Allow Enter key to submit
    document.getElementById('dashModalName').addEventListener('keydown', e => {
        if (e.key === 'Enter') saveDashboardModal();
    });
}

function openCreateDashboardModal() {
    document.getElementById('dashboardModalTitle').textContent = 'New Dashboard';
    document.getElementById('dashModalId').value   = '';
    document.getElementById('dashModalName').value = '';
    document.getElementById('dashModalDesc').value = '';
    new bootstrap.Modal(document.getElementById('dashboardModal')).show();
    setTimeout(() => document.getElementById('dashModalName').focus(), 300);
}

function openEditDashboardModal(dashboardId) {
    const dash = dashboards.find(d => d.id === dashboardId);
    if (!dash) return;
    document.getElementById('dashboardModalTitle').textContent = 'Edit Dashboard';
    document.getElementById('dashModalId').value   = dashboardId;
    document.getElementById('dashModalName').value = dash.name;
    document.getElementById('dashModalDesc').value = dash.description || '';
    new bootstrap.Modal(document.getElementById('dashboardModal')).show();
    setTimeout(() => document.getElementById('dashModalName').focus(), 300);
}

async function saveDashboardModal() {
    const id          = document.getElementById('dashModalId').value;
    const name        = document.getElementById('dashModalName').value.trim();
    const description = document.getElementById('dashModalDesc').value.trim();

    if (!name) {
        document.getElementById('dashModalName').classList.add('is-invalid');
        document.getElementById('dashModalName').focus();
        return;
    }
    document.getElementById('dashModalName').classList.remove('is-invalid');

    const modalEl = document.getElementById('dashboardModal');

    if (id) {
        // Edit mode
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
        }
    } else {
        // Create mode
        const r = await fetch('/api/dashboards/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, name, description })
        });
        const j = await r.json();
        if (j.success) {
            bootstrap.Modal.getInstance(modalEl).hide();
            await initDashboards();
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
        html: `<span style="color:var(--ts);">Delete <strong>${dash.name}</strong> and its <strong>${widgetCount}</strong> widget${widgetCount !== 1 ? 's' : ''}?<br>This cannot be undone.</span>`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        background: 'var(--bg)',
        color: 'var(--tp)',
        confirmButtonColor: '#ef4444',
    });
    if (!result.isConfirmed) return;

    const r = await fetch(`/api/dashboards/${dashboardId}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const j = await r.json();
    if (!j.success) return;

    dashboards = dashboards.filter(d => d.id !== dashboardId);
    const next = dashboards[0];
    if (next) {
        dashboards.forEach(d => d.is_active = (d.id === next.id));
        activeDash = next;
        renderTabs();
        await loadDashboard(next.id);
        fetch(`/api/dashboards/${next.id}/activate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        }).catch(() => {});
    } else {
        activeDash = null;
        renderTabs();
        document.getElementById('widgetGrid').innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:60px 0;color:var(--th);">
                No dashboards. Click <strong>+</strong> to create one.
            </div>`;
        document.getElementById('customizeWidgetList').innerHTML = '';
    }
}

// ── Widget settings modal ──────────────────────────────────────────────────────

function setupWidgetSettingsModal() {
    document.getElementById('wsModalSave').addEventListener('click', saveWidgetSettings);
}

async function openWidgetSettingsModal(widgetId) {
    // Fetch latest widget state from server
    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (!wj.success) return;
    const w = wj.widgets.find(x => x.id === widgetId);
    if (!w) return;

    document.getElementById('wsWidgetId').value = widgetId;
    document.getElementById('wsTitle').value = w.custom_title || '';

    // Chart type section
    const ctSection = document.getElementById('wsChartTypeSection');
    const ctPicker  = document.getElementById('wsChartTypePicker');
    const typeOpts  = CHART_TYPE_OPTIONS[w.widget_type];
    if (typeOpts) {
        ctSection.style.display = '';
        ctPicker.innerHTML = '';
        const activeType = w.chart_type || typeOpts[0];
        typeOpts.forEach(t => {
            const btn = document.createElement('button');
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

    // Category filter section
    const catSection = document.getElementById('wsCategorySection');
    const catList    = document.getElementById('wsCategoryList');
    const filterSupport = FILTER_SUPPORT[w.widget_type] || {};
    if (filterSupport.categories) {
        catSection.style.display = '';
        catList.innerHTML = '<span style="font-size:0.8rem;color:var(--th);">Loading…</span>';
        try {
            const cr = await fetch(`/api/categories/list?user_id=${userId}`);
            const cj = await cr.json();
            const cats = cj.success ? cj.categories : [];
            const selectedIds = new Set((w.filter_config?.category_ids || []));
            catList.innerHTML = '';
            cats.forEach(c => {
                const label = document.createElement('label');
                label.className = 'filter-check-item';
                label.innerHTML = `<input type="checkbox" value="${c.id}" ${selectedIds.has(c.id) ? 'checked' : ''}><span>${c.name}</span>`;
                catList.appendChild(label);
            });
        } catch (_) { catList.innerHTML = '<span style="color:var(--dn);font-size:0.8rem;">Failed to load categories.</span>'; }
    } else {
        catSection.style.display = 'none';
    }

    // Account filter section
    const accSection = document.getElementById('wsAccountSection');
    const accList    = document.getElementById('wsAccountList');
    if (filterSupport.accounts) {
        accSection.style.display = '';
        accList.innerHTML = '<span style="font-size:0.8rem;color:var(--th);">Loading…</span>';
        try {
            const ar = await fetch(`/api/accounts/list?user_id=${userId}`);
            const aj = await ar.json();
            const accs = aj.success ? aj.accounts : [];
            const selectedIds = new Set((w.filter_config?.account_ids || []));
            accList.innerHTML = '';
            accs.forEach(a => {
                const label = document.createElement('label');
                label.className = 'filter-check-item';
                label.innerHTML = `<input type="checkbox" value="${a.id}" ${selectedIds.has(a.id) ? 'checked' : ''}><span>${a.name}</span>`;
                accList.appendChild(label);
            });
        } catch (_) { accList.innerHTML = '<span style="color:var(--dn);font-size:0.8rem;">Failed to load accounts.</span>'; }
    } else {
        accSection.style.display = 'none';
    }

    // Loan filter section (Sprint 33 follow-up)
    const loanSection = document.getElementById('wsLoanSection');
    const loanSelect  = document.getElementById('wsLoanSelect');
    if (filterSupport.loans) {
        loanSection.style.display = '';
        loanSelect.innerHTML = '<option>Loading…</option>';
        try {
            const lr = await fetch(`/api/loans/list?user_id=${userId}`);
            const lj = await lr.json();
            const loans = lj.success ? lj.loans : [];
            const selectedId = w.filter_config?.loan_id;
            loanSelect.innerHTML = `<option value="">${loans.length ? 'First loan (default)' : 'No loans yet'}</option>`;
            loans.forEach(l => {
                const selected = selectedId != null && String(l.id) === String(selectedId) ? 'selected' : '';
                loanSelect.innerHTML += `<option value="${l.id}" ${selected}>${l.name}</option>`;
            });
        } catch (_) { loanSelect.innerHTML = '<option>Failed to load loans</option>'; }
    } else {
        loanSection.style.display = 'none';
    }

    // Color picker section (Sprint 20)
    const colorSection = document.getElementById('wsColorSection');
    const colorList = document.getElementById('wsColorList');
    const slots = COLOR_SLOTS[w.widget_type];
    if (slots) {
        colorSection.style.display = '';
        colorList.innerHTML = '';
        const overrides = w.chart_colors || {};
        slots.forEach(slot => {
            const defaultValue = slot.default();
            const value = overrides[slot.key] || defaultValue;
            const row = document.createElement('div');
            row.className = 'color-picker-item';
            row.dataset.colorKey = slot.key;
            row.dataset.defaultValue = defaultValue;
            row.innerHTML = `
                <span class="color-picker-item-label">${slot.label}</span>
                <div class="color-picker-item-controls">
                    <input type="color" value="${value}">
                    <button type="button" class="color-picker-reset-btn">Reset</button>
                </div>`;
            row.querySelector('.color-picker-reset-btn').addEventListener('click', () => {
                row.querySelector('input[type="color"]').value = defaultValue;
            });
            colorList.appendChild(row);
        });
    } else {
        colorSection.style.display = 'none';
    }

    new bootstrap.Modal(document.getElementById('widgetSettingsModal')).show();
}

async function saveWidgetSettings() {
    const widgetId = parseInt(document.getElementById('wsWidgetId').value);

    const customTitle = document.getElementById('wsTitle').value.trim() || null;

    // Chart type (null if section hidden or default selected)
    const activeCTBtn = document.querySelector('#wsChartTypePicker .chart-type-btn.active');
    const chartType   = activeCTBtn ? activeCTBtn.dataset.type : null;

    // Filters
    const categoryIds = Array.from(document.querySelectorAll('#wsCategoryList input:checked')).map(cb => parseInt(cb.value));
    const accountIds  = Array.from(document.querySelectorAll('#wsAccountList input:checked')).map(cb => parseInt(cb.value));
    const filterConfig = {};
    if (categoryIds.length) filterConfig.category_ids = categoryIds;
    if (accountIds.length)  filterConfig.account_ids  = accountIds;

    // Guarded by the section's own visibility (not just a truthy value) —
    // #wsLoanSelect is a single shared element across widget types, so its
    // .value can still hold a stale selection from a previously-open widget
    // that didn't support a loan filter at all.
    const loanSection = document.getElementById('wsLoanSection');
    const loanSelect  = document.getElementById('wsLoanSelect');
    if (loanSection && loanSection.style.display !== 'none' && loanSelect && loanSelect.value) {
        filterConfig.loan_id = parseInt(loanSelect.value);
    }

    const filterConfigToSend = Object.keys(filterConfig).length ? filterConfig : null;

    // Colors — only send ones actually changed from their default
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
            custom_title:  customTitle,
            chart_type:    chartType,
            filter_config: filterConfigToSend,
            chart_colors:  chartColorsToSend,
        })
    });
    const j = await r.json();
    if (!j.success) return;

    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('widgetSettingsModal')).hide();

    // Reload widget with new settings — fetch updated state from server
    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (!wj.success) return;
    const updatedW = wj.widgets.find(x => x.id === widgetId);
    if (!updatedW) return;

    // Update the card title in the DOM
    // VULN: innerHTML — Stored XSS via custom_title
    const titleEl = document.querySelector(`#widget-${widgetId} .widget-title`);
    if (titleEl) titleEl.innerHTML = updatedW.custom_title || updatedW.title;

    // Re-render widget data
    if (updatedW.is_enabled) loadWidgetData(updatedW);
}

// ── Widget add / remove ────────────────────────────────────────────────────────

async function addWidgetToDashboard(widgetType) {
    if (!activeDash) return;

    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widget_type: widgetType })
    });
    const j = await r.json();
    if (j.success && j.widget) {
        const w    = j.widget;
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

        // Refresh customize panel to mark widget as added
        const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
        const wj = await wr.json();
        if (wj.success) refreshCustomizePanel(wj.widgets);
    }
}

async function confirmRemoveWidget(widgetId, widgetTitle) {
    const result = await Swal.fire({
        title: 'Remove Widget?',
        html: `<span style="color:var(--ts);">Remove <strong>${widgetTitle}</strong> from this dashboard?<br>This cannot be undone.</span>`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Remove',
        cancelButtonText: 'Cancel',
        background: 'var(--bg)',
        color: 'var(--tp)',
        confirmButtonColor: '#ef4444',
    });
    if (!result.isConfirmed) return;

    const r = await fetch(`/api/dashboards/${activeDash.id}/widgets/${widgetId}/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const j = await r.json();
    if (!j.success) return;

    const card = document.getElementById(`widget-${widgetId}`);
    if (card) card.remove();
    if (chartInstances[widgetId]) {
        chartInstances[widgetId].destroy();
        delete chartInstances[widgetId];
    }

    // Refresh customize panel
    const wr = await fetch(`/api/dashboards/${activeDash.id}/widgets`);
    const wj = await wr.json();
    if (wj.success) refreshCustomizePanel(wj.widgets);
}

// ── Shared chart options ───────────────────────────────────────────────────────
function chartOpts({ prefix = '', title = '' } = {}) {
    const p = PALETTE();
    return {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { display: true, position: 'top', labels: { padding: 12, font: { size: 11 } } },
            title:  title ? { display: true, text: title, font: { size: 12 } } : { display: false },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${prefix}${fmtCurrency(ctx.parsed.y ?? ctx.parsed)}` } }
        },
        scales: {
            x: { grid: { color: p.neutral } },
            y: { beginAtZero: true, grid: { color: p.neutral }, ticks: { callback: v => prefix + fmtCurrency(v) } }
        }
    };
}
