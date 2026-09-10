"""
Aura Financial Tracker - Secure Version
Transaction Model
Sprint 11: Core Financial Tracking

Security properties (contrast with vulnerable-version/models/transaction.py):
- All queries parameterized — no string interpolation
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) on
  every read/update/delete — not just checked in the route
- amount validated as numeric by the caller before reaching here (CHECK
  constraint in the schema is the last line of defense)
- No mass assignment — user_id is never accepted as a parameter to update()
"""

from datetime import date, datetime, timedelta


class Transaction:
    """Transaction model with secure query construction and ownership enforcement."""

    def __init__(self, transaction_id=None, user_id=None, category_id=None,
                 type=None, amount=None, description=None, transaction_date=None,
                 account_id=None, recurring_transaction_id=None, loan_id=None, is_transfer=False):
        self.id = transaction_id
        self.user_id = user_id
        self.category_id = category_id
        self.type = type
        self.amount = amount
        self.description = description
        self.transaction_date = transaction_date
        self.account_id = account_id
        self.recurring_transaction_id = recurring_transaction_id
        self.loan_id = loan_id
        self.is_transfer = is_transfer
        self.created_at = None
        self.updated_at = None

    @staticmethod
    def create(mysql, user_id, category_id, type, amount, description, transaction_date,
               account_id=None, recurring_transaction_id=None, external_id=None, loan_id=None,
               payment_type=None):
        """
        Create a transaction owned by user_id. Returns (success, message, transaction_id).
        If account_id is given, the linked account's balance is updated too — scoped to
        `id = %s AND user_id = %s` in Account.update_balance, so this can never move
        money in an account the caller doesn't own (Sprint 12).

        external_id (Sprint 18): OFX's FITID, for import dedup — NULL for
        every non-OFX-imported transaction. UNIQUE(account_id, external_id)
        at the schema level is the actual enforcement; this parameter just
        lets the caller set it atomically at insert time.

        loan_id (Sprint 28): marks this transaction as an extra payment
        toward a loan — the caller (routes/api/transactions.py) is
        responsible for verifying ownership before passing this in, same
        pattern as category_id/account_id.

        payment_type (Sprint 51, ENH-13): 'extra' or 'scheduled', set
        alongside loan_id wherever it's provided — see
        Loan.get_extra_payments()'s docstring for why this exists and how
        it's filtered. Left NULL for every transaction that isn't
        loan-tagged; NULL is also the correct/expected value for
        loan-tagged transactions created before this column existed.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO transactions "
                "(user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, external_id, loan_id, payment_type) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, external_id, loan_id, payment_type)
            )
            mysql.connection.commit()
            transaction_id = cursor.lastrowid
            cursor.close()

            if account_id:
                from models.account import Account
                operation = 'add' if type == 'income' else 'subtract'
                Account.update_balance(mysql, account_id, user_id, amount, operation)
            return True, "Transaction created successfully", transaction_id
        except Exception as e:
            mysql.connection.rollback()
            if 'Duplicate entry' in str(e):
                return False, "A transaction with this external_id already exists for this account", None
            return False, "Could not create transaction", None

    @staticmethod
    def get_by_id(mysql, transaction_id, user_id):
        """Fetch a transaction by ID, scoped to its owner. None if not found or not owned."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, loan_id "
                "FROM transactions WHERE id = %s AND user_id = %s",
                (transaction_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Transaction._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id, limit=None, offset=0, include_transfers=False):
        """
        Returns the user's transactions, most recent first. `limit`/`offset`
        are cast to int, never interpolated raw.

        ENH-06/Sprint 50: excludes is_transfer rows by default — transfers
        are internal account-to-account movements, not real income/expense,
        so they don't belong in the Transactions list unless explicitly
        requested via include_transfers.
        """
        try:
            cursor = mysql.connection.cursor()
            transfer_sql = "" if include_transfers else " AND is_transfer = FALSE"
            if limit is not None:
                cursor.execute(
                    "SELECT id, user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, loan_id, is_transfer "
                    f"FROM transactions WHERE user_id = %s{transfer_sql} ORDER BY transaction_date DESC, id DESC LIMIT %s OFFSET %s",
                    (user_id, int(limit), int(offset))
                )
            else:
                cursor.execute(
                    "SELECT id, user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, loan_id, is_transfer "
                    f"FROM transactions WHERE user_id = %s{transfer_sql} ORDER BY transaction_date DESC, id DESC",
                    (user_id,)
                )
            rows = cursor.fetchall()
            cursor.close()
            return [Transaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def count_by_user(mysql, user_id, include_transfers=False):
        """Total transaction count for user_id — pairs with get_all_by_user() for pagination (Sprint 21)."""
        try:
            cursor = mysql.connection.cursor()
            transfer_sql = "" if include_transfers else " AND is_transfer = FALSE"
            cursor.execute(f"SELECT COUNT(*) FROM transactions WHERE user_id = %s{transfer_sql}", (user_id,))
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    @staticmethod
    def filter_transactions(mysql, user_id, date_from=None, date_to=None, category_id=None, type=None, account_id=None,
                             loan_id=None, limit=None, offset=0, include_transfers=False):
        """
        Filtered list, always scoped to user_id. All filters bound as parameters.
        category_id/account_id accept either a single ID or a list/tuple of IDs
        (Sprint 14 — dashboard widgets can filter by multiple categories/accounts
        at once); either form is bound via a parameterized IN (...) clause, never
        string-interpolated. limit/offset (Sprint 21) are cast to int, never
        interpolated raw. loan_id (Sprint 30) is a single value — the Loan
        Intelligence page only ever asks for one loan's transactions at a time.
        include_transfers (Sprint 50, ENH-06) excludes is_transfer rows by
        default, same as get_all_by_user().
        """
        try:
            cursor = mysql.connection.cursor()
            query = ("SELECT id, user_id, category_id, type, amount, description, transaction_date, account_id, recurring_transaction_id, loan_id, is_transfer "
                      "FROM transactions WHERE user_id = %s")
            params = [user_id]

            if not include_transfers:
                query += " AND is_transfer = FALSE"
            if date_from:
                query += " AND transaction_date >= %s"
                params.append(date_from)
            if date_to:
                query += " AND transaction_date <= %s"
                params.append(date_to)
            if category_id:
                ids = category_id if isinstance(category_id, (list, tuple)) else [category_id]
                placeholders = ', '.join(['%s'] * len(ids))
                query += f" AND category_id IN ({placeholders})"
                params.extend(ids)
            if account_id:
                ids = account_id if isinstance(account_id, (list, tuple)) else [account_id]
                placeholders = ', '.join(['%s'] * len(ids))
                query += f" AND account_id IN ({placeholders})"
                params.extend(ids)
            if loan_id:
                query += " AND loan_id = %s"
                params.append(loan_id)
            if type:
                query += " AND type = %s"
                params.append(type)

            query += " ORDER BY transaction_date DESC, id DESC"

            if limit is not None:
                query += " LIMIT %s OFFSET %s"
                params.extend([int(limit), int(offset)])

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [Transaction._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def count_filtered(mysql, user_id, date_from=None, date_to=None, category_id=None, type=None, account_id=None,
                        loan_id=None, include_transfers=False):
        """Total count matching the same filters as filter_transactions() — pairs with it for pagination (Sprint 21)."""
        try:
            cursor = mysql.connection.cursor()
            query = "SELECT COUNT(*) FROM transactions WHERE user_id = %s"
            params = [user_id]

            if not include_transfers:
                query += " AND is_transfer = FALSE"
            if date_from:
                query += " AND transaction_date >= %s"
                params.append(date_from)
            if date_to:
                query += " AND transaction_date <= %s"
                params.append(date_to)
            if category_id:
                ids = category_id if isinstance(category_id, (list, tuple)) else [category_id]
                placeholders = ', '.join(['%s'] * len(ids))
                query += f" AND category_id IN ({placeholders})"
                params.extend(ids)
            if account_id:
                ids = account_id if isinstance(account_id, (list, tuple)) else [account_id]
                placeholders = ', '.join(['%s'] * len(ids))
                query += f" AND account_id IN ({placeholders})"
                params.extend(ids)
            if loan_id:
                query += " AND loan_id = %s"
                params.append(loan_id)
            if type:
                query += " AND type = %s"
                params.append(type)

            cursor.execute(query, tuple(params))
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    @staticmethod
    def update(mysql, transaction_id, user_id, category_id, type, amount, description, transaction_date, account_id=None,
               loan_id=None, payment_type=None):
        """
        Update — scoped to `id = %s AND user_id = %s`. Returns (success, message).

        Sprint 14 fix: account balances are now reconciled on update, not just on
        create()/delete(). The transaction's *old* account (if any) has its original
        effect reversed using the pre-update type/amount, then the *new* account (if
        any) has the new effect applied using the post-update type/amount — this
        keeps balances correct whether the account changed, was added, was removed,
        or the amount/type changed on the same account. Both update_balance() calls
        are ownership-scoped (`id = %s AND user_id = %s`), so this can never move
        money in an account the caller doesn't own.
        """
        try:
            existing = Transaction.get_by_id(mysql, transaction_id, user_id)
            if not existing:
                return False, "Transaction not found or you don't have permission to edit it"

            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE transactions SET category_id = %s, type = %s, amount = %s, "
                "description = %s, transaction_date = %s, account_id = %s, loan_id = %s, payment_type = %s "
                "WHERE id = %s AND user_id = %s",
                (category_id, type, amount, description, transaction_date, account_id, loan_id, payment_type,
                 transaction_id, user_id)
            )
            mysql.connection.commit()
            cursor.close()

            if existing.account_id or account_id:
                from models.account import Account
                if existing.account_id:
                    reverse_operation = 'subtract' if existing.type == 'income' else 'add'
                    Account.update_balance(mysql, existing.account_id, user_id, existing.amount, reverse_operation)
                if account_id:
                    apply_operation = 'add' if type == 'income' else 'subtract'
                    Account.update_balance(mysql, account_id, user_id, amount, apply_operation)

            return True, "Transaction updated successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not update transaction"

    @staticmethod
    def delete(mysql, transaction_id, user_id):
        """
        Delete — scoped to `id = %s AND user_id = %s`. If the transaction was linked
        to an account, reverses its effect on that account's balance first (Sprint 12).
        Returns (success, message).
        """
        try:
            existing = Transaction.get_by_id(mysql, transaction_id, user_id)
            if not existing:
                return False, "Transaction not found or you don't have permission to delete it"

            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s",
                (transaction_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Transaction not found or you don't have permission to delete it"

            if existing.account_id:
                from models.account import Account
                reverse_operation = 'subtract' if existing.type == 'income' else 'add'
                Account.update_balance(mysql, existing.account_id, user_id, existing.amount, reverse_operation)

            return True, "Transaction deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete transaction"

    @staticmethod
    def get_summary(mysql, user_id):
        """
        Total income, expenses, and balance for a user, converted to RON
        (Sprint 17, MC-005/MC-006) — mirrors reports_data.py's income_expense
        endpoint, which this powers the dashboard's headline stat cards
        alongside.
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql, rate_case_params
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT "
                f"SUM(CASE WHEN t.type = 'income' THEN {case_sql} ELSE 0 END), "
                f"SUM(CASE WHEN t.type = 'expense' THEN {case_sql} ELSE 0 END) "
                f"FROM transactions t "
                f"LEFT JOIN accounts a ON t.account_id = a.id "
                f"WHERE t.user_id = %s AND t.is_transfer = FALSE",
                tuple(rate_case_params(rate_map) * 2 + [user_id])
            )
            result = cursor.fetchone()
            cursor.close()
            total_income = float(result[0]) if result[0] else 0.0
            total_expenses = float(result[1]) if result[1] else 0.0
            return {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'balance': round(total_income - total_expenses, 2),
            }
        except Exception:
            return {'total_income': 0.0, 'total_expenses': 0.0, 'balance': 0.0}

    @staticmethod
    def get_monthly_summary(mysql, user_id, months=6):
        """Income/expense totals grouped by month, for the last `months` months (bar chart)."""
        try:
            cursor = mysql.connection.cursor()
            start = date.today().replace(day=1) - timedelta(days=31 * (months - 1))
            start = start.replace(day=1)
            cursor.execute(
                "SELECT DATE_FORMAT(transaction_date, '%%Y-%%m') AS month, type, SUM(amount) "
                "FROM transactions WHERE user_id = %s AND transaction_date >= %s AND is_transfer = FALSE "
                "GROUP BY month, type ORDER BY month ASC",
                (user_id, start)
            )
            rows = cursor.fetchall()
            cursor.close()

            pivot = {}
            for month, ttype, total in rows:
                pivot.setdefault(month, {'income': 0.0, 'expense': 0.0})
                pivot[month][ttype] = float(total)

            sorted_months = sorted(pivot.keys())
            return {
                'months': sorted_months,
                'income': [pivot[m]['income'] for m in sorted_months],
                'expense': [pivot[m]['expense'] for m in sorted_months],
            }
        except Exception:
            return {'months': [], 'income': [], 'expense': []}

    @staticmethod
    def get_category_breakdown(mysql, user_id):
        """
        Expense totals per category, for the donut chart.

        Fixed 2026-08-12 (Sprint 50): previously summed t.amount raw with no
        currency conversion at all — a mixed-currency account's expenses
        skewed this chart's totals, a distinct gap from BUG-19's
        hardcoded-3-currency issue (this method didn't call rate_case_sql()
        at all). Also excludes is_transfer rows (BUG-18) — transfers have no
        category_id, so they were previously inflating "Uncategorized".
        """
        from utils.currency import get_rate_map, rate_case_sql, rate_case_params
        try:
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(c.name, 'Uncategorized'), COALESCE(c.color, '#6c757d'), SUM({case_sql}) "
                f"FROM transactions t LEFT JOIN categories c ON t.category_id = c.id "
                f"LEFT JOIN accounts a ON t.account_id = a.id "
                f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE "
                f"GROUP BY t.category_id, c.name, c.color ORDER BY SUM({case_sql}) DESC",
                tuple(rate_case_params(rate_map) * 2 + [user_id])
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'name': r[0], 'color': r[1], 'total': float(r[2])} for r in rows]
        except Exception:
            return []

    ANOMALY_WINDOW_MONTHS = 4    # 3-month baseline + the current month
    MOVING_AVG_WINDOW = 3
    ANOMALY_THRESHOLD_PCT = 30.0

    @staticmethod
    def get_average_amount(mysql, user_id, type):
        """
        Sprint 26 follow-up: average transaction amount for this user/type,
        used to flag an AI-proposed amount as unusually large before the
        user confirms it (routes/api/ai_advisor.py) — defense-in-depth on
        top of the confirmation gate itself, not a replacement for it.
        Returns None if there's no history to compare against.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT AVG(amount) FROM transactions WHERE user_id = %s AND type = %s",
                (user_id, type)
            )
            avg = cursor.fetchone()[0]
            cursor.close()
            return float(avg) if avg is not None else None
        except Exception:
            return None

    @staticmethod
    def get_monthly_anomalies(mysql, user_id):
        """
        Relocated from routes/api/reports_data.py's private _monthly_anomalies()
        in Sprint 25, so the new AI-insight scheduler job can reuse it without
        importing from a routes module (every other scheduled job in this
        codebase only imports from models/). Behavior unchanged from Sprint 20.

        Flags categories whose most recent month's expense total is at least
        ANOMALY_THRESHOLD_PCT above their own MOVING_AVG_WINDOW-month trailing
        average, looking at the last ANOMALY_WINDOW_MONTHS months.
        """
        from utils.currency import get_rate_map, rate_case_sql, rate_case_params
        try:
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
            start = str(datetime.now().date() - timedelta(days=30 * Transaction.ANOMALY_WINDOW_MONTHS))
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, "
                f"COALESCE(c.name, 'Uncategorized') AS category, SUM({case_sql}) AS total "
                f"FROM transactions t "
                f"LEFT JOIN categories c ON t.category_id = c.id "
                f"LEFT JOIN accounts a ON t.account_id = a.id "
                f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE AND t.transaction_date >= %s "
                f"GROUP BY month, t.category_id, c.name ORDER BY month ASC",
                tuple(rate_case_params(rate_map) + [user_id, start])
            )
            rows = cursor.fetchall()
            cursor.close()
        except Exception:
            return []

        by_cat = {}
        for month, cat, total in rows:
            by_cat.setdefault(cat, {})[month] = float(total)

        current_month_key = datetime.now().strftime('%Y-%m')
        anomalies = []
        for cat, months in by_cat.items():
            if current_month_key not in months:
                continue
            prior_months = sorted(m for m in months if m != current_month_key)[-Transaction.MOVING_AVG_WINDOW:]
            if len(prior_months) < Transaction.MOVING_AVG_WINDOW:
                continue
            baseline = sum(months[m] for m in prior_months) / Transaction.MOVING_AVG_WINDOW
            if baseline <= 0:
                continue
            current = months[current_month_key]
            pct_above = (current - baseline) / baseline * 100
            if pct_above >= Transaction.ANOMALY_THRESHOLD_PCT:
                anomalies.append({
                    'category': cat, 'current': round(current, 2),
                    'average': round(baseline, 2), 'pct_above': round(pct_above, 1),
                })

        anomalies.sort(key=lambda a: a['pct_above'], reverse=True)
        return anomalies

    @staticmethod
    def _from_row(row):
        return Transaction(
            transaction_id=row[0],
            user_id=row[1],
            category_id=row[2],
            type=row[3],
            amount=float(row[4]) if row[4] is not None else 0.0,
            description=row[5],
            transaction_date=row[6],
            account_id=row[7] if len(row) > 7 else None,
            recurring_transaction_id=row[8] if len(row) > 8 else None,
            loan_id=row[9] if len(row) > 9 else None,
            is_transfer=bool(row[10]) if len(row) > 10 else False,
        )
