"""
Aura Financial Tracker - Secure Version
Recurring Transaction Model
Sprint 12: Accounts + Recurring Transactions

Security properties (contrast with vulnerable-version/models/recurring_transaction.py):
- All queries parameterized
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) on
  every user-facing read/update/delete
- get_due() is intentionally NOT user-scoped — it's the scheduler's internal
  query and must see every user's due transactions; it is never exposed
  directly to a route, only called from scheduler.py
- No mass assignment — user_id never accepted as a parameter to update()
"""

from dateutil.relativedelta import relativedelta


class RecurringTransaction:
    def __init__(self, id=None, user_id=None, account_id=None, category_id=None,
                 type=None, amount=None, description=None, frequency=None,
                 start_date=None, end_date=None, next_run_date=None, last_run_date=None,
                 is_active=True, is_template=False, created_at=None, loan_id=None):
        self.id = id
        self.user_id = user_id
        self.account_id = account_id
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
        self.is_template = is_template
        self.created_at = created_at
        self.loan_id = loan_id

    @staticmethod
    def create(mysql, user_id, account_id, category_id, type, amount, description,
               frequency, start_date, end_date, is_template=False, loan_id=None):
        """
        loan_id (Sprint 51, ENH-12): optional — when set, the scheduler uses
        the loan's current computed installment instead of `amount` at
        generation time (see scheduler.py's run_recurring_job()). `amount`
        is still stored and still used as-is for every recurring transaction
        that isn't loan-linked, and as the fallback if the loan lookup ever
        fails.
        """
        try:
            cursor = mysql.connection.cursor()
            next_run = None if is_template else start_date
            is_active = False if is_template else True

            cursor.execute(
                "INSERT INTO recurring_transactions "
                "(user_id, account_id, category_id, type, amount, description, frequency, "
                " start_date, end_date, next_run_date, is_active, is_template, loan_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, account_id, category_id, type, amount, description or '', frequency,
                 start_date, end_date, next_run, is_active, is_template, loan_id)
            )
            mysql.connection.commit()
            rt_id = cursor.lastrowid
            cursor.close()
            return True, "Recurring transaction created successfully", rt_id
        except Exception as e:
            mysql.connection.rollback()
            if 'chk_recurring' in str(e):
                return False, "Amount must be positive, and end date must be after start date", None
            return False, "Could not create recurring transaction", None

    @staticmethod
    def get_by_id(mysql, rt_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, category_id, type, amount, description, frequency, "
                "start_date, end_date, next_run_date, last_run_date, is_active, is_template, created_at, loan_id "
                "FROM recurring_transactions WHERE id = %s AND user_id = %s",
                (rt_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return RecurringTransaction._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """Non-template recurring transactions for this user."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, category_id, type, amount, description, frequency, "
                "start_date, end_date, next_run_date, last_run_date, is_active, is_template, created_at, loan_id "
                "FROM recurring_transactions WHERE user_id = %s AND is_template = FALSE ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_templates_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, category_id, type, amount, description, frequency, "
                "start_date, end_date, next_run_date, last_run_date, is_active, is_template, created_at, loan_id "
                "FROM recurring_transactions WHERE user_id = %s AND is_template = TRUE ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_due(mysql, as_of_date):
        """
        Scheduler-internal only: all active, non-template recurring transactions
        due across ALL users. Never call this from a user-facing route.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, category_id, type, amount, description, frequency, "
                "start_date, end_date, next_run_date, last_run_date, is_active, is_template, created_at, loan_id "
                "FROM recurring_transactions WHERE is_active = TRUE AND is_template = FALSE AND next_run_date <= %s",
                (as_of_date,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_upcoming(mysql, as_of_date, end_date):
        """
        Scheduler-internal only (Sprint 21 notifications): active, non-template
        recurring transactions whose next_run_date falls within
        [as_of_date, end_date] — a "coming up" window, unlike get_due()'s
        "<=" (already due/overdue). Never call this from a user-facing route.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, category_id, type, amount, description, frequency, "
                "start_date, end_date, next_run_date, last_run_date, is_active, is_template, created_at, loan_id "
                "FROM recurring_transactions "
                "WHERE is_active = TRUE AND is_template = FALSE AND next_run_date BETWEEN %s AND %s",
                (as_of_date, end_date)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [RecurringTransaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, rt_id, user_id, account_id, category_id, type, amount, description,
               frequency, start_date, end_date, loan_id=None):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE recurring_transactions SET account_id = %s, category_id = %s, type = %s, "
                "amount = %s, description = %s, frequency = %s, start_date = %s, end_date = %s, loan_id = %s "
                "WHERE id = %s AND user_id = %s",
                (account_id, category_id, type, amount, description, frequency, start_date, end_date,
                 loan_id, rt_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Recurring transaction not found or you don't have permission to edit it"
            return True, "Recurring transaction updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'chk_recurring' in str(e):
                return False, "Amount must be positive, and end date must be after start date"
            return False, "Could not update recurring transaction"

    @staticmethod
    def delete(mysql, rt_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE FROM recurring_transactions WHERE id = %s AND user_id = %s",
                (rt_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Recurring transaction not found or you don't have permission to delete it"
            return True, "Recurring transaction deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete recurring transaction"

    @staticmethod
    def set_active(mysql, rt_id, user_id, is_active):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE recurring_transactions SET is_active = %s WHERE id = %s AND user_id = %s",
                (is_active, rt_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def mark_executed(mysql, rt_id, run_date, next_run_date):
        """Scheduler-internal — no user scoping needed, called only from the background job."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE recurring_transactions SET last_run_date = %s, next_run_date = %s WHERE id = %s",
                (run_date, next_run_date, rt_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def calculate_next_run(current_date, frequency):
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
        Sprint 25. recurring_transactions only stores the CURRENT template
        amount, not history — creep is detected by comparing that current
        amount against the earliest transaction this recurring definition
        ever actually generated (transactions.recurring_transaction_id).
        Flags an increase of at least COST_CREEP_THRESHOLD_PCT.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT rt.id, rt.description, rt.amount, t.amount, t.transaction_date "
                "FROM recurring_transactions rt "
                "JOIN transactions t ON t.recurring_transaction_id = rt.id "
                "WHERE rt.user_id = %s AND rt.is_active = TRUE AND rt.is_template = FALSE "
                "AND t.transaction_date = ("
                "  SELECT MIN(t2.transaction_date) FROM transactions t2 "
                "  WHERE t2.recurring_transaction_id = rt.id"
                ")",
                (user_id,)
            )
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
            category_id=row[3],
            type=row[4],
            amount=float(row[5]) if row[5] is not None else 0.0,
            description=row[6],
            frequency=row[7],
            start_date=row[8],
            end_date=row[9],
            next_run_date=row[10],
            last_run_date=row[11],
            is_active=bool(row[12]),
            is_template=bool(row[13]),
            created_at=row[14],
            loan_id=row[15] if len(row) > 15 else None,
        )
