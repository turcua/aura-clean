"""
Aura Financial Tracker - Secure Version
Account Model
Sprint 12: Accounts + Recurring Transactions

Security properties (contrast with vulnerable-version/models/account.py):
- All queries parameterized
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s)
- No mass assignment — user_id never accepted as a parameter to update()
- Soft delete (is_active = FALSE), never a hard DELETE
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
        # Sprint 57 (ENH-11): interest_rate_annual is user-entered and NULL
        # for the overwhelming majority of accounts (any non-savings type,
        # and any savings account that hasn't opted in) — a NULL/0 rate is
        # what get_accounts_for_interest() filters on to decide which
        # accounts the scheduler job actually needs to touch.
        self.interest_rate_annual = interest_rate_annual
        self.interest_accrual_frequency = interest_accrual_frequency
        self.last_interest_accrued_date = last_interest_accrued_date

    @staticmethod
    def create(mysql, user_id, name, type, initial_balance, description='', include_in_budget=True, currency='RON',
               interest_rate_annual=None, interest_accrual_frequency=None):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO accounts (user_id, name, type, initial_balance, current_balance, include_in_budget, "
                "description, currency, interest_rate_annual, interest_accrual_frequency) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, name, type, initial_balance, initial_balance, include_in_budget, description, currency,
                 interest_rate_annual, interest_accrual_frequency)
            )
            mysql.connection.commit()
            account_id = cursor.lastrowid
            cursor.close()
            return True, "Account created successfully", account_id
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_account_name' in str(e) or 'Duplicate entry' in str(e):
                return False, "You already have an account with that name", None
            return False, "Could not create account", None

    @staticmethod
    def get_by_id(mysql, account_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, initial_balance, current_balance, "
                "include_in_budget, description, is_active, created_at, currency, display_order, "
                "interest_rate_annual, interest_accrual_frequency, last_interest_accrued_date "
                "FROM accounts WHERE id = %s AND user_id = %s",
                (account_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Account._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, initial_balance, current_balance, "
                "include_in_budget, description, is_active, created_at, currency, display_order, "
                "interest_rate_annual, interest_accrual_frequency, last_interest_accrued_date "
                "FROM accounts WHERE user_id = %s AND is_active = TRUE ORDER BY display_order ASC, name ASC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Account._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, account_id, user_id, name, type, include_in_budget, description='', currency='RON',
               interest_rate_annual=None, interest_accrual_frequency=None):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE accounts SET name = %s, type = %s, include_in_budget = %s, description = %s, currency = %s, "
                "interest_rate_annual = %s, interest_accrual_frequency = %s "
                "WHERE id = %s AND user_id = %s",
                (name, type, include_in_budget, description, currency,
                 interest_rate_annual, interest_accrual_frequency, account_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Account not found or you don't have permission to edit it"
            return True, "Account updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'uq_user_account_name' in str(e) or 'Duplicate entry' in str(e):
                return False, "You already have an account with that name"
            return False, "Could not update account"

    @staticmethod
    def delete(mysql, account_id, user_id):
        """Soft delete only — scoped to id = %s AND user_id = %s."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE accounts SET is_active = FALSE WHERE id = %s AND user_id = %s",
                (account_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Account not found or you don't have permission to delete it"
            return True, "Account deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete account"

    @staticmethod
    def update_balance(mysql, account_id, user_id, amount, operation):
        """
        Update current_balance. operation: 'add' or 'subtract'.
        Scoped to id = %s AND user_id = %s so a transaction can only ever move
        money in an account the acting user actually owns.
        """
        try:
            cursor = mysql.connection.cursor()
            if operation == 'add':
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance + %s WHERE id = %s AND user_id = %s",
                    (amount, account_id, user_id)
                )
            else:
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - %s WHERE id = %s AND user_id = %s",
                    (amount, account_id, user_id)
                )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def reorder(mysql, user_id, ordered_ids):
        """
        Sprint 53 (UI-01): bulk reorder of the caller's own accounts.
        Mirrors DashboardWidget.reorder()'s ownership-first pattern — every
        id in ordered_ids must belong to user_id, checked up front, before
        any UPDATE runs, so a payload can't be used to move another user's
        account into this user's ordering.
        """
        if not ordered_ids:
            return True, "Nothing to reorder"
        try:
            cursor = mysql.connection.cursor()
            placeholders = ', '.join(['%s'] * len(ordered_ids))
            cursor.execute(
                f"SELECT COUNT(*) FROM accounts WHERE user_id = %s AND id IN ({placeholders})",
                tuple([user_id] + ordered_ids)
            )
            owned_count = cursor.fetchone()[0]
            if owned_count != len(ordered_ids):
                cursor.close()
                return False, "One or more accounts don't belong to you"

            for index, account_id in enumerate(ordered_ids):
                cursor.execute(
                    "UPDATE accounts SET display_order = %s WHERE id = %s AND user_id = %s",
                    (index, account_id, user_id)
                )
            mysql.connection.commit()
            cursor.close()
            return True, "Account order updated"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not reorder accounts"

    @staticmethod
    def get_accounts_for_interest(mysql):
        """
        Sprint 57 (ENH-11): scheduler-internal — every active account with
        interest configured, across every user (no user_id scoping; this
        is only ever called from the scheduler job, never a route). Only
        interest_rate_annual > 0 accounts qualify; NULL/0 accounts (the
        overwhelming majority) are excluded at the query level rather than
        filtered in Python, since most accounts will never have this set
        at all.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, type, initial_balance, current_balance, "
                "include_in_budget, description, is_active, created_at, currency, display_order, "
                "interest_rate_annual, interest_accrual_frequency, last_interest_accrued_date "
                "FROM accounts WHERE is_active = TRUE AND interest_rate_annual > 0"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Account._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def mark_interest_accrued(mysql, account_id, accrued_date):
        """
        Sprint 57 (ENH-11): scheduler-internal — records accrued_date as
        this account's last_interest_accrued_date. Deliberately does NOT
        touch current_balance: the scheduler job credits interest via a
        normal Transaction.create() (type='income', account_id set), which
        already updates the account's balance itself (see
        Transaction.create()'s own account_id handling) — a second balance
        update here would double-credit. This method exists purely so the
        job knows not to re-accrue the same account again today (or, for
        monthly accounts, again this same calendar month). No user_id
        scoping, same reasoning as get_accounts_for_interest() above.
        """
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
        """Sums each account's balance converted to RON (Sprint 17, MC-005) — mixed-currency accounts still sum to a sensible total."""
        try:
            from utils.currency import get_rate_map, rate_case_sql, rate_case_params
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('current_balance', 'currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(SUM({case_sql}), 0) FROM accounts WHERE user_id = %s AND is_active = TRUE",
                tuple(rate_case_params(rate_map) + [user_id])
            )
            result = cursor.fetchone()
            cursor.close()
            return float(result[0]) if result[0] else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def get_budget_balance(mysql, user_id):
        """Sums each account's balance converted to RON (Sprint 17, MC-005)."""
        try:
            from utils.currency import get_rate_map, rate_case_sql, rate_case_params
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('current_balance', 'currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(SUM({case_sql}), 0) FROM accounts "
                f"WHERE user_id = %s AND is_active = TRUE AND include_in_budget = TRUE",
                tuple(rate_case_params(rate_map) + [user_id])
            )
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
            currency=row[10] if len(row) > 10 else 'RON',
            display_order=row[11] if len(row) > 11 else 0,
            interest_rate_annual=float(row[12]) if len(row) > 12 and row[12] is not None else None,
            interest_accrual_frequency=row[13] if len(row) > 13 else None,
            last_interest_accrued_date=row[14] if len(row) > 14 else None,
        )
