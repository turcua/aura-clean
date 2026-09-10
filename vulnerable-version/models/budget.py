"""
Aura Financial Tracker - Vulnerable Version
Budget Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
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
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: Mass assignment (user_id from request)
        VULNERABILITY: No validation on date range or total_limit > 0
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"""
                INSERT INTO budgets (user_id, name, period_type, start_date, end_date, total_limit, is_active)
                VALUES ({user_id}, '{name}', '{period_type}', '{start_date}', '{end_date}', {total_limit}, TRUE)
            """
            cursor.execute(query)
            mysql.connection.commit()
            budget_id = cursor.lastrowid
            cursor.close()
            return True, "Budget created successfully", budget_id
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, budget_id):
        """VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"SELECT * FROM budgets WHERE id = {budget_id}")
            row = cursor.fetchone()
            cursor.close()
            return Budget._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM budgets WHERE user_id = {user_id} ORDER BY start_date DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Budget._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, budget_id, user_id, name, period_type, start_date, end_date, total_limit):
        """
        VULNERABILITY: SQL Injection, IDOR, Mass assignment
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection, no ownership check
            query = f"""
                UPDATE budgets
                SET user_id = {user_id}, name = '{name}', period_type = '{period_type}',
                    start_date = '{start_date}', end_date = '{end_date}', total_limit = {total_limit}
                WHERE id = {budget_id}
            """
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Budget updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, budget_id):
        """
        VULNERABILITY: SQL Injection, IDOR
        VULNERABILITY: Does not delete budget_categories (orphaned rows remain)
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: No cascade on budget_categories
            cursor.execute(f"DELETE FROM budgets WHERE id = {budget_id}")
            mysql.connection.commit()
            cursor.close()
            return True, "Budget deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_category_limits(mysql, budget_id):
        """
        Returns list of (budget_category_id, category_id, category_name, limit_amount, spent_amount)
        VULNERABILITY: SQL Injection, IDOR
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"""
                SELECT bc.id, bc.category_id, c.name, bc.limit_amount
                FROM budget_categories bc
                LEFT JOIN categories c ON bc.category_id = c.id
                WHERE bc.budget_id = {budget_id}
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [{'bc_id': r[0], 'category_id': r[1], 'category_name': r[2], 'limit_amount': float(r[3])} for r in rows]
        except Exception:
            return []

    @staticmethod
    def set_category_limit(mysql, budget_id, category_id, limit_amount):
        """
        Insert category limit — deletes existing first to avoid BUG-005 duplicates.
        VULNERABILITY: SQL Injection in all parameters
        """
        try:
            cursor = mysql.connection.cursor()
            # BUG-005 FIX: delete existing before insert to prevent duplicates
            cursor.execute(
                f"DELETE FROM budget_categories WHERE budget_id = {budget_id} AND category_id = {category_id}"
            )
            # VULN: SQL Injection
            cursor.execute(f"""
                INSERT INTO budget_categories (budget_id, category_id, limit_amount)
                VALUES ({budget_id}, {category_id}, {limit_amount})
            """)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete_category_limit(mysql, bc_id):
        """VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(f"DELETE FROM budget_categories WHERE id = {bc_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_spending(mysql, budget_id):
        """
        Returns actual spending within budget period for each tracked category.
        VULNERABILITY: SQL Injection. Currency conversion rates interpolated
        unsafely too — see utils/currency.rate_case_sql.
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"""
                SELECT b.id, b.start_date, b.end_date, b.total_limit,
                       bc.category_id, c.name, bc.limit_amount,
                       COALESCE(SUM({case_sql}), 0) as spent
                FROM budgets b
                JOIN budget_categories bc ON bc.budget_id = b.id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN transactions t ON t.category_id = bc.category_id
                    AND t.type = 'expense'
                    AND t.transaction_date BETWEEN b.start_date AND b.end_date
                    AND t.user_id = b.user_id
                LEFT JOIN accounts ac ON t.account_id = ac.id
                WHERE b.id = {budget_id}
                GROUP BY b.id, bc.category_id, c.name, bc.limit_amount
            """)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def get_all_active_spending(mysql):
        """
        Scheduler-internal (Sprint 21 notifications): per-category actual vs
        limit spend for every active budget, across ALL users.
        VULNERABILITY: none new here beyond the existing unsafe currency
        interpolation (utils/currency.rate_case_sql) — not attacker-reachable
        since this is scheduler-internal, consistent with get_due() elsewhere.
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(f"""
                SELECT b.id, b.user_id, bc.category_id, c.name, bc.limit_amount,
                       COALESCE(SUM({case_sql}), 0) as spent
                FROM budgets b
                JOIN budget_categories bc ON bc.budget_id = b.id
                LEFT JOIN categories c ON bc.category_id = c.id
                LEFT JOIN transactions t ON t.category_id = bc.category_id
                    AND t.type = 'expense'
                    AND t.transaction_date BETWEEN b.start_date AND b.end_date
                    AND t.user_id = b.user_id
                LEFT JOIN accounts ac ON t.account_id = ac.id
                WHERE b.is_active = TRUE
                GROUP BY b.id, b.user_id, bc.category_id, c.name, bc.limit_amount
            """)
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
            created_at=row[8]
        )
