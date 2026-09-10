"""
Aura Financial Tracker - Vulnerable Version
Transaction Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 2: Thunder Breathing - Second Form
"""

from flask import current_app
from flask_mysqldb import MySQL
from datetime import datetime, timedelta

class Transaction:
    """Transaction model with intentional security vulnerabilities"""
    
    def __init__(self, transaction_id=None, user_id=None, category_id=None,
                 type=None, amount=None, description=None, transaction_date=None,
                 account_id=None, is_transfer=False, recurring_transaction_id=None, loan_id=None):
        self.id = transaction_id
        self.user_id = user_id
        self.category_id = category_id
        self.type = type  # 'income' or 'expense'
        self.amount = amount
        self.description = description
        self.transaction_date = transaction_date
        self.created_at = None
        self.updated_at = None
        self.account_id = account_id
        self.is_transfer = is_transfer
        self.recurring_transaction_id = recurring_transaction_id
        self.loan_id = loan_id
    
    @staticmethod
    def create(mysql, user_id, category_id, type, amount, description, transaction_date,
               account_id=None, is_transfer=False, recurring_transaction_id=None, external_id=None,
               loan_id=None, payment_type=None):
        """
        VULNERABILITY: SQL Injection through string concatenation
        VULNERABILITY: No input validation
        VULNERABILITY: Mass assignment (user_id can be manipulated)

        external_id (Sprint 18): OFX's FITID. No UNIQUE constraint exists on
        (account_id, external_id) in this version (see
        init-vulnerable-sprint18.sql) — dedup, if any, is left entirely to
        the caller, and even that check is itself exploitable (VULN-068/069).

        loan_id (Sprint 28): marks this transaction as an extra payment
        toward a loan. VULNERABILITY: no ownership check — any loan_id is
        accepted, same pattern as account_id/category_id in this version.

        payment_type (Sprint 51, ENH-13): 'extra' or 'scheduled', see
        Loan.get_extra_payments()'s docstring.
        """
        try:
            cursor = mysql.connection.cursor()
            acc_val = account_id if account_id else 'NULL'
            recur_val = recurring_transaction_id if recurring_transaction_id else 'NULL'
            loan_val = loan_id if loan_id else 'NULL'
            transfer_flag = 1 if is_transfer else 0
            ext_val = f"'{external_id}'" if external_id else 'NULL'
            ptype_val = f"'{payment_type}'" if payment_type else 'NULL'

            # VULN: SQL Injection - using string formatting instead of parameterized queries
            query = f"""
                INSERT INTO transactions
                    (user_id, category_id, type, amount, description, transaction_date,
                     account_id, is_transfer, recurring_transaction_id, external_id, loan_id, payment_type)
                VALUES
                    ({user_id}, {category_id if category_id else 'NULL'}, '{type}', {amount},
                     '{description}', '{transaction_date}', {acc_val}, {transfer_flag}, {recur_val}, {ext_val}, {loan_val}, {ptype_val})
            """

            cursor.execute(query)
            mysql.connection.commit()
            transaction_id = cursor.lastrowid
            cursor.close()

            # Update account balance if account is linked
            if account_id:
                from models.account import Account
                operation = 'add' if type == 'income' else 'subtract'
                Account.update_balance(mysql, account_id, amount, operation)

            return True, "Transaction created successfully", transaction_id

        except Exception as e:
            mysql.connection.rollback()
            # VULN: Detailed error message leaks database information
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def get_by_id(mysql, transaction_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification (IDOR)
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection
            # loan_id (Sprint 30): appended explicitly rather than relying on
            # its position in `*` — deterministic regardless of the table's
            # physical column order.
            query = f"SELECT *, loan_id FROM transactions WHERE id = {transaction_id}"

            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()

            if result:
                transaction = Transaction(
                    transaction_id=result[0],
                    user_id=result[1],
                    category_id=result[2],
                    type=result[3],
                    amount=result[4],
                    description=result[5],
                    transaction_date=result[6],
                    account_id=result[9] if len(result) > 9 else None,
                    is_transfer=bool(result[10]) if len(result) > 10 else False,
                    recurring_transaction_id=result[11] if len(result) > 11 else None,
                    loan_id=result[-1]
                )
                return transaction
            return None
            
        except Exception as e:
            return None
    
    @staticmethod
    def get_all_by_user(mysql, user_id, limit=None, offset=0, include_transfers=False):
        """
        VULNERABILITY: SQL Injection in user_id, limit, and offset
        VULNERABILITY: Sprint 21 added pagination, but per_page/offset are
        never clamped server-side (see routes/api/transactions.py) — the
        DOS-via-large-dataset gap this docstring already warned about still
        applies, just via a huge ?per_page= instead of no limit at all.

        ENH-06/Sprint 50: excludes is_transfer rows by default, same as
        secure-version, via a plain string-concatenated clause (matching
        this method's existing SQLi style, not parameterized).
        """
        try:
            cursor = mysql.connection.cursor()
            transfer_sql = "" if include_transfers else " AND is_transfer = FALSE"

            # VULN: SQL Injection
            if limit:
                query = f"SELECT *, loan_id FROM transactions WHERE user_id = {user_id}{transfer_sql} ORDER BY transaction_date DESC LIMIT {limit} OFFSET {offset}"
            else:
                query = f"SELECT *, loan_id FROM transactions WHERE user_id = {user_id}{transfer_sql} ORDER BY transaction_date DESC"

            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()

            transactions = []
            for row in results:
                transaction = Transaction(
                    transaction_id=row[0],
                    user_id=row[1],
                    category_id=row[2],
                    type=row[3],
                    amount=row[4],
                    description=row[5],
                    transaction_date=row[6],
                    account_id=row[9] if len(row) > 9 else None,
                    is_transfer=bool(row[10]) if len(row) > 10 else False,
                    recurring_transaction_id=row[11] if len(row) > 11 else None,
                    loan_id=row[-1]
                )
                transactions.append(transaction)

            return transactions

        except Exception as e:
            return []

    @staticmethod
    def count_by_user(mysql, user_id, include_transfers=False):
        """
        VULNERABILITY: SQL Injection in user_id.
        Total transaction count for user_id — pairs with get_all_by_user() for pagination (Sprint 21).
        """
        try:
            cursor = mysql.connection.cursor()
            transfer_sql = "" if include_transfers else " AND is_transfer = FALSE"
            # VULN: SQL Injection
            cursor.execute(f"SELECT COUNT(*) FROM transactions WHERE user_id = {user_id}{transfer_sql}")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    @staticmethod
    def update(mysql, transaction_id, user_id, category_id, type, amount, description, transaction_date, account_id=None,
               loan_id=None, payment_type=None):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification (can update any transaction)
        VULNERABILITY: Mass assignment (can change user_id)
        Note: like the vulnerable version's Transaction.delete(), this does not
        reconcile account balances when account_id/amount/type change on update —
        an intentional, pre-existing bug (see Sprint 12 dev log), not fixed here.
        loan_id (Sprint 30): no ownership check, same pattern as account_id.
        payment_type (Sprint 51, ENH-13).
        """
        try:
            cursor = mysql.connection.cursor()
            acc_val = account_id if account_id else 'NULL'
            loan_val = loan_id if loan_id else 'NULL'
            ptype_val = f"'{payment_type}'" if payment_type else 'NULL'

            # VULN: SQL Injection - no ownership check
            query = f"""
                UPDATE transactions
                SET user_id = {user_id},
                    category_id = {category_id if category_id else 'NULL'},
                    type = '{type}',
                    amount = {amount},
                    description = '{description}',
                    transaction_date = '{transaction_date}',
                    account_id = {acc_val},
                    loan_id = {loan_val},
                    payment_type = {ptype_val}
                WHERE id = {transaction_id}
            """

            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()

            return True, "Transaction updated successfully"

        except Exception as e:
            mysql.connection.rollback()
            # VULN: Detailed error messages
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def delete(mysql, transaction_id):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: No ownership verification (can delete any transaction)
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection - no ownership check
            query = f"DELETE FROM transactions WHERE id = {transaction_id}"
            
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            
            return True, "Transaction deleted successfully"
            
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def get_summary(mysql, user_id):
        """
        VULNERABILITY: SQL Injection. Currency conversion rates interpolated
        unsafely too — see utils/currency.rate_case_sql.
        Calculate total income, expenses, and balance for a user
        """
        try:
            from utils.currency import get_rate_map, rate_case_sql
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
            cursor = mysql.connection.cursor()

            # VULN: SQL Injection
            # NOTE: type/user_id must be qualified (t.type, t.user_id) — both
            # transactions and accounts have columns with these exact names,
            # so the LEFT JOIN made them ambiguous, which MySQL rejected and
            # the broad except below silently turned into "0.00 everywhere".
            query = f"""
                SELECT
                    SUM(CASE WHEN t.type = 'income' THEN {case_sql} ELSE 0 END) as total_income,
                    SUM(CASE WHEN t.type = 'expense' THEN {case_sql} ELSE 0 END) as total_expenses,
                    SUM(CASE WHEN t.type = 'income' THEN {case_sql} ELSE -({case_sql}) END) as balance
                FROM transactions t
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE t.user_id = {user_id}
                  AND t.is_transfer = FALSE
            """

            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            return {
                'total_income': float(result[0]) if result[0] else 0.0,
                'total_expenses': float(result[1]) if result[1] else 0.0,
                'balance': float(result[2]) if result[2] else 0.0
            }
            
        except Exception as e:
            return {
                'total_income': 0.0,
                'total_expenses': 0.0,
                'balance': 0.0
            }
    
    @staticmethod
    def filter_transactions(mysql, user_id, date_from=None, date_to=None, category_id=None, type=None,
                             loan_id=None, limit=None, offset=0, include_transfers=False, account_id=None):
        """
        VULNERABILITY: SQL Injection in all filter parameters (including limit/offset, Sprint 21)
        VULNERABILITY: Reflected XSS in filter parameters
        loan_id (Sprint 30): same no-ownership-check f-string pattern as category_id.
        include_transfers (Sprint 50, ENH-06): excludes is_transfer rows by
        default, same as get_all_by_user().
        account_id (Sprint 50, ENH-05): same no-ownership-check f-string
        pattern as category_id/loan_id — added for filter-UI parity with
        secure-version, which already had this filter.
        """
        try:
            cursor = mysql.connection.cursor()

            # VULN: SQL Injection - building query with string concatenation
            query = f"SELECT *, loan_id FROM transactions WHERE user_id = {user_id}"
            if not include_transfers:
                query += " AND is_transfer = FALSE"

            if date_from:
                query += f" AND transaction_date >= '{date_from}'"

            if date_to:
                query += f" AND transaction_date <= '{date_to}'"

            if category_id:
                query += f" AND category_id = {category_id}"

            if account_id:
                query += f" AND account_id = {account_id}"

            if loan_id:
                query += f" AND loan_id = {loan_id}"

            if type:
                query += f" AND type = '{type}'"

            query += " ORDER BY transaction_date DESC"

            # VULN: SQL Injection - limit/offset interpolated directly, never clamped
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()

            transactions = []
            for row in results:
                transaction = Transaction(
                    transaction_id=row[0],
                    user_id=row[1],
                    category_id=row[2],
                    type=row[3],
                    amount=row[4],
                    description=row[5],
                    transaction_date=row[6],
                    account_id=row[9] if len(row) > 9 else None,
                    is_transfer=bool(row[10]) if len(row) > 10 else False,
                    recurring_transaction_id=row[11] if len(row) > 11 else None,
                    loan_id=row[-1]
                )
                transactions.append(transaction)

            return transactions

        except Exception as e:
            return []

    @staticmethod
    def count_filtered(mysql, user_id, date_from=None, date_to=None, category_id=None, type=None, loan_id=None,
                        include_transfers=False, account_id=None):
        """
        VULNERABILITY: SQL Injection in all filter parameters.
        Total count matching the same filters as filter_transactions() — pairs with it for pagination (Sprint 21).
        """
        try:
            cursor = mysql.connection.cursor()
            query = f"SELECT COUNT(*) FROM transactions WHERE user_id = {user_id}"
            if not include_transfers:
                query += " AND is_transfer = FALSE"

            if date_from:
                query += f" AND transaction_date >= '{date_from}'"
            if date_to:
                query += f" AND transaction_date <= '{date_to}'"
            if category_id:
                query += f" AND category_id = {category_id}"
            if account_id:
                query += f" AND account_id = {account_id}"
            if loan_id:
                query += f" AND loan_id = {loan_id}"
            if type:
                query += f" AND type = '{type}'"

            cursor.execute(query)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    ANOMALY_WINDOW_MONTHS = 4    # 3-month baseline + the current month
    MOVING_AVG_WINDOW = 3
    ANOMALY_THRESHOLD_PCT = 30.0

    @staticmethod
    def get_monthly_anomalies(mysql, user_id):
        """
        Relocated from routes/api/reports_data.py's private _monthly_anomalies()
        in Sprint 25, so the new AI-insight scheduler job can reuse it without
        importing from a routes module. Behavior unchanged from Sprint 20.
        VULNERABILITY (VULN-072): SQL Injection via user_id — unchanged by the move.
        """
        from utils.currency import get_rate_map, rate_case_sql
        try:
            rate_map = get_rate_map(mysql)
            case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
            start = str(datetime.now().date() - timedelta(days=30 * Transaction.ANOMALY_WINDOW_MONTHS))
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection via user_id
            cursor.execute(f"""
                SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                       COALESCE(c.name, 'Uncategorized')        AS category,
                       SUM({case_sql})                           AS total
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE t.user_id = {user_id}
                  AND t.type = 'expense'
                  AND t.is_transfer = FALSE
                  AND t.transaction_date >= '{start}'
                GROUP BY month, t.category_id, c.name
                ORDER BY month ASC
            """)
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
