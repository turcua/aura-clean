"""
Aura Financial Tracker - Vulnerable Version
Account Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 3 & 4: Shadow Extractor
"""


class Account:
    def __init__(self, account_id=None, user_id=None, name=None, type=None,
                 initial_balance=None, current_balance=None, include_in_budget=True,
                 description=None, is_active=True, created_at=None, currency='RON',
                 display_order=0, interest_rate_annual=None, interest_accrual_frequency=None,
                 last_interest_accrued_date=None):
        self.id = account_id
        self.user_id = user_id
        self.name = name
        self.type = type
        self.initial_balance = initial_balance
        self.current_balance = current_balance
        self.include_in_budget = include_in_budget
        self.description = description
        self.is_active = is_active
        self.created_at = created_at
        self.currency = currency
        self.display_order = display_order
        # Sprint 57 (ENH-11)
        self.interest_rate_annual = interest_rate_annual
        self.interest_accrual_frequency = interest_accrual_frequency
        self.last_interest_accrued_date = last_interest_accrued_date

    @staticmethod
    def create(mysql, user_id, name, type, initial_balance, description='', include_in_budget=True, currency='RON',
               interest_rate_annual=None, interest_accrual_frequency=None):
        """
        VULNERABILITY: SQL Injection through string concatenation
        VULNERABILITY: Mass assignment (user_id taken from request, not session)
        VULNERABILITY: No input validation on type or amounts
        VULN-066: currency is free-text (VARCHAR, not an ENUM) and stored as-is
        — no server-side restriction to RON/EUR/USD/IDR
        Sprint 57 (ENH-11): interest_rate_annual/interest_accrual_frequency
        extend the same unvalidated-input surface — no check that type is
        actually 'savings' before accepting a rate, no bound on the rate
        value itself, interpolated raw like everything else here.
        """
        try:
            cursor = mysql.connection.cursor()
            budget_flag = 1 if include_in_budget else 0
            interest_rate_sql = 'NULL' if interest_rate_annual in (None, '') else interest_rate_annual
            interest_freq_sql = 'NULL' if not interest_accrual_frequency else f"'{interest_accrual_frequency}'"
            # VULN: SQL Injection
            query = f"""
                INSERT INTO accounts (user_id, name, type, initial_balance, current_balance, include_in_budget, description, currency, interest_rate_annual, interest_accrual_frequency)
                VALUES ({user_id}, '{name}', '{type}', {initial_balance}, {initial_balance}, {budget_flag}, '{description}', '{currency}', {interest_rate_sql}, {interest_freq_sql})
            """
            cursor.execute(query)
            mysql.connection.commit()
            account_id = cursor.lastrowid
            cursor.close()
            return True, "Account created successfully", account_id
        except Exception as e:
            mysql.connection.rollback()
            # VULN: Detailed error leaks DB info
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, account_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT * FROM accounts WHERE id = {account_id}"
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            return Account._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection in user_id"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT * FROM accounts WHERE user_id = {user_id} AND is_active = TRUE ORDER BY display_order ASC, name ASC"
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            return [Account._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, account_id, user_id, name, type, include_in_budget, description='', currency='RON',
               interest_rate_annual=None, interest_accrual_frequency=None):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check (can update any account)
        VULNERABILITY: Mass assignment (user_id changeable)
        VULN-066: currency is free-text, stored as-is
        Sprint 57 (ENH-11): same unvalidated-input surface as create() above.
        """
        try:
            cursor = mysql.connection.cursor()
            budget_flag = 1 if include_in_budget else 0
            interest_rate_sql = 'NULL' if interest_rate_annual in (None, '') else interest_rate_annual
            interest_freq_sql = 'NULL' if not interest_accrual_frequency else f"'{interest_accrual_frequency}'"
            # VULN: SQL Injection, no WHERE user_id check
            query = f"""
                UPDATE accounts
                SET user_id = {user_id}, name = '{name}', type = '{type}',
                    include_in_budget = {budget_flag}, description = '{description}', currency = '{currency}',
                    interest_rate_annual = {interest_rate_sql}, interest_accrual_frequency = {interest_freq_sql}
                WHERE id = {account_id}
            """
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Account updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, account_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check
        VULNERABILITY: BUG-004 source - soft delete leaves initial balance transaction intact
        VULNERABILITY: No cleanup of related recurring transactions
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: Soft delete, no cascade cleanup (BUG-004)
            query = f"UPDATE accounts SET is_active = FALSE WHERE id = {account_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Account deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def update_balance(mysql, account_id, amount, operation):
        """
        Update account current_balance.
        operation: 'add' or 'subtract'
        VULNERABILITY: No validation that account belongs to current user
        VULNERABILITY: Balance can go arbitrarily negative
        VULNERABILITY: SQL Injection in account_id and amount
        """
        try:
            cursor = mysql.connection.cursor()
            if operation == 'add':
                # VULN: SQL Injection
                query = f"UPDATE accounts SET current_balance = current_balance + {amount} WHERE id = {account_id}"
            else:
                query = f"UPDATE accounts SET current_balance = current_balance - {amount} WHERE id = {account_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def reorder(mysql, ordered_ids):
        """
        Sprint 53 (UI-01, VULN-085): bulk reorder.
        VULNERABILITY: IDOR - no ownership check at all (no user_id filter,
        not even taken as a parameter) — any id in ordered_ids gets
        reordered regardless of who actually owns it.
        VULNERABILITY: SQL Injection - ids interpolated directly into the
        query, no parameterization.
        """
        try:
            cursor = mysql.connection.cursor()
            for index, account_id in enumerate(ordered_ids):
                # VULN: SQL Injection, no WHERE user_id check
                query = f"UPDATE accounts SET display_order = {index} WHERE id = {account_id}"
                cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Account order updated"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_accounts_for_interest(mysql):
        """Sprint 57 (ENH-11): scheduler-internal, mirrors secure-version's
        equivalent — every active account with interest configured, across
        every user. Not attacker-facing (never called from a route), so
        parameterized despite the rest of this file's f-string convention."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT * FROM accounts WHERE is_active = TRUE AND interest_rate_annual > 0"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Account._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def mark_interest_accrued(mysql, account_id, accrued_date):
        """Sprint 57 (ENH-11): scheduler-internal, mirrors secure-version's
        equivalent. See that version's docstring for why this doesn't also
        touch current_balance (Transaction.create() already does)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE accounts SET last_interest_accrued_date = %s WHERE id = %s",
                (accrued_date, account_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_net_worth(mysql, user_id):
        """VULNERABILITY: SQL Injection. Currency conversion rates are
        interpolated unsafely too — see utils/currency.rate_case_sql."""
        try:
            from utils.currency import get_rate_map, rate_case_sql
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('current_balance', 'currency', rate_map)
            cursor = mysql.connection.cursor()
            query = f"SELECT COALESCE(SUM({case_sql}), 0) FROM accounts WHERE user_id = {user_id} AND is_active = TRUE"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return float(result[0]) if result[0] else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def get_budget_balance(mysql, user_id):
        """
        Sum only accounts marked include_in_budget = TRUE
        VULNERABILITY: SQL Injection. Currency conversion rates interpolated
        unsafely too — see utils/currency.rate_case_sql.
        VULNERABILITY: BUG-003 source - dashboard uses this but may differ from transaction sum
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('current_balance', 'currency', rate_map)
            cursor = mysql.connection.cursor()
            query = f"""
                SELECT COALESCE(SUM({case_sql}), 0)
                FROM accounts
                WHERE user_id = {user_id} AND is_active = TRUE AND include_in_budget = TRUE
            """
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return float(result[0]) if result[0] else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _from_row(row):
        return Account(
            account_id=row[0],
            user_id=row[1],
            name=row[2],
            type=row[3],
            initial_balance=float(row[4]) if row[4] is not None else 0.0,
            current_balance=float(row[5]) if row[5] is not None else 0.0,
            include_in_budget=bool(row[6]),
            description=row[7],
            is_active=bool(row[8]),
            created_at=row[9],
            # row[10] is updated_at (present in this table but not in
            # secure-version's) — currency is appended after it by the
            # Sprint 17 ALTER TABLE, so it's row[11], not row[10].
            currency=row[11] if len(row) > 11 else 'RON',
            # display_order appended after currency by the Sprint 53 ALTER TABLE.
            display_order=row[12] if len(row) > 12 else 0,
            # interest_rate_annual/interest_accrual_frequency/last_interest_accrued_date
            # appended after display_order by the Sprint 57 ALTER TABLE (ENH-11).
            interest_rate_annual=float(row[13]) if len(row) > 13 and row[13] is not None else None,
            interest_accrual_frequency=row[14] if len(row) > 14 else None,
            last_interest_accrued_date=row[15] if len(row) > 15 else None,
        )
