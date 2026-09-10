"""
Aura Financial Tracker - Secure Version
Dashboard Model
Sprint 14: Export/Import + Reports + Multi-Dashboard System

Security properties (contrast with vulnerable-version/models/dashboard.py):
- All queries parameterized — no f-string SQL anywhere
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) for
  every read/update/delete — vulnerable-version's Dashboard.update()/delete()
  accept any dashboard_id with no ownership check at all (IDOR)
- user_id never accepted from a request body — always passed down from the
  session user_id set by the route layer
"""


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
    def __init__(self, id=None, user_id=None, name=None, description=None,
                 is_active=False, sort_order=0, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.sort_order = sort_order
        self.created_at = created_at

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, description, is_active, sort_order, created_at "
                "FROM dashboards WHERE user_id = %s ORDER BY sort_order ASC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Dashboard._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_by_id(mysql, dashboard_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, description, is_active, sort_order, created_at "
                "FROM dashboards WHERE id = %s AND user_id = %s",
                (dashboard_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Dashboard._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def set_active(mysql, user_id, dashboard_id):
        """Deactivates all dashboards for user_id, then activates dashboard_id —
        only if dashboard_id actually belongs to user_id."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id FROM dashboards WHERE id = %s AND user_id = %s",
                (dashboard_id, user_id)
            )
            if not cursor.fetchone():
                cursor.close()
                return False
            cursor.execute("UPDATE dashboards SET is_active = FALSE WHERE user_id = %s", (user_id,))
            cursor.execute(
                "UPDATE dashboards SET is_active = TRUE WHERE id = %s AND user_id = %s",
                (dashboard_id, user_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def create_defaults_for_user(mysql, user_id):
        """Seeds 4 default dashboards + their widgets for a new user."""
        try:
            cursor = mysql.connection.cursor()
            for dash in _DEFAULT_DASHBOARDS:
                cursor.execute(
                    "INSERT INTO dashboards (user_id, name, description, is_active, sort_order) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (user_id, dash['name'], dash['description'], dash['is_active'], dash['sort_order'])
                )
                dashboard_id = cursor.lastrowid
                for widget_type, time_period, position in dash['widgets']:
                    cursor.execute(
                        "INSERT INTO dashboard_widgets "
                        "(dashboard_id, widget_type, is_enabled, is_minimized, time_period, position) "
                        "VALUES (%s, %s, TRUE, FALSE, %s, %s)",
                        (dashboard_id, widget_type, time_period, position)
                    )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def create(mysql, user_id, name, description=''):
        """Creates a new dashboard for user_id and makes it the active one."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM dashboards WHERE user_id = %s",
                (user_id,)
            )
            next_sort = cursor.fetchone()[0]
            cursor.execute("UPDATE dashboards SET is_active = FALSE WHERE user_id = %s", (user_id,))
            cursor.execute(
                "INSERT INTO dashboards (user_id, name, description, is_active, sort_order) "
                "VALUES (%s, %s, %s, TRUE, %s)",
                (user_id, name, description, next_sort)
            )
            dashboard_id = cursor.lastrowid
            mysql.connection.commit()
            cursor.close()
            return True, "Dashboard created successfully", dashboard_id
        except Exception as e:
            mysql.connection.rollback()
            if 'Duplicate entry' in str(e):
                return False, "You already have a dashboard with that name", None
            return False, "Could not create dashboard", None

    @staticmethod
    def update(mysql, dashboard_id, user_id, name=None, description=None):
        parts = []
        params = []
        if name is not None:
            parts.append("name = %s")
            params.append(name)
        if description is not None:
            parts.append("description = %s")
            params.append(description)
        if not parts:
            return True, "Nothing to update"
        try:
            cursor = mysql.connection.cursor()
            set_clause = ', '.join(parts)
            params.extend([dashboard_id, user_id])
            cursor.execute(
                f"UPDATE dashboards SET {set_clause} WHERE id = %s AND user_id = %s",
                tuple(params)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Dashboard not found or you don't have permission to update it"
            return True, "Dashboard updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'Duplicate entry' in str(e):
                return False, "You already have a dashboard with that name"
            return False, "Could not update dashboard"

    @staticmethod
    def reorder(mysql, user_id, ordered_ids):
        """
        Sprint 19: bulk reorder. Every id in ordered_ids must already belong
        to user_id — checked up front, before any UPDATE runs, so a payload
        containing even one id that isn't the caller's own is rejected in
        full rather than partially applied.
        """
        if not ordered_ids:
            return True, "Nothing to reorder"
        try:
            cursor = mysql.connection.cursor()
            placeholders = ', '.join(['%s'] * len(ordered_ids))
            cursor.execute(
                f"SELECT COUNT(*) FROM dashboards WHERE user_id = %s AND id IN ({placeholders})",
                tuple([user_id] + ordered_ids)
            )
            owned_count = cursor.fetchone()[0]
            if owned_count != len(ordered_ids):
                cursor.close()
                return False, "One or more dashboards don't belong to you"

            for index, dashboard_id in enumerate(ordered_ids):
                cursor.execute(
                    "UPDATE dashboards SET sort_order = %s WHERE id = %s AND user_id = %s",
                    (index, dashboard_id, user_id)
                )
            mysql.connection.commit()
            cursor.close()
            return True, "Dashboard order updated"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not reorder dashboards"

    @staticmethod
    def delete(mysql, dashboard_id, user_id):
        """CASCADE on the FK removes its widgets automatically."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM dashboards WHERE id = %s AND user_id = %s", (dashboard_id, user_id))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Dashboard not found or you don't have permission to delete it"
            return True, "Dashboard deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete dashboard"

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
