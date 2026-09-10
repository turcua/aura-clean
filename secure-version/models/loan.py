"""
Aura Financial Tracker - Secure Version
Loan + Loan Event Models
Sprint 28: Loan Intelligence Foundation

Security properties (contrast with vulnerable-version/models/loan.py):
- All queries parameterized — no string interpolation
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) on
  every loan read/update
- LoanEvent ownership verified via a JOIN back to loans.user_id, not just
  trusting loan_id — same pattern as Budget.get_category_limits()
- No mass assignment — user_id never accepted as a parameter to update-style methods
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
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO loans (user_id, name, principal, margin_pct, initial_base_index_pct, "
                "start_date, original_term_months, currency) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, name, principal, margin_pct, initial_base_index_pct,
                 start_date, original_term_months, currency)
            )
            mysql.connection.commit()
            loan_id = cursor.lastrowid
            cursor.close()
            return True, "Loan created successfully", loan_id
        except Exception:
            mysql.connection.rollback()
            return False, "Could not create loan", None

    @staticmethod
    def get_by_id(mysql, loan_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, principal, margin_pct, initial_base_index_pct, "
                "start_date, original_term_months, currency, status, refinanced_from_loan_id, created_at "
                "FROM loans WHERE id = %s AND user_id = %s",
                (loan_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return Loan._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, name, principal, margin_pct, initial_base_index_pct, "
                "start_date, original_term_months, currency, status, refinanced_from_loan_id, created_at "
                "FROM loans WHERE user_id = %s ORDER BY name ASC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Loan._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, loan_id, user_id, name, currency, margin_pct):
        """
        Sprint 51 (ENH-01): only name/currency/margin_pct are editable —
        principal/start_date/original_term_months are deliberately excluded
        from this method's signature entirely (not just left unchanged),
        since project() replays every projection from those values and the
        Baseline track's meaning could become confusing if they changed
        after events (rate changes, snapshots, extra payments) already
        exist. If one of those three is wrong, delete and recreate the loan
        instead — confirmed with user during Sprint 51 planning.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE loans SET name = %s, currency = %s, margin_pct = %s WHERE id = %s AND user_id = %s",
                (name, currency, margin_pct, loan_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Loan not found or you don't have permission to edit it"
            return True, "Loan updated successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not update loan"

    @staticmethod
    def delete(mysql, loan_id, user_id):
        """
        Ownership-scoped. Safe by schema design (Sprint 51): loan_events
        cascades (ON DELETE CASCADE), transactions.loan_id and
        recurring_transactions.loan_id both SET NULL — deleting a loan
        cleanly unlinks its tagged transactions rather than deleting them.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM loans WHERE id = %s AND user_id = %s", (loan_id, user_id))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Loan not found or you don't have permission to delete it"
            return True, "Loan deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete loan"

    @staticmethod
    def get_extra_payments(mysql, loan_id, user_id):
        """
        Extra payments for this loan, sourced from ordinary transactions
        tagged with loan_id — not a loan_events row (see module docstring
        and Release 8's scope decisions). Ownership double-checked here too
        (loan_id = %s AND user_id = %s), not just relying on the caller
        having already verified the loan.

        Filtered on payment_type since Sprint 51 (ENH-13): once scheduled
        (recurring) payments also started carrying loan_id, for ledger
        visibility, this method needed a way to keep excluding them —
        otherwise every scheduled payment would be double-counted as an
        extra payment here AND accounted for again via project()'s own
        scheduled_principal, reintroducing the exact double-count bug fixed
        2026-08-07/2026-08-12. Deliberately `<> 'scheduled'` rather than
        `= 'extra'`: a NULL payment_type (every row created before this
        column existed, or any future caller that doesn't set it) is
        treated as an extra payment, matching this method's exact behavior
        before Sprint 51 — so the one-time backfill's timing relative to
        this code's deploy doesn't affect correctness either way.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT transaction_date, amount, id, created_at FROM transactions "
                "WHERE loan_id = %s AND user_id = %s "
                "AND (payment_type IS NULL OR payment_type <> 'scheduled') "
                "ORDER BY transaction_date ASC",
                (loan_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'date': r[0], 'amount': float(r[1]), 'id': r[2], 'created_at': r[3]} for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_payment_ledger(mysql, loan_id, user_id):
        """
        Sprint 51 (ENH-13) — every real transaction tied to this loan, extra
        and scheduled together, for display/audit only. Deliberately
        separate from get_extra_payments() (which the projection engine
        reads and must stay narrowly scoped) — this method is never called
        from utils/loan_engine.py or anywhere near project().
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT transaction_date, amount, type, description, payment_type "
                "FROM transactions WHERE loan_id = %s AND user_id = %s "
                "ORDER BY transaction_date DESC",
                (loan_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [
                {
                    'date': str(r[0]), 'amount': float(r[1]), 'type': r[2],
                    'description': r[3], 'payment_type': r[4] or 'extra',
                }
                for r in rows
            ]
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
    def create(mysql, loan_id, user_id, event_type, effective_date, payload):
        """Ownership verified via the JOIN before the INSERT — a loan_id
        that isn't the caller's own never gets an event attached to it."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM loans WHERE id = %s AND user_id = %s", (loan_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return False, "Loan not found or you don't have permission", None
            cursor.execute(
                "INSERT INTO loan_events (loan_id, event_type, effective_date, payload) "
                "VALUES (%s, %s, %s, %s)",
                (loan_id, event_type, effective_date, json.dumps(payload))
            )
            mysql.connection.commit()
            event_id = cursor.lastrowid
            cursor.close()
            return True, "Event logged successfully", event_id
        except Exception:
            mysql.connection.rollback()
            return False, "Could not log event", None

    @staticmethod
    def get_by_loan(mysql, loan_id, user_id):
        """Ownership verified via the JOIN back to loans.user_id, not just
        trusting loan_id — same pattern as Budget.get_category_limits().
        Excludes soft-deleted events (Sprint 49) so a deleted snapshot stops
        affecting projections/timeline immediately, without losing the row."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT e.id, e.loan_id, e.event_type, e.effective_date, e.payload, e.created_at "
                "FROM loan_events e JOIN loans l ON e.loan_id = l.id "
                "WHERE e.loan_id = %s AND l.user_id = %s AND e.deleted_at IS NULL "
                "ORDER BY e.effective_date ASC",
                (loan_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [LoanEvent._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_deleted(mysql, loan_id, user_id):
        """Soft-deleted events for this loan, most recently deleted first —
        same ownership-JOIN pattern as get_by_loan(). Sprint 49."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT e.id, e.loan_id, e.event_type, e.effective_date, e.payload, e.created_at "
                "FROM loan_events e JOIN loans l ON e.loan_id = l.id "
                "WHERE e.loan_id = %s AND l.user_id = %s AND e.deleted_at IS NOT NULL "
                "ORDER BY e.deleted_at DESC",
                (loan_id, user_id)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [LoanEvent._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def delete(mysql, event_id, loan_id, user_id):
        """Ownership verified via the JOIN back to loans.user_id, matching
        create()/get_by_loan()'s existing pattern — an event_id that isn't
        actually attached to one of the caller's own loans is never deleted
        (rowcount stays 0 rather than erroring, so a mismatched loan_id vs.
        event_id also fails safely here).

        Soft-delete since Sprint 49: marks deleted_at rather than removing
        the row, so it can be recovered via restore() with no time limit —
        replaces the old 5-second client-side undo toast as the real
        recovery path, found necessary after a real snapshot deletion
        (2026-08-12) needed to be undone well after that window would have
        closed. Only touches rows not already deleted, so calling this
        twice on the same event_id fails safely (rowcount 0) rather than
        overwriting an earlier deleted_at."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE loan_events e JOIN loans l ON e.loan_id = l.id "
                "SET e.deleted_at = NOW() "
                "WHERE e.id = %s AND e.loan_id = %s AND l.user_id = %s AND e.deleted_at IS NULL",
                (event_id, loan_id, user_id)
            )
            mysql.connection.commit()
            deleted = cursor.rowcount > 0
            cursor.close()
            if not deleted:
                return False, "Event not found or you don't have permission"
            return True, "Event deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete event"

    @staticmethod
    def restore(mysql, event_id, loan_id, user_id):
        """Undo a soft-delete — same ownership-JOIN pattern as delete().
        Only touches rows that are actually deleted, so restoring an
        event_id that was never deleted (or already restored) fails safely
        (rowcount 0) rather than being a no-op success. Sprint 49."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE loan_events e JOIN loans l ON e.loan_id = l.id "
                "SET e.deleted_at = NULL "
                "WHERE e.id = %s AND e.loan_id = %s AND l.user_id = %s AND e.deleted_at IS NOT NULL",
                (event_id, loan_id, user_id)
            )
            mysql.connection.commit()
            restored = cursor.rowcount > 0
            cursor.close()
            if not restored:
                return False, "Event not found or you don't have permission"
            return True, "Event restored successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not restore event"

    @staticmethod
    def _from_row(row):
        payload = row[4]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return LoanEvent(
            id=row[0], loan_id=row[1], event_type=row[2], effective_date=row[3],
            payload=payload, created_at=row[5],
        )
