"""
Aura Financial Tracker - Secure Version
DashboardWidget Model
Sprint 14: Export/Import + Reports + Multi-Dashboard System

Security properties (contrast with vulnerable-version/models/dashboard_widget.py):
- All queries parameterized — no f-string SQL anywhere
- dashboard_widgets has no user_id column of its own, so every query that
  touches a widget_id JOINs back to dashboards and checks d.user_id = %s —
  vulnerable-version's equivalent methods accept dashboard_id/widget_id with
  no ownership check at all (IDOR)
- widget_type and time_period are validated against a whitelist before being
  written (in addition to the schema's CHECK constraints — defense in depth)
- filter_config is bound as a normal parameter (json.dumps'd string into a
  JSON column) rather than string-interpolated via CAST(...) — vulnerable's
  version can still be broken out of with a crafted category_ids payload
- custom_title is stored as-is (length-capped, parameterized) but is always
  rendered with textContent on the frontend, never innerHTML — vulnerable's
  dashboard.js renders it via innerHTML, a stored-XSS vector (VULN-047/056)
"""

import json
import re

# Sprint 20: per-series color overrides, one hex string per COLOR_SLOTS key
# (frontend-defined per widget_type). Validated as strict 6-digit hex so a
# stored value can never be anything but a Chart.js-safe color string.
_HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


WIDGET_TITLES = {
    'income_expense_bar':     'Income vs Expenses',
    'expense_donut':          'Expense Distribution',
    'recent_transactions':    'Recent Transactions',
    'savings_goals_progress': 'Savings Goals Progress',
    'budget_vs_actual':       'Budget vs Actual',
    'potential_to_save':      'Potential to Save',
    'category_heatmap':       'Category Heatmap',
    'top_categories_trend':   'Top Categories Trend',
    'fixed_vs_variable':      'Fixed vs Variable',
    'obligations_monthly':    'Obligations Monthly',
    'extra_repayments_ytd':   'Extra Repayments YTD',
    'debt_payments_metric':   'Total Debt Payments',
    'spending_trend':         'Spending Trend & Anomalies',
    'yoy_category_comparison': 'Year-over-Year Comparison',
    'loan_summary':           'Loan Summary',
    'loans_overview':         'All Loans Overview',
    'loan_trajectory':        'Payoff Trajectory',
    'debt_reduction_impact':  'Debt Reduction Impact',
    'interest_overview':      'Interest Overview',
    'budget_accounts':        'Accounts Included in Budget',
}

WIDGET_DEFAULT_PERIODS = {
    'income_expense_bar':     '6M',
    'expense_donut':          '1M',
    'recent_transactions':    '1M',
    'savings_goals_progress': '1Y',
    'budget_vs_actual':       '1M',
    'potential_to_save':      '1M',
    'category_heatmap':       '1Y',
    'top_categories_trend':   '6M',
    'fixed_vs_variable':      '3M',
    'obligations_monthly':    '1Y',
    'extra_repayments_ytd':   '1Y',
    'debt_payments_metric':   '1Y',
    'spending_trend':         '6M',
    'yoy_category_comparison': 'ALL',
    'loan_summary':           'ALL',
    'loans_overview':         'ALL',
    'loan_trajectory':        'ALL',
    'debt_reduction_impact':  'ALL',
    'interest_overview':      'ALL',
    'budget_accounts':        'ALL',
}

WIDGET_ENDPOINTS = {
    'income_expense_bar':     '/api/reports-data/income-expense',
    'expense_donut':          '/api/reports-data/expense-distribution',
    'recent_transactions':    '/api/transactions/list',
    'savings_goals_progress': '/api/reports-data/savings-goals',
    'budget_vs_actual':       '/api/reports-data/budget-vs-actual',
    'potential_to_save':      '/api/reports-data/potential-to-save',
    'category_heatmap':       '/api/reports-data/category-heatmap',
    'top_categories_trend':   '/api/reports-data/top-categories',
    'fixed_vs_variable':      '/api/reports-data/fixed-variable',
    'obligations_monthly':    '/api/reports-data/obligations',
    'extra_repayments_ytd':   '/api/reports-data/obligations',
    'debt_payments_metric':   '/api/reports-data/obligations',
    'spending_trend':         '/api/reports-data/spending-trend',
    'yoy_category_comparison': '/api/reports-data/yoy-comparison',
    'loan_summary':           '/api/loans/list',
    'loans_overview':         '/api/loans/list',
    'loan_trajectory':        '/api/loans/list',
    'debt_reduction_impact':  '/api/loans/list',
    'interest_overview':      '/api/loans/list',
    'budget_accounts':        '/api/accounts/list',
}

ALLOWED_WIDGET_TYPES = set(WIDGET_TITLES.keys())
ALLOWED_TIME_PERIODS = {'1M', '3M', '6M', '1Y', 'ALL'}
ALLOWED_CHART_TYPES = {'bar', 'line', 'donut'}

_UNSET = object()


class DashboardWidget:
    def __init__(self, id=None, dashboard_id=None, widget_type=None,
                 is_enabled=True, is_minimized=False, time_period='1M',
                 position=0, created_at=None, updated_at=None,
                 chart_type=None, filter_config=None, custom_title=None,
                 chart_colors=None):
        self.id = id
        self.dashboard_id = dashboard_id
        self.widget_type = widget_type
        self.is_enabled = is_enabled
        self.is_minimized = is_minimized
        self.time_period = time_period
        self.position = position
        self.created_at = created_at
        self.updated_at = updated_at
        self.chart_type = chart_type
        self.filter_config = filter_config
        self.custom_title = custom_title
        self.chart_colors = chart_colors

    @property
    def title(self):
        return WIDGET_TITLES.get(self.widget_type, self.widget_type)

    @property
    def endpoint(self):
        return WIDGET_ENDPOINTS.get(self.widget_type, '')

    @staticmethod
    def get_by_dashboard(mysql, dashboard_id, user_id):
        """Ownership verified via JOIN to dashboards.user_id — returns [] for a
        dashboard_id that doesn't belong to user_id (indistinguishable from empty)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT dw.id, dw.dashboard_id, dw.widget_type, dw.is_enabled, dw.is_minimized, "
                "dw.time_period, dw.position, dw.created_at, dw.updated_at, "
                "dw.chart_type, dw.filter_config, dw.custom_title, dw.chart_colors "
                "FROM dashboard_widgets dw "
                "JOIN dashboards d ON dw.dashboard_id = d.id "
                "WHERE dw.dashboard_id = %s AND d.user_id = %s "
                "ORDER BY dw.position ASC",
                (dashboard_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [DashboardWidget._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_by_id(mysql, widget_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT dw.id, dw.dashboard_id, dw.widget_type, dw.is_enabled, dw.is_minimized, "
                "dw.time_period, dw.position, dw.created_at, dw.updated_at, "
                "dw.chart_type, dw.filter_config, dw.custom_title, dw.chart_colors "
                "FROM dashboard_widgets dw "
                "JOIN dashboards d ON dw.dashboard_id = d.id "
                "WHERE dw.id = %s AND d.user_id = %s",
                (widget_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return DashboardWidget._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def update_state(mysql, widget_id, user_id, is_minimized=None, time_period=None, is_enabled=None,
                      chart_type=_UNSET, filter_config=_UNSET, custom_title=_UNSET,
                      chart_colors=_UNSET):
        """Updates one or more state fields on a widget owned by user_id.
        chart_type/filter_config/custom_title/chart_colors use the _UNSET
        sentinel so an explicit None (clear the field) can be told apart
        from "not supplied"."""
        parts = []
        params = []

        if is_minimized is not None:
            parts.append("is_minimized = %s")
            params.append(bool(is_minimized))
        if time_period is not None:
            if time_period not in ALLOWED_TIME_PERIODS:
                return False
            parts.append("time_period = %s")
            params.append(time_period)
        if is_enabled is not None:
            parts.append("is_enabled = %s")
            params.append(bool(is_enabled))

        if chart_type is not _UNSET:
            if chart_type and chart_type not in ALLOWED_CHART_TYPES:
                return False
            parts.append("chart_type = %s")
            params.append(chart_type or None)

        if filter_config is not _UNSET:
            parts.append("filter_config = %s")
            params.append(json.dumps(filter_config) if filter_config else None)

        if custom_title is not _UNSET:
            custom_title = (custom_title or '').strip() or None
            if custom_title and len(custom_title) > 150:
                return False
            parts.append("custom_title = %s")
            params.append(custom_title)

        if chart_colors is not _UNSET:
            if chart_colors:
                if not isinstance(chart_colors, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) and _HEX_COLOR_RE.match(v)
                    for k, v in chart_colors.items()
                ):
                    return False
                parts.append("chart_colors = %s")
                params.append(json.dumps(chart_colors))
            else:
                parts.append("chart_colors = NULL")

        try:
            cursor = mysql.connection.cursor()
            # Ownership must be checked independently of whether the update itself
            # is a no-op — rowcount stays 0 both when the widget isn't owned by
            # user_id AND when the new values match the existing row, so it can't
            # be used on its own to detect an ownership failure.
            cursor.execute(
                "SELECT dw.id FROM dashboard_widgets dw "
                "JOIN dashboards d ON dw.dashboard_id = d.id "
                "WHERE dw.id = %s AND d.user_id = %s",
                (widget_id, user_id)
            )
            if not cursor.fetchone():
                cursor.close()
                return False

            if not parts:
                cursor.close()
                return True

            set_clause = ', '.join(parts)
            params.extend([widget_id, user_id])
            cursor.execute(
                f"UPDATE dashboard_widgets dw "
                f"JOIN dashboards d ON dw.dashboard_id = d.id "
                f"SET {set_clause} "
                f"WHERE dw.id = %s AND d.user_id = %s",
                tuple(params)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def add_to_dashboard(mysql, dashboard_id, user_id, widget_type):
        """Adds a widget to dashboard_id — only if it belongs to user_id and
        widget_type is a recognised type."""
        if widget_type not in ALLOWED_WIDGET_TYPES:
            return None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id FROM dashboards WHERE id = %s AND user_id = %s",
                (dashboard_id, user_id)
            )
            if not cursor.fetchone():
                cursor.close()
                return None

            cursor.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM dashboard_widgets WHERE dashboard_id = %s",
                (dashboard_id,)
            )
            next_pos = cursor.fetchone()[0]
            time_period = WIDGET_DEFAULT_PERIODS.get(widget_type, '1M')
            cursor.execute(
                "INSERT INTO dashboard_widgets "
                "(dashboard_id, widget_type, is_enabled, is_minimized, time_period, position) "
                "VALUES (%s, %s, TRUE, FALSE, %s, %s)",
                (dashboard_id, widget_type, time_period, next_pos)
            )
            widget_id = cursor.lastrowid
            mysql.connection.commit()
            cursor.close()
            return widget_id
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def reorder(mysql, dashboard_id, user_id, ordered_ids):
        """
        Sprint 19: bulk reorder within a single dashboard. Every id in
        ordered_ids must belong to dashboard_id AND dashboard_id must belong
        to user_id — checked up front, before any UPDATE runs. Rejects the
        whole batch if any id is missing or belongs to a different
        dashboard, so a payload can't be used to silently reassign a
        widget's position from outside the dashboard it's shown on.
        """
        if not ordered_ids:
            return True, "Nothing to reorder"
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id FROM dashboards WHERE id = %s AND user_id = %s",
                (dashboard_id, user_id)
            )
            if not cursor.fetchone():
                cursor.close()
                return False, "Dashboard not found or you don't have permission"

            placeholders = ', '.join(['%s'] * len(ordered_ids))
            cursor.execute(
                f"SELECT COUNT(*) FROM dashboard_widgets WHERE dashboard_id = %s AND id IN ({placeholders})",
                tuple([dashboard_id] + ordered_ids)
            )
            owned_count = cursor.fetchone()[0]
            if owned_count != len(ordered_ids):
                cursor.close()
                return False, "One or more widgets don't belong to this dashboard"

            for index, widget_id in enumerate(ordered_ids):
                cursor.execute(
                    "UPDATE dashboard_widgets SET position = %s WHERE id = %s AND dashboard_id = %s",
                    (index, widget_id, dashboard_id)
                )
            mysql.connection.commit()
            cursor.close()
            return True, "Widget order updated"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not reorder widgets"

    @staticmethod
    def remove(mysql, widget_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE dw FROM dashboard_widgets dw "
                "JOIN dashboards d ON dw.dashboard_id = d.id "
                "WHERE dw.id = %s AND d.user_id = %s",
                (widget_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def _from_row(row):
        filter_config = row[10]
        if isinstance(filter_config, str):
            try:
                filter_config = json.loads(filter_config)
            except (ValueError, TypeError):
                filter_config = None
        chart_colors = row[12] if len(row) > 12 else None
        if isinstance(chart_colors, str):
            try:
                chart_colors = json.loads(chart_colors)
            except (ValueError, TypeError):
                chart_colors = None
        return DashboardWidget(
            id=row[0],
            dashboard_id=row[1],
            widget_type=row[2],
            is_enabled=bool(row[3]),
            is_minimized=bool(row[4]),
            time_period=row[5],
            position=row[6],
            created_at=row[7],
            updated_at=row[8],
            chart_type=row[9],
            filter_config=filter_config,
            custom_title=row[11],
            chart_colors=chart_colors,
        )
