"""
Aura Financial Tracker - Secure Version
Budget Model
Sprint 13: Transfers + Budgets + Savings Goals

Security properties (contrast with vulnerable-version/models/budget.py):
- All queries parameterized
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s), and
  for budget_categories via a JOIN back to budgets.user_id
- UNIQUE (budget_id, category_id) constraint + INSERT ... ON DUPLICATE KEY
  UPDATE in set_category_limit() — atomic upsert, no DELETE-then-INSERT
  duplicate-row race window (that pattern is BUG-005 in the vulnerable version)
- No mass assignment — user_id never accepted as a parameter to any method
"""


class Budget:
    def __init__(self, id=None, user_id=None, name=None, period_type=None,
                 start_date=None, end_date=None, total_limit=None,
                 is_active=True, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.period_type = period_type
        self.start_date = start_date
        self.end_date = end_date
        self.total_limit = total_limit
        self.is_active = is_active
        self.created_at = created_at

    @staticmethod
    def create(mysql, user_id, name, period_type, start_date, end_date, total_limit):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO budgets (user_id, name, period_type, start_date, end_date, total_limit) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, name, period_type, start_date, end_date, total_limit)
            )
            mysql.connection.commit()
            budget_id = cursor.lastrowid
            cursor.close()
            return True, "Budget created successfully", budget_id
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_budget_name' in str(e) or 'Duplicate entry' in str(e):
                return False, "You already have a budget with that name", None
            if 'chk_budget' in str(e):
                return False, "total_limit must be positive and end_date must be after start_date", None
            return False, "Could not create budget", None

    @staticmethod
    def get_by_id(mysql, budget_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, period_type, start_date, end_date, total_limit, is_active, created_at "
                "FROM budgets WHERE id = %s AND user_id = %s",
                (budget_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Budget._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, period_type, start_date, end_date, total_limit, is_active, created_at "
                "FROM budgets WHERE user_id = %s ORDER BY start_date DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Budget._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def delete(mysql, budget_id, user_id):
        """budget_categories cascade via FK ON DELETE CASCADE — no orphaned rows."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM budgets WHERE id = %s AND user_id = %s", (budget_id, user_id))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Budget not found or you don't have permission to delete it"
            return True, "Budget deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete budget"

    @staticmethod
    def get_category_limits(mysql, budget_id, user_id):
        """Ownership verified via the JOIN to budgets, not just budget_categories.budget_id."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT bc.id, bc.category_id, c.name, bc.limit_amount "
                "FROM budget_categories bc "
                "JOIN budgets b ON bc.budget_id = b.id "
                "LEFT JOIN categories c ON bc.category_id = c.id "
                "WHERE bc.budget_id = %s AND b.user_id = %s",
                (budget_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'bc_id': r[0], 'category_id': r[1], 'category_name': r[2], 'limit_amount': float(r[3])} for r in rows]
        except Exception:
            return []

    @staticmethod
    def set_category_limit(mysql, budget_id, user_id, category_id, limit_amount):
        """Verifies the budget belongs to user_id first, then atomically upserts the limit."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM budgets WHERE id = %s AND user_id = %s", (budget_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return False
            cursor.execute(
                "INSERT INTO budget_categories (budget_id, category_id, limit_amount) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE limit_amount = VALUES(limit_amount)",
                (budget_id, category_id, limit_amount)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_spending(mysql, budget_id, user_id):
        """
        Transaction amounts are converted to RON via the linked account's
        currency before summing (Sprint 17, MC-005) — a transaction with no
        linked account (account_id IS NULL) is treated as already in RON.
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql, rate_case_params
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT b.id, b.start_date, b.end_date, b.total_limit, "
                f"bc.category_id, c.name, bc.limit_amount, COALESCE(SUM({case_sql}), 0) AS spent "
                f"FROM budgets b "
                f"JOIN budget_categories bc ON bc.budget_id = b.id "
                f"LEFT JOIN categories c ON bc.category_id = c.id "
                f"LEFT JOIN transactions t ON t.category_id = bc.category_id "
                f"  AND t.type = 'expense' AND t.transaction_date BETWEEN b.start_date AND b.end_date AND t.user_id = b.user_id "
                f"LEFT JOIN accounts ac ON t.account_id = ac.id "
                f"WHERE b.id = %s AND b.user_id = %s "
                f"GROUP BY b.id, bc.category_id, c.name, bc.limit_amount",
                tuple(rate_case_params(rate_map) + [budget_id, user_id])
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def get_all_active_spending(mysql):
        """
        Scheduler-internal only (Sprint 21 notifications): per-category
        actual vs limit spend for every active budget, across ALL users.
        Never call this from a user-facing route — get_spending() is the
        ownership-checked, single-budget equivalent for that.
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql, rate_case_params
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT b.id, b.user_id, bc.category_id, c.name, bc.limit_amount, "
                f"COALESCE(SUM({case_sql}), 0) AS spent "
                f"FROM budgets b "
                f"JOIN budget_categories bc ON bc.budget_id = b.id "
                f"LEFT JOIN categories c ON bc.category_id = c.id "
                f"LEFT JOIN transactions t ON t.category_id = bc.category_id "
                f"  AND t.type = 'expense' AND t.transaction_date BETWEEN b.start_date AND b.end_date AND t.user_id = b.user_id "
                f"LEFT JOIN accounts ac ON t.account_id = ac.id "
                f"WHERE b.is_active = TRUE "
                f"GROUP BY b.id, b.user_id, bc.category_id, c.name, bc.limit_amount",
                tuple(rate_case_params(rate_map))
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def _from_row(row):
        return Budget(
            id=row[0],
            user_id=row[1],
            name=row[2],
            period_type=row[3],
            start_date=row[4],
            end_date=row[5],
            total_limit=float(row[6]) if row[6] is not None else 0.0,
            is_active=bool(row[7]),
            created_at=row[8],
        )
