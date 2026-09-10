"""
Aura Financial Tracker - Vulnerable Version
Loan + Loan Event Models (WITH INTENTIONAL VULNERABILITIES)
Sprint 28: Loan Intelligence Foundation
"""

import json


class Loan:
    def __init__(self, id=None, user_id=None, name=None, principal=None, margin_pct=None,
                 initial_base_index_pct=None, start_date=None, original_term_months=None,
                 currency='RON', status='active', refinanced_from_loan_id=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.principal = principal
        self.margin_pct = margin_pct
        self.initial_base_index_pct = initial_base_index_pct
        self.start_date = start_date
        self.original_term_months = original_term_months
        self.currency = currency
        self.status = status
        self.refinanced_from_loan_id = refinanced_from_loan_id
        self.created_at = created_at

    @staticmethod
    def create(mysql, user_id, name, principal, margin_pct, initial_base_index_pct,
               start_date, original_term_months, currency='RON'):
        """VULNERABILITY: SQL Injection, mass assignment (user_id from request)."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"INSERT INTO loans (user_id, name, principal, margin_pct, initial_base_index_pct, "
                f"start_date, original_term_months, currency) "
                f"VALUES ({user_id}, '{name}', {principal}, {margin_pct}, {initial_base_index_pct}, "
                f"'{start_date}', {original_term_months}, '{currency}')"
            )
            mysql.connection.commit()
            loan_id = cursor.lastrowid
            cursor.close()
            return True, "Loan created successfully", loan_id
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no user_id check at all."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT id, user_id, name, principal, margin_pct, initial_base_index_pct, "
                f"start_date, original_term_months, currency, status, refinanced_from_loan_id, created_at "
                f"FROM loans WHERE id = {loan_id}"
            )
            row = cursor.fetchone()
            cursor.close()
            return Loan._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection, IDOR — any user_id returns that user's loans."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT id, user_id, name, principal, margin_pct, initial_base_index_pct, "
                f"start_date, original_term_months, currency, status, refinanced_from_loan_id, created_at "
                f"FROM loans WHERE user_id = {user_id} ORDER BY name ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Loan._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, loan_id, name, currency, margin_pct):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id
        at all, matching get_by_id()/delete()'s existing pattern for this
        class — any authenticated user can edit any other user's loan.
        Sprint 51 (ENH-01)."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"UPDATE loans SET name = '{name}', currency = '{currency}', margin_pct = {margin_pct} "
                f"WHERE id = {loan_id}"
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Loan not found"
            return True, "Loan updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id
        at all, matching update()'s pattern above. Sprint 51 (ENH-01)."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"DELETE FROM loans WHERE id = {loan_id}")
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Loan not found"
            return True, "Loan deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_payment_ledger(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id
        at all, matching get_extra_payments(). Sprint 51 (ENH-13) — display/
        audit only, never called from the projection engine."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT transaction_date, amount, type, description, payment_type "
                f"FROM transactions WHERE loan_id = {loan_id} ORDER BY transaction_date DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [
                {'date': str(r[0]), 'amount': float(r[1]), 'type': r[2], 'description': r[3], 'payment_type': r[4] or 'extra'}
                for r in rows
            ]
        except Exception:
            return []

    @staticmethod
    def get_extra_payments(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id at all.

        Filtered on payment_type since Sprint 51 (ENH-13) — same reasoning
        as secure-version's copy: scheduled (recurring) payments also carry
        loan_id now, for ledger visibility, so this needs a way to keep
        excluding them from the projection engine's extra-payment count.
        NULL payment_type (every row from before this column existed) is
        still treated as an extra payment, matching this method's exact
        pre-Sprint-51 behavior."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT transaction_date, amount, id, created_at FROM transactions "
                f"WHERE loan_id = {loan_id} AND (payment_type IS NULL OR payment_type <> 'scheduled') "
                f"ORDER BY transaction_date ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'date': r[0], 'amount': float(r[1]), 'id': r[2], 'created_at': r[3]} for r in rows]
        except Exception:
            return []

    @staticmethod
    def _from_row(row):
        return Loan(
            id=row[0], user_id=row[1], name=row[2], principal=float(row[3]),
            margin_pct=float(row[4]), initial_base_index_pct=float(row[5]),
            start_date=row[6], original_term_months=row[7], currency=row[8],
            status=row[9], refinanced_from_loan_id=row[10], created_at=row[11],
        )


class LoanEvent:
    def __init__(self, id=None, loan_id=None, event_type=None, effective_date=None,
                 payload=None, created_at=None):
        self.id = id
        self.loan_id = loan_id
        self.event_type = event_type
        self.effective_date = effective_date
        self.payload = payload
        self.created_at = created_at

    @staticmethod
    def create(mysql, loan_id, event_type, effective_date, payload):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id at all."""
        try:
            cursor = mysql.connection.cursor()
            payload_json = json.dumps(payload).replace("'", "''")
            # VULN: SQL Injection
            cursor.execute(
                f"INSERT INTO loan_events (loan_id, event_type, effective_date, payload) "
                f"VALUES ({loan_id}, '{event_type}', '{effective_date}', '{payload_json}')"
            )
            mysql.connection.commit()
            event_id = cursor.lastrowid
            cursor.close()
            return True, "Event logged successfully", event_id
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_loan(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id at all.
        Excludes soft-deleted events (Sprint 49) — same deleted_at column as
        secure-version, added the same insecure way as every other query in
        this class (unparameterized, no ownership check)."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT id, loan_id, event_type, effective_date, payload, created_at "
                f"FROM loan_events WHERE loan_id = {loan_id} AND deleted_at IS NULL "
                f"ORDER BY effective_date ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [LoanEvent._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_deleted(mysql, loan_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on loan_id
        at all, matching get_by_loan(). Sprint 49."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT id, loan_id, event_type, effective_date, payload, created_at "
                f"FROM loan_events WHERE loan_id = {loan_id} AND deleted_at IS NOT NULL "
                f"ORDER BY deleted_at DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [LoanEvent._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def delete(mysql, event_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on event_id
        at all, matching create()/get_by_loan()'s existing pattern for this
        class — any authenticated user can delete any other user's loan event.

        Soft-delete since Sprint 49 (marks deleted_at instead of removing the
        row, matching secure-version's recovery behavior) — the vulnerable
        SQL injection / missing-ownership-check pattern is otherwise
        unchanged: still an f-string UPDATE, still no user_id/loan_id scoping."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"UPDATE loan_events SET deleted_at = NOW() WHERE id = {event_id} AND deleted_at IS NULL")
            mysql.connection.commit()
            deleted = cursor.rowcount > 0
            cursor.close()
            if not deleted:
                return False, "Event not found"
            return True, "Event deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def restore(mysql, event_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on event_id
        at all, matching delete(). Sprint 49."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"UPDATE loan_events SET deleted_at = NULL WHERE id = {event_id} AND deleted_at IS NOT NULL")
            mysql.connection.commit()
            restored = cursor.rowcount > 0
            cursor.close()
            if not restored:
                return False, "Event not found"
            return True, "Event restored successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def _from_row(row):
        payload = row[4]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return LoanEvent(
            id=row[0], loan_id=row[1], event_type=row[2], effective_date=row[3],
            payload=payload, created_at=row[5],
        )
