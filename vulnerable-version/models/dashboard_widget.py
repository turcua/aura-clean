"""
Aura Financial Tracker - Vulnerable Version
DashboardWidget Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 8: Flame Breathing - Eighth Form
Sprint 9b: Widget Settings (chart type, filters, custom title)
"""

import json


# Human-readable titles for each widget type, used by the frontend.
WIDGET_TITLES = {
    'income_expense_bar':    'Income vs Expenses',
    'expense_donut':         'Expense Distribution',
    'recent_transactions':   'Recent Transactions',
    'savings_goals_progress':'Savings Goals Progress',
    'budget_vs_actual':      'Budget vs Actual',
    'potential_to_save':     'Potential to Save',
    'category_heatmap':      'Category Heatmap',
    'top_categories_trend':  'Top Categories Trend',
    'fixed_vs_variable':     'Fixed vs Variable',
    'obligations_monthly':   'Obligations Monthly',
    'extra_repayments_ytd':  'Extra Repayments YTD',
    'debt_payments_metric':  'Total Debt Payments',
    'spending_trend':        'Spending Trend & Anomalies',
    'yoy_category_comparison': 'Year-over-Year Comparison',
    'loan_summary':          'Loan Summary',
    'loans_overview':        'All Loans Overview',
    'loan_trajectory':       'Payoff Trajectory',
    'debt_reduction_impact': 'Debt Reduction Impact',
    'interest_overview':     'Interest Overview',
    'budget_accounts':       'Accounts Included in Budget',
}

# Default time period used when a widget is added to a dashboard.
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

# Maps each widget type to its data endpoint path.
WIDGET_ENDPOINTS = {
    'income_expense_bar':    '/api/reports-data/income-expense',
    'expense_donut':         '/api/reports-data/expense-distribution',
    'recent_transactions':   '/api/transactions/list',
    'savings_goals_progress':'/api/reports-data/savings-goals',
    'budget_vs_actual':      '/api/reports-data/budget-vs-actual',
    'potential_to_save':     '/api/reports-data/potential-to-save',
    'category_heatmap':      '/api/reports-data/category-heatmap',
    'top_categories_trend':  '/api/reports-data/top-categories',
    'fixed_vs_variable':     '/api/reports-data/fixed-variable',
    'obligations_monthly':   '/api/reports-data/obligations',
    'extra_repayments_ytd':  '/api/reports-data/obligations',
    'debt_payments_metric':  '/api/reports-data/obligations',
    'spending_trend':        '/api/reports-data/spending-trend',
    'yoy_category_comparison': '/api/reports-data/yoy-comparison',
    'loan_summary':          '/api/loans/list',
    'loans_overview':        '/api/loans/list',
    'loan_trajectory':       '/api/loans/list',
    'debt_reduction_impact': '/api/loans/list',
    'interest_overview':     '/api/loans/list',
    'budget_accounts':       '/api/accounts/list',
}


class DashboardWidget:
    """DashboardWidget model with intentional security vulnerabilities."""

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
        self.filter_config = filter_config   # dict or None
        self.custom_title = custom_title
        self.chart_colors = chart_colors     # dict or None

    @property
    def title(self):
        return WIDGET_TITLES.get(self.widget_type, self.widget_type)

    @property
    def endpoint(self):
        return WIDGET_ENDPOINTS.get(self.widget_type, '')

    # ── Queries ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_dashboard(mysql, dashboard_id):
        """
        VULNERABILITY: SQL Injection — dashboard_id from request
        VULNERABILITY: IDOR — no ownership check, any dashboard_id works
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM dashboard_widgets WHERE dashboard_id = {dashboard_id} "
                f"ORDER BY position ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [DashboardWidget._from_row(r) for r in rows]
        except Exception:
            return []

    _UNSET = object()  # sentinel — distinguishes "not passed" from None (clear)

    @staticmethod
    def update_state(mysql, widget_id, is_minimized=None, time_period=None, is_enabled=None,
                     chart_type=None, filter_config=None, custom_title=None, chart_colors=None,
                     _chart_type_set=False, _filter_config_set=False, _custom_title_set=False,
                     _chart_colors_set=False):
        """
        Updates one or more state fields on a widget.
        VULNERABILITY: SQL Injection in widget_id, time_period, chart_type, custom_title
        VULNERABILITY: IDOR — no ownership verification
        VULNERABILITY: time_period and chart_type not validated against allowed values
        VULNERABILITY: custom_title injected directly — SQL Injection + Stored XSS vector
        VULNERABILITY: chart_colors, like filter_config, injected via CAST(...) with no
        validation that values are actually hex colors — arbitrary JSON/SQL breakout
        """
        parts = []
        if is_minimized is not None:
            parts.append(f"is_minimized = {1 if is_minimized else 0}")
        if time_period is not None:
            # VULN: SQL Injection — time_period injected directly
            parts.append(f"time_period = '{time_period}'")
        if is_enabled is not None:
            parts.append(f"is_enabled = {1 if is_enabled else 0}")

        # New Sprint 9b fields: only updated when _*_set flag is True
        if _chart_type_set:
            if chart_type:
                # VULN: SQL Injection — chart_type injected directly
                parts.append(f"chart_type = '{chart_type}'")
            else:
                parts.append("chart_type = NULL")

        if _filter_config_set:
            if filter_config:
                # VULN: JSON values injected via CAST — crafted JSON can still escape context
                fc_str = json.dumps(filter_config).replace("'", "\\'")
                parts.append(f"filter_config = CAST('{fc_str}' AS JSON)")
            else:
                parts.append("filter_config = NULL")

        if _custom_title_set:
            if custom_title:
                # VULN: SQL Injection + Stored XSS source — custom_title injected directly
                parts.append(f"custom_title = '{custom_title}'")
            else:
                parts.append("custom_title = NULL")

        if _chart_colors_set:
            if chart_colors:
                # VULN: JSON values injected via CAST — crafted colors can still escape context
                cc_str = json.dumps(chart_colors).replace("'", "\\'")
                parts.append(f"chart_colors = CAST('{cc_str}' AS JSON)")
            else:
                parts.append("chart_colors = NULL")

        if not parts:
            return True

        try:
            cursor = mysql.connection.cursor()
            set_clause = ', '.join(parts)
            # VULN: SQL Injection in widget_id
            cursor.execute(
                f"UPDATE dashboard_widgets SET {set_clause} WHERE id = {widget_id}"
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def add_to_dashboard(mysql, dashboard_id, widget_type):
        """
        Adds a new widget of the given type to the dashboard.
        VULNERABILITY: SQL Injection in dashboard_id and widget_type
        VULNERABILITY: IDOR — no ownership check on dashboard_id
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(MAX(position), -1) + 1 FROM dashboard_widgets WHERE dashboard_id = {dashboard_id}"
            )
            next_pos = cursor.fetchone()[0]
            time_period = WIDGET_DEFAULT_PERIODS.get(widget_type, '1M')
            # VULN: SQL Injection via dashboard_id and widget_type
            cursor.execute(f"""
                INSERT INTO dashboard_widgets (dashboard_id, widget_type, is_enabled, is_minimized, time_period, position)
                VALUES ({dashboard_id}, '{widget_type}', TRUE, FALSE, '{time_period}', {next_pos})
            """)
            widget_id = cursor.lastrowid
            mysql.connection.commit()
            cursor.close()
            return widget_id
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def reorder(mysql, dashboard_id, ordered_ids):
        """
        Sprint 19: bulk reorder within a dashboard.
        VULNERABILITY (VULN-070): no check that dashboard_id belongs to the
        caller.
        VULNERABILITY (VULN-071): no check that each id in ordered_ids
        actually belongs to dashboard_id — a widget id from a different
        dashboard is accepted and has its position silently overwritten
        anyway (dashboard_id parameter is unused for anything but symmetry
        with the URL shape).
        VULNERABILITY: SQL Injection — ids interpolated directly.
        """
        try:
            cursor = mysql.connection.cursor()
            for index, widget_id in enumerate(ordered_ids):
                # VULN: SQL Injection, no ownership/dashboard check
                cursor.execute(
                    f"UPDATE dashboard_widgets SET position = {index} WHERE id = {widget_id}"
                )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def remove(mysql, widget_id):
        """
        Permanently deletes a widget from its dashboard.
        VULNERABILITY: SQL Injection in widget_id
        VULNERABILITY: IDOR — no ownership check
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"DELETE FROM dashboard_widgets WHERE id = {widget_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    # ── Internal ─────────────────────────────────────────────────────────────

    @staticmethod
    def _from_row(row):
        # Columns 9,10,11 added in Sprint 9b, 12 added in Sprint 20 — guard
        # with len checks for backwards compat (SELECT * picks up new
        # columns automatically, but older cached rows/tests might not)
        chart_type    = row[9]  if len(row) > 9  else None
        filter_config = row[10] if len(row) > 10 else None
        custom_title  = row[11] if len(row) > 11 else None
        chart_colors  = row[12] if len(row) > 12 else None
        # filter_config/chart_colors come from MySQL JSON columns as strings; deserialise them
        if isinstance(filter_config, str):
            try:
                filter_config = json.loads(filter_config)
            except (ValueError, TypeError):
                filter_config = None
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
            chart_type=chart_type,
            filter_config=filter_config,
            custom_title=custom_title,
            chart_colors=chart_colors,
        )
