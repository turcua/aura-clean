"""
Aura Financial Tracker - Vulnerable Version
Transfer Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""


class Transfer:
    def __init__(self, id=None, user_id=None, from_account_id=None, to_account_id=None,
                 from_transaction_id=None, to_transaction_id=None,
                 amount=None, description=None, transfer_date=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.from_account_id = from_account_id
        self.to_account_id = to_account_id
        self.from_transaction_id = from_transaction_id
        self.to_transaction_id = to_transaction_id
        self.amount = amount
        self.description = description
        self.transfer_date = transfer_date
        self.created_at = created_at

    @staticmethod
    def create(mysql, user_id, from_account_id, to_account_id, amount, description, transfer_date,
               recurring_transaction_id=None):
        """
        Creates two linked transactions and one transfer record, then updates both balances.
        VULNERABILITY: SQL Injection throughout
        VULNERABILITY: IDOR - no check that accounts belong to user
        VULNERABILITY: No check that from_account_id != to_account_id (self-transfer)
        VULNERABILITY: No check that from_account has sufficient balance
        VULNERABILITY: Mass assignment (user_id from request)

        Sprint 17: converts `amount` from from_account's currency to
        to_account's currency (via the saved exchange rates) before crediting
        the destination side — same currency-mixing fix as secure-version,
        minus the ownership check on the currency lookup (IDOR, as everywhere
        else in this model).
        """
        try:
            from utils.currency import get_rate_map, convert, BASE_CURRENCY

            # amount arrives as a raw string from the request body (this
            # version never casts it — it used to only ever be used inside
            # f-string SQL, where that doesn't matter). The conversion math
            # below does real Python arithmetic, so it needs an actual
            # number here; this is a plain type fix, not new validation —
            # no bounds/sanity checks are added.
            amount = float(amount)

            cursor = mysql.connection.cursor()
            desc = description or 'Transfer'
            recur_val = recurring_transaction_id if recurring_transaction_id else 'NULL'

            # VULN: SQL Injection, IDOR — no user_id check on the currency lookup
            cursor.execute(f"SELECT id, currency FROM accounts WHERE id IN ({from_account_id}, {to_account_id})")
            # Keys normalized to str: row[0] comes back as an int from MySQL,
            # but from_account_id/to_account_id arrive as strings from the
            # request body (mass assignment, no int() cast anywhere in this
            # version) — comparing int keys against string lookups silently
            # missed every time, defaulting both currencies to 'RON' and
            # making every transfer a 1:1 copy regardless of actual currency.
            currencies = {str(row[0]): row[1] for row in cursor.fetchall()}
            from_currency = currencies.get(str(from_account_id), 'RON')
            to_currency = currencies.get(str(to_account_id), 'RON')

            rate_map = get_rate_map(mysql)
            received_amount = convert(amount, from_currency, to_currency, rate_map)
            amount_in_ron = convert(amount, from_currency, BASE_CURRENCY, rate_map)

            # VULN: SQL Injection - create debit transaction (expense side)
            cursor.execute(f"""
                INSERT INTO transactions
                    (user_id, category_id, type, amount, description, transaction_date,
                     account_id, is_transfer, recurring_transaction_id)
                VALUES
                    ({user_id}, NULL, 'expense', {amount}, '{desc}', '{transfer_date}',
                     {from_account_id}, TRUE, {recur_val})
            """)
            from_tx_id = cursor.lastrowid

            # VULN: SQL Injection - create credit transaction (income side)
            cursor.execute(f"""
                INSERT INTO transactions
                    (user_id, category_id, type, amount, description, transaction_date,
                     account_id, is_transfer, recurring_transaction_id)
                VALUES
                    ({user_id}, NULL, 'income', {received_amount}, '{desc}', '{transfer_date}',
                     {to_account_id}, TRUE, {recur_val})
            """)
            to_tx_id = cursor.lastrowid

            # VULN: SQL Injection - create transfer record
            cursor.execute(f"""
                INSERT INTO transfers
                    (user_id, from_account_id, to_account_id, from_transaction_id, to_transaction_id,
                     amount, description, transfer_date)
                VALUES
                    ({user_id}, {from_account_id}, {to_account_id}, {from_tx_id}, {to_tx_id},
                     {amount}, '{desc}', '{transfer_date}')
            """)
            transfer_id = cursor.lastrowid

            # Update account balances
            cursor.execute(
                f"UPDATE accounts SET current_balance = current_balance - {amount} WHERE id = {from_account_id}"
            )
            cursor.execute(
                f"UPDATE accounts SET current_balance = current_balance + {received_amount} WHERE id = {to_account_id}"
            )

            # ENH-004: Auto-update savings goals linked to destination account
            # VULNERABILITY: IDOR — queries by account_id only, no user ownership check on goal
            # VULNERABILITY: SQL Injection in to_account_id and amount
            # VULNERABILITY: current_amount can exceed target_amount (no cap enforced)
            # Goals are treated as RON throughout (Sprint 17, MC-006) — credit the
            # RON-equivalent of the transferred amount, not the raw destination-currency amount.
            cursor.execute(
                f"UPDATE savings_goals SET current_amount = current_amount + {amount_in_ron} "
                f"WHERE account_id = {to_account_id} AND status = 'active'"
            )

            mysql.connection.commit()
            cursor.close()
            return True, "Transfer completed successfully", transfer_id

        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, transfer_id):
        """VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"SELECT * FROM transfers WHERE id = {transfer_id}")
            row = cursor.fetchone()
            cursor.close()
            return Transfer._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM transfers WHERE user_id = {user_id} ORDER BY transfer_date DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Transfer._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def delete(mysql, transfer_id):
        """
        Deletes transfer record and both linked transactions, reverses balances.
        VULNERABILITY: SQL Injection, IDOR
        VULNERABILITY: No atomicity guarantee if intermediate step fails
        """
        try:
            cursor = mysql.connection.cursor()

            # Fetch transfer first to get linked data
            cursor.execute(f"SELECT * FROM transfers WHERE id = {transfer_id}")
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False, "Transfer not found"

            transfer = Transfer._from_row(row)

            # Sprint 17: to_account may have been credited a converted amount
            # (see create()) — reverse using the credit transaction's own
            # amount, not transfer.amount (which is the source-side amount).
            cursor.execute(f"SELECT amount FROM transactions WHERE id = {transfer.to_transaction_id}")
            tx_row = cursor.fetchone()
            received_amount = float(tx_row[0]) if tx_row else transfer.amount

            # Reverse balances
            cursor.execute(
                f"UPDATE accounts SET current_balance = current_balance + {transfer.amount} WHERE id = {transfer.from_account_id}"
            )
            cursor.execute(
                f"UPDATE accounts SET current_balance = current_balance - {received_amount} WHERE id = {transfer.to_account_id}"
            )

            # Delete linked transactions
            cursor.execute(f"DELETE FROM transactions WHERE id = {transfer.from_transaction_id}")
            cursor.execute(f"DELETE FROM transactions WHERE id = {transfer.to_transaction_id}")

            # Delete transfer record
            cursor.execute(f"DELETE FROM transfers WHERE id = {transfer_id}")

            mysql.connection.commit()
            cursor.close()
            return True, "Transfer deleted successfully"

        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def _from_row(row):
        return Transfer(
            id=row[0],
            user_id=row[1],
            from_account_id=row[2],
            to_account_id=row[3],
            from_transaction_id=row[4],
            to_transaction_id=row[5],
            amount=float(row[6]) if row[6] is not None else 0.0,
            description=row[7],
            transfer_date=row[8],
            created_at=row[9]
        )
