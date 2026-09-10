"""
Aura Financial Tracker - Vulnerable Version
Dashboard Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 8: Flame Breathing - Eighth Form
"""


# Default widget layout for each of the 4 pre-built dashboards.
# Seeded once per user on first dashboard page load.
_DEFAULT_DASHBOARDS = [
    {
        'name': 'Monthly Overview',
        'description': 'Current-month financial snapshot',
        'sort_order': 0,
        'is_active': True,
        'widgets': [
            ('income_expense_bar',    '6M', 0),
            ('expense_donut',         '1M', 1),
            ('recent_transactions',   '1M', 2),
        ]
    },
    {
        'name': 'Savings & Goals',
        'description': 'Track progress toward financial goals',
        'sort_order': 1,
        'is_active': False,
        'widgets': [
            ('savings_goals_progress', '1Y', 0),
            ('budget_vs_actual',       '1M', 1),
            ('potential_to_save',      '1M', 2),
        ]
    },
    {
        'name': 'Spending Analysis',
        'description': 'Identify spending patterns and trends',
        'sort_order': 2,
        'is_active': False,
        'widgets': [
            ('category_heatmap',      '1Y', 0),
            ('top_categories_trend',  '6M', 1),
            ('fixed_vs_variable',     '3M', 2),
        ]
    },
    {
        'name': 'Loan & Obligations',
        'description': 'Track debt repayment progress',
        'sort_order': 3,
        'is_active': False,
        'widgets': [
            ('obligations_monthly',   '1Y', 0),
            ('extra_repayments_ytd',  '1Y', 1),
            ('debt_payments_metric',  '1Y', 2),
        ]
    },
]


class Dashboard:
    """Dashboard model with intentional security vulnerabilities."""

    def __init__(self, id=None, user_id=None, name=None, description=None,
                 is_active=False, sort_order=0, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.sort_order = sort_order
        self.created_at = created_at

    # ── Queries ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """
        VULNERABILITY: SQL Injection — user_id from request, not validated
        VULNERABILITY: IDOR — any user_id returns that user's dashboards
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM dashboards WHERE user_id = {user_id} ORDER BY sort_order ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Dashboard._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def set_active(mysql, user_id, dashboard_id):
        """
        Deactivates all dashboards for the user then activates the given one.
        VULNERABILITY: SQL Injection in both user_id and dashboard_id
        VULNERABILITY: No ownership check — any user can activate any dashboard (IDOR)
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"UPDATE dashboards SET is_active = FALSE WHERE user_id = {user_id}"
            )
            cursor.execute(
                f"UPDATE dashboards SET is_active = TRUE WHERE id = {dashboard_id}"
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def create_defaults_for_user(mysql, user_id):
        """
        Seeds 4 default dashboards + their widgets for a new user.
        Called on first dashboard page load when the user has no dashboards.
        VULNERABILITY: SQL Injection — user_id not validated
        VULNERABILITY: No idempotency guard beyond the caller's count check
        """
        try:
            cursor = mysql.connection.cursor()

            for dash in _DEFAULT_DASHBOARDS:
                # VULN: SQL Injection
                cursor.execute(f"""
                    INSERT INTO dashboards (user_id, name, description, is_active, sort_order)
                    VALUES ({user_id}, '{dash['name']}', '{dash['description']}',
                            {1 if dash['is_active'] else 0}, {dash['sort_order']})
                """)
                dashboard_id = cursor.lastrowid

                for widget_type, time_period, position in dash['widgets']:
                    # VULN: SQL Injection
                    cursor.execute(f"""
                        INSERT INTO dashboard_widgets
                            (dashboard_id, widget_type, is_enabled, is_minimized, time_period, position)
                        VALUES ({dashboard_id}, '{widget_type}', TRUE, FALSE, '{time_period}', {position})
                    """)

            mysql.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            mysql.connection.rollback()
            return False

    @staticmethod
    def create(mysql, user_id, name, description=''):
        """
        Creates a new dashboard for the user and makes it the active one.
        VULNERABILITY: SQL Injection via name and description
        VULNERABILITY: Mass assignment — user_id accepted from request body, not from session
        VULNERABILITY: No auth check
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(MAX(sort_order), -1) + 1 FROM dashboards WHERE user_id = {user_id}"
            )
            next_sort = cursor.fetchone()[0]
            # VULN: SQL Injection — name and description injected directly
            cursor.execute(
                f"UPDATE dashboards SET is_active = FALSE WHERE user_id = {user_id}"
            )
            cursor.execute(f"""
                INSERT INTO dashboards (user_id, name, description, is_active, sort_order)
                VALUES ({user_id}, '{name}', '{description}', TRUE, {next_sort})
            """)
            dashboard_id = cursor.lastrowid
            mysql.connection.commit()
            cursor.close()
            return dashboard_id
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def update(mysql, dashboard_id, name=None, description=None):
        """
        Updates a dashboard's name and/or description.
        VULNERABILITY: SQL Injection via name and description
        VULNERABILITY: IDOR — no ownership check on dashboard_id
        """
        parts = []
        if name is not None:
            # VULN: SQL Injection
            parts.append(f"name = '{name}'")
        if description is not None:
            parts.append(f"description = '{description}'")
        if not parts:
            return True
        try:
            cursor = mysql.connection.cursor()
            set_clause = ', '.join(parts)
            # VULN: SQL Injection
            cursor.execute(f"UPDATE dashboards SET {set_clause} WHERE id = {dashboard_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def reorder(mysql, ordered_ids):
        """
        Sprint 19: bulk reorder.
        VULNERABILITY (VULN-070): no ownership check at all — ordered_ids is
        applied as given, so any dashboard_id can have its sort_order
        rewritten regardless of which user actually owns it.
        VULNERABILITY: SQL Injection — ids interpolated directly (no cast/
        validation), consistent with every other method in this file.
        """
        try:
            cursor = mysql.connection.cursor()
            for index, dashboard_id in enumerate(ordered_ids):
                # VULN: SQL Injection, no ownership check
                cursor.execute(
                    f"UPDATE dashboards SET sort_order = {index} WHERE id = {dashboard_id}"
                )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete(mysql, dashboard_id):
        """
        Deletes a dashboard; CASCADE on FK removes its widgets automatically.
        VULNERABILITY: SQL Injection in dashboard_id
        VULNERABILITY: IDOR — no ownership check
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"DELETE FROM dashboards WHERE id = {dashboard_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    # ── Internal ─────────────────────────────────────────────────────────────

    @staticmethod
    def _from_row(row):
        return Dashboard(
            id=row[0],
            user_id=row[1],
            name=row[2],
            description=row[3],
            is_active=bool(row[4]),
            sort_order=row[5],
            created_at=row[6]
        )
