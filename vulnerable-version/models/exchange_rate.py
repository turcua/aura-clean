"""
Aura Financial Tracker - Vulnerable Version
Exchange Rate Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 17: Multi-Currency (static rates)
"""


class ExchangeRate:
    def __init__(self, id=None, currency_code=None, rate_to_base=None, updated_at=None):
        self.id = id
        self.currency_code = currency_code
        self.rate_to_base = rate_to_base
        self.updated_at = updated_at

    @staticmethod
    def get_all(mysql):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, currency_code, rate_to_base, updated_at FROM exchange_rates "
                "ORDER BY currency_code"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [ExchangeRate._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update_rate(mysql, currency_code, rate_to_base):
        """
        VULN-064: no bounds/type check on rate_to_base — negative, zero, or
        absurdly large values are accepted and committed as-is.
        VULN-066: currency_code is not restricted to EUR/USD/IDR — arbitrary
        text (including HTML/JS) is accepted.

        VULN-065 removed (Sprint 17 hotfix, explicit user request,
        2026-07-25): this used to always INSERT (no UNIQUE constraint
        existed on currency_code), so editing an existing rate created a
        duplicate row instead of updating it. A UNIQUE constraint was added
        via init-vulnerable-sprint17-hotfix.sql and this now upserts —
        SQL injection on currency_code/rate_to_base remains, since both are
        still concatenated directly into the query string.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection remains — currency_code/rate_to_base concatenated
            query = f"""
                INSERT INTO exchange_rates (currency_code, rate_to_base)
                VALUES ('{currency_code}', {rate_to_base})
                ON DUPLICATE KEY UPDATE rate_to_base = {rate_to_base}
            """
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Exchange rate updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, rate_id):
        """
        No auth/ownership check at this layer (enforced nowhere in this
        version). Deletes a single row by id — duplicates from the old
        VULN-065 behavior shouldn't occur anymore post-hotfix, but this
        stays id-based rather than currency_code-based regardless.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection (rate_id is taken from the URL as an int
            # by Flask's <int:> converter, so this particular call site isn't
            # exploitable, but the pattern is unparameterized like the rest
            # of this model)
            query = f"DELETE FROM exchange_rates WHERE id = {rate_id}"
            cursor.execute(query)
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Currency not found"
            return True, "Exchange rate deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def _from_row(row):
        return ExchangeRate(
            id=row[0],
            currency_code=row[1],
            rate_to_base=float(row[2]),
            updated_at=row[3],
        )
