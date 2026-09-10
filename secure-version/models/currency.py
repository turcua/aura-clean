"""
Aura Financial Tracker - Secure Version
Currency Reference Model
Sprint 17 follow-up: dynamic currency list

Security properties: currency_code validated as exactly 3 uppercase ASCII
letters before any query runs (defense in depth alongside the DB-level
CHECK); duplicate codes rejected via the PRIMARY KEY; create() creates the
currency and its starter exchange rate atomically — no way to end up with
one but not the other; all queries parameterized.
"""

import re

CODE_PATTERN = re.compile(r'^[A-Z]{3}$')
MAX_RATE = 1_000_000


class Currency:
    def __init__(self, code=None, is_base=False, created_at=None):
        self.code = code
        self.is_base = is_base
        self.created_at = created_at

    @staticmethod
    def get_all(mysql):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT code, is_base, created_at FROM currencies ORDER BY is_base DESC, code")
            rows = cursor.fetchall()
            cursor.close()
            return [Currency._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def create(mysql, code, initial_rate_to_base):
        """Creates a new non-base currency plus its starter exchange rate, in one transaction."""
        code = (code or '').strip().upper()
        if not CODE_PATTERN.match(code):
            return False, "Currency code must be exactly 3 uppercase letters (e.g. GBP)", None
        if code == 'RON':
            return False, "RON is already the base currency", None

        try:
            rate = round(float(initial_rate_to_base), 6)
        except (TypeError, ValueError):
            return False, "Initial rate must be a number", None
        if not (0 < rate <= MAX_RATE):
            return False, f"Initial rate must be greater than 0 and at most {MAX_RATE}", None

        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO currencies (code, is_base) VALUES (%s, FALSE)", (code,))
            cursor.execute(
                "INSERT INTO exchange_rates (currency_code, rate_to_base) VALUES (%s, %s)",
                (code, rate)
            )
            mysql.connection.commit()
            cursor.close()
            return True, f"Currency {code} added successfully", code
        except Exception as e:
            mysql.connection.rollback()
            if 'Duplicate entry' in str(e):
                return False, f"Currency {code} already exists", None
            return False, "Could not add currency", None

    @staticmethod
    def _from_row(row):
        return Currency(code=row[0], is_base=bool(row[1]), created_at=row[2])
