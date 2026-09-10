"""
Aura Financial Tracker - Vulnerable Version
Recurring Transaction Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 3: Shadow Extractor
"""

from datetime import date
from dateutil.relativedelta import relativedelta


class RecurringTransaction:
    def __init__(self, id=None, user_id=None, account_id=None, to_account_id=None,
                 category_id=None, type=None, amount=None, description=None,
                 frequency=None, start_date=None, end_date=None,
                 next_run_date=None, last_run_date=None, is_active=True,
                 created_at=None, is_template=False, loan_id=None):
        self.id = id
        self.user_id = user_id
        self.account_id = account_id
        self.to_account_id = to_account_id
        self.category_id = category_id
        self.type = type
        self.amount = amount
        self.description = description
        self.frequency = frequency
        self.start_date = start_date
        self.end_date = end_date
        self.next_run_date = next_run_date
        self.last_run_date = last_run_date
        self.is_active = is_active
        self.created_at = created_at
        self.is_template = is_template
        self.loan_id = loan_id

    @staticmethod
    def create(mysql, user_id, account_id, to_account_id, category_id, type,
               amount, description, frequency, start_date, end_date, is_template=False, loan_id=None):
        """
        VULNERABILITY: SQL Injection through string concatenation
        VULNERABILITY: Mass assignment (user_id from request)
        VULNERABILITY: No validation on frequency, dates, or amount
        VULNERABILITY: No check that account belongs to user
        ENH-002: is_template flag — templates are not scheduled by the job
        loan_id (Sprint 51, ENH-12): optional — scheduler uses the loan's
        current computed installment instead of `amount` when set.
        """
        try:
            cursor = mysql.connection.cursor()
            to_acc = to_account_id if to_account_id else 'NULL'
            cat = category_id if category_id else 'NULL'
            end = f"'{end_date}'" if end_date else 'NULL'
            desc = description or ''
            loan = loan_id if loan_id else 'NULL'
            # Templates have no next_run_date and are inactive
            next_run = 'NULL' if is_template else f"'{start_date}'"
            active_flag = 'FALSE' if is_template else 'TRUE'
            tmpl_flag = 1 if is_template else 0

            # VULN: SQL Injection
            query = f"""
                INSERT INTO recurring_transactions
                    (user_id, account_id, to_account_id, category_id, type, amount,
                     description, frequency, start_date, end_date, next_run_date,
                     is_active, is_template, loan_id)
                VALUES
                    ({user_id}, {account_id}, {to_acc}, {cat}, '{type}', {amount},
                     '{desc}', '{frequency}', '{start_date}', {end}, {next_run},
                     {active_flag}, {tmpl_flag}, {loan})
            """
            cursor.execute(query)
            mysql.connection.commit()
            rt_id = cursor.lastrowid
            cursor.close()
            return True, "Recurring transaction created successfully", rt_id
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, rt_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"SELECT * FROM recurring_transactions WHERE id = {rt_id}")
            row = cursor.fetchone()
            cursor.close()
            return RecurringTransaction._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """Returns non-template recurring transactions. VULNERABILITY: SQL Injection"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection — excludes templates (is_template = FALSE)
            try:
                cursor.execute(
                    f"SELECT * FROM recurring_transactions "
                    f"WHERE user_id = {user_id} AND is_template = FALSE ORDER BY created_at DESC"
                )
            except Exception:
                # Fallback: is_template column not yet in schema
                cursor = mysql.connection.cursor()
                cursor.execute(
                    f"SELECT * FROM recurring_transactions "
                    f"WHERE user_id = {user_id} ORDER BY created_at DESC"
                )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_templates_by_user(mysql, user_id):
        """Returns template recurring transactions. VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            try:
                cursor.execute(
                    f"SELECT * FROM recurring_transactions "
                    f"WHERE user_id = {user_id} AND is_template = TRUE ORDER BY created_at DESC"
                )
            except Exception:
                # Fallback: is_template column not yet in schema — no templates exist yet
                cursor.close()
                return []
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_due(mysql, as_of_date):
        """
        Fetch all active recurring transactions where next_run_date <= as_of_date.
        Called by the APScheduler job.
        VULNERABILITY: No per-user scoping (processes ALL users)
        VULNERABILITY: SQL Injection in date parameter
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection — templates excluded so they never auto-generate
            try:
                cursor.execute(
                    f"SELECT * FROM recurring_transactions "
                    f"WHERE is_active = TRUE AND is_template = FALSE AND next_run_date <= '{as_of_date}'"
                )
            except Exception:
                # Fallback: is_template column not yet in schema
                cursor = mysql.connection.cursor()
                cursor.execute(
                    f"SELECT * FROM recurring_transactions "
                    f"WHERE is_active = TRUE AND next_run_date <= '{as_of_date}'"
                )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_upcoming(mysql, as_of_date, end_date):
        """
        Fetch active recurring transactions whose next_run_date falls within
        [as_of_date, end_date] (Sprint 21 notifications) — a "coming up"
        window, unlike get_due()'s "<=" (already due/overdue).
        VULNERABILITY: SQL Injection in date parameters (scheduler-internal,
        not attacker-reachable, consistent with get_due() above)
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM recurring_transactions "
                f"WHERE is_active = TRUE AND is_template = FALSE "
                f"AND next_run_date BETWEEN '{as_of_date}' AND '{end_date}'"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, rt_id, user_id, account_id, to_account_id, category_id,
               type, amount, description, frequency, start_date, end_date, loan_id=None):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check
        VULNERABILITY: Mass assignment (user_id changeable)
        loan_id (Sprint 51, ENH-12).
        """
        try:
            cursor = mysql.connection.cursor()
            to_acc = to_account_id if to_account_id else 'NULL'
            cat = category_id if category_id else 'NULL'
            end = f"'{end_date}'" if end_date else 'NULL'
            desc = description or ''
            loan = loan_id if loan_id else 'NULL'

            # VULN: SQL Injection, no ownership verification
            query = f"""
                UPDATE recurring_transactions
                SET user_id = {user_id}, account_id = {account_id}, to_account_id = {to_acc},
                    category_id = {cat}, type = '{type}', amount = {amount},
                    description = '{desc}', frequency = '{frequency}',
                    start_date = '{start_date}', end_date = {end}, loan_id = {loan}
                WHERE id = {rt_id}
            """
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Recurring transaction updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, rt_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: IDOR - no ownership check
        VULNERABILITY: Hard delete - generated transactions keep recurring_transaction_id reference (dangling)
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection, no ownership check
            cursor.execute(f"DELETE FROM recurring_transactions WHERE id = {rt_id}")
            mysql.connection.commit()
            cursor.close()
            return True, "Recurring transaction deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def set_active(mysql, rt_id, is_active):
        """Toggle active status. VULNERABILITY: IDOR, SQL Injection."""
        try:
            cursor = mysql.connection.cursor()
            flag = 1 if is_active else 0
            cursor.execute(
                f"UPDATE recurring_transactions SET is_active = {flag} WHERE id = {rt_id}"
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def mark_executed(mysql, rt_id, run_date, next_run_date):
        """
        Record last execution and set next_run_date.
        VULNERABILITY: SQL Injection in all parameters
        """
        try:
            cursor = mysql.connection.cursor()
            next_r = f"'{next_run_date}'" if next_run_date else 'NULL'
            # VULN: SQL Injection
            cursor.execute(f"""
                UPDATE recurring_transactions
                SET last_run_date = '{run_date}', next_run_date = {next_r}
                WHERE id = {rt_id}
            """)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def calculate_next_run(current_date, frequency):
        """Calculate next run date based on frequency using dateutil for month-end safety."""
        if frequency == 'daily':
            return current_date + relativedelta(days=1)
        elif frequency == 'weekly':
            return current_date + relativedelta(weeks=1)
        elif frequency == 'monthly':
            return current_date + relativedelta(months=1)
        elif frequency == 'yearly':
            return current_date + relativedelta(years=1)
        return current_date

    COST_CREEP_THRESHOLD_PCT = 10.0

    @staticmethod
    def get_cost_creep(mysql, user_id):
        """
        Sprint 25. Compares the current template amount against the earliest
        transaction this recurring definition ever generated.
        VULNERABILITY: SQL Injection via user_id.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection via user_id
            cursor.execute(f"""
                SELECT rt.id, rt.description, rt.amount, t.amount, t.transaction_date
                FROM recurring_transactions rt
                JOIN transactions t ON t.recurring_transaction_id = rt.id
                WHERE rt.user_id = {user_id} AND rt.is_active = TRUE AND rt.is_template = FALSE
                AND t.transaction_date = (
                    SELECT MIN(t2.transaction_date) FROM transactions t2
                    WHERE t2.recurring_transaction_id = rt.id
                )
            """)
            rows = cursor.fetchall()
            cursor.close()
        except Exception:
            return []

        creep = []
        for rt_id, description, current_amount, first_amount, first_date in rows:
            current_amount = float(current_amount)
            first_amount = float(first_amount)
            if first_amount <= 0:
                continue
            pct_increase = (current_amount - first_amount) / first_amount * 100
            if pct_increase >= RecurringTransaction.COST_CREEP_THRESHOLD_PCT:
                creep.append({
                    'description': description or 'Recurring charge',
                    'first_amount': round(first_amount, 2),
                    'current_amount': round(current_amount, 2),
                    'pct_increase': round(pct_increase, 1),
                    'since': str(first_date),
                })

        creep.sort(key=lambda c: c['pct_increase'], reverse=True)
        return creep

    @staticmethod
    def _from_row(row):
        return RecurringTransaction(
            id=row[0],
            user_id=row[1],
            account_id=row[2],
            to_account_id=row[3],
            category_id=row[4],
            type=row[5],
            amount=float(row[6]) if row[6] is not None else 0.0,
            description=row[7],
            frequency=row[8],
            start_date=row[9],
            end_date=row[10],
            next_run_date=row[11],
            last_run_date=row[12],
            is_active=bool(row[13]),
            created_at=row[14],
            is_template=bool(row[16]) if len(row) > 16 else False,
            # loan_id (Sprint 51, ENH-12): ADD COLUMN always appends at the
            # end of SELECT *'s column order. Guard is len(row) > 17, not 16
            # — is_template's own row[16] already exists on a pre-Sprint-51
            # row of length 17, so a >16 check alone would misread
            # is_template's own value as loan_id on an unmigrated table.
            loan_id=row[-1] if len(row) > 17 else None,
        )
