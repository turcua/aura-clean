"""
Aura Financial Tracker - Secure Version
Transfer Model
Sprint 13: Transfers + Budgets + Savings Goals

Security properties (contrast with vulnerable-version/models/transfer.py):
- All queries parameterized
- Ownership of both accounts is verified by the caller (routes/api/transfers.py)
  before create() runs; the balance UPDATEs here are additionally scoped to
  `id = %s AND user_id = %s` as a second line of defense
- CHECK constraints in the schema: amount > 0, from_account_id != to_account_id
- No mass assignment — user_id never accepted as a parameter to any method
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
    def create(mysql, user_id, from_account_id, to_account_id, amount, description, transfer_date):
        """
        Creates two linked transactions (debit + credit) and one transfer record,
        then updates both account balances. Both accounts must already be
        confirmed as owned by user_id by the caller. Returns (success, message, transfer_id).

        Sprint 17 (MC-005 follow-up): if the two accounts are in different
        currencies, `amount` (in from_account's currency) is converted via
        the saved exchange rates before crediting to_account — the debit
        transaction/balance uses the original amount, the credit
        transaction/balance uses the converted amount. `transfers.amount`
        keeps its original meaning: the amount that left the source account.
        """
        try:
            from utils.currency import get_rate_map, convert

            cursor = mysql.connection.cursor()
            desc = description or 'Transfer'

            cursor.execute(
                "SELECT id, currency FROM accounts WHERE id IN (%s, %s) AND user_id = %s",
                (from_account_id, to_account_id, user_id)
            )
            currencies = {row[0]: row[1] for row in cursor.fetchall()}
            from_currency = currencies.get(from_account_id, 'RON')
            to_currency = currencies.get(to_account_id, 'RON')

            rate_map = get_rate_map(mysql)
            received_amount = convert(amount, from_currency, to_currency, rate_map)
            if received_amount is None:
                cursor.close()
                return False, "No exchange rate available to convert between these currencies", None
            received_amount = round(received_amount, 2)

            cursor.execute(
                "INSERT INTO transactions (user_id, category_id, type, amount, description, transaction_date, account_id, is_transfer) "
                "VALUES (%s, NULL, 'expense', %s, %s, %s, %s, TRUE)",
                (user_id, amount, desc, transfer_date, from_account_id)
            )
            from_tx_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO transactions (user_id, category_id, type, amount, description, transaction_date, account_id, is_transfer) "
                "VALUES (%s, NULL, 'income', %s, %s, %s, %s, TRUE)",
                (user_id, received_amount, desc, transfer_date, to_account_id)
            )
            to_tx_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO transfers (user_id, from_account_id, to_account_id, from_transaction_id, to_transaction_id, amount, description, transfer_date) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, from_account_id, to_account_id, from_tx_id, to_tx_id, amount, desc, transfer_date)
            )
            transfer_id = cursor.lastrowid

            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance - %s WHERE id = %s AND user_id = %s",
                (amount, from_account_id, user_id)
            )
            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance + %s WHERE id = %s AND user_id = %s",
                (received_amount, to_account_id, user_id)
            )

            mysql.connection.commit()
            cursor.close()
            return True, "Transfer completed successfully", transfer_id
        except Exception as e:
            mysql.connection.rollback()
            from flask import current_app
            current_app.logger.exception("Transfer.create failed")
            if 'chk_transfer' in str(e):
                return False, "Amount must be positive and the two accounts must differ", None
            return False, "Could not complete transfer", None

    @staticmethod
    def get_by_id(mysql, transfer_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, from_account_id, to_account_id, from_transaction_id, to_transaction_id, "
                "amount, description, transfer_date, created_at "
                "FROM transfers WHERE id = %s AND user_id = %s",
                (transfer_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Transfer._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, from_account_id, to_account_id, from_transaction_id, to_transaction_id, "
                "amount, description, transfer_date, created_at "
                "FROM transfers WHERE user_id = %s ORDER BY transfer_date DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Transfer._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def delete(mysql, transfer_id, user_id):
        """
        Reverses both balances, deletes both linked transactions and the
        transfer record. Ownership-scoped.

        Sprint 17: transfer.amount is the source-side (from_account) amount
        only — the destination side may have been credited a converted
        amount (see create()). The credit transaction's own `amount` is the
        source of truth for how much to reverse on to_account.
        """
        try:
            transfer = Transfer.get_by_id(mysql, transfer_id, user_id)
            if not transfer:
                return False, "Transfer not found or you don't have permission to delete it"

            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT amount FROM transactions WHERE id = %s AND user_id = %s",
                (transfer.to_transaction_id, user_id)
            )
            row = cursor.fetchone()
            received_amount = float(row[0]) if row else transfer.amount

            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance + %s WHERE id = %s AND user_id = %s",
                (transfer.amount, transfer.from_account_id, user_id)
            )
            cursor.execute(
                "UPDATE accounts SET current_balance = current_balance - %s WHERE id = %s AND user_id = %s",
                (received_amount, transfer.to_account_id, user_id)
            )
            cursor.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s",
                (transfer.from_transaction_id, user_id)
            )
            cursor.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s",
                (transfer.to_transaction_id, user_id)
            )
            cursor.execute(
                "DELETE FROM transfers WHERE id = %s AND user_id = %s",
                (transfer_id, user_id)
            )

            mysql.connection.commit()
            cursor.close()
            return True, "Transfer deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete transfer"

    @staticmethod
    def get_average_amount(mysql, user_id):
        """Sprint 26 follow-up: average transfer amount for this user, used
        to flag an AI-proposed transfer as unusually large before
        confirmation. Returns None if there's no history to compare against."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT AVG(amount) FROM transfers WHERE user_id = %s",
                (user_id,)
            )
            avg = cursor.fetchone()[0]
            cursor.close()
            return float(avg) if avg is not None else None
        except Exception:
            return None

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
            created_at=row[9],
        )
