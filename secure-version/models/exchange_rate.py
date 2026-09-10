"""
Aura Financial Tracker - Secure Version
Exchange Rate Model
Sprint 17: Multi-Currency (static rates)

Security properties (contrast with vulnerable-version/models/exchange_rate.py):
- All queries parameterized (%s placeholders) — no string interpolation
- currency_code validated against the currencies table (excluding the base
  currency) before any query runs, backed by the DB-level FOREIGN KEY and
  chk_rate_currency_not_base CHECK as defense in depth. The valid set is
  dynamic (Sprint 17 follow-up: currencies can be added via Currency.create()
  without a schema change) rather than a fixed tuple.
- rate_to_base validated as a positive, bounded number before any query runs,
  backed by the DB-level CHECK (rate_to_base > 0) as defense in depth
- No mass assignment — update_rate() only ever touches rate_to_base
"""

MAX_RATE = 1_000_000


def _non_base_currency_codes(mysql):
    from models.currency import Currency
    return {c.code for c in Currency.get_all(mysql) if not c.is_base}


class ExchangeRate:
    def __init__(self, currency_code=None, rate_to_base=None, updated_at=None):
        self.currency_code = currency_code
        self.rate_to_base = rate_to_base
        self.updated_at = updated_at

    @staticmethod
    def get_all(mysql):
        """Returns all non-base currency rates. RON (base, 1.0) is implicit and not stored."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT currency_code, rate_to_base, updated_at FROM exchange_rates "
                "ORDER BY currency_code"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [ExchangeRate._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update_rate(mysql, currency_code, rate_to_base):
        """Updates the rate for an existing supported currency. Returns (success, message)."""
        if currency_code not in _non_base_currency_codes(mysql):
            return False, "Unsupported currency code"
        try:
            rate = round(float(rate_to_base), 6)
        except (TypeError, ValueError):
            return False, "rate_to_base must be a number"
        if not (0 < rate <= MAX_RATE):
            return False, f"rate_to_base must be greater than 0 and at most {MAX_RATE}"

        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE exchange_rates SET rate_to_base = %s WHERE currency_code = %s",
                (rate, currency_code)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Currency not found"
            return True, "Exchange rate updated successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not update exchange rate"

    @staticmethod
    def delete(mysql, currency_code):
        """Removes a currency's rate row. Returns (success, message)."""
        if currency_code not in _non_base_currency_codes(mysql):
            return False, "Unsupported currency code"
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM exchange_rates WHERE currency_code = %s", (currency_code,))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Currency not found"
            return True, "Exchange rate deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete exchange rate"

    @staticmethod
    def _from_row(row):
        return ExchangeRate(
            currency_code=row[0],
            rate_to_base=float(row[1]),
            updated_at=row[2],
        )
