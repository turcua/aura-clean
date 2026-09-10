"""
Aura Financial Tracker - Secure Version
AI Pending Action Model
Sprint 26: Excessive Agency

Security properties:
- All queries parameterized
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) on
  every read/update — a pending action can only ever be looked up, confirmed,
  or cancelled by the user it belongs to
- action_params stored as JSON exactly as proposed by the AI, but this is
  never trusted at confirm time — routes/api/ai_advisor.py's confirm-action
  independently re-validates every field against real ownership/sanity
  checks before executing anything
"""

import json


class AIPendingAction:
    def __init__(self, id=None, user_id=None, action_type=None, action_params=None,
                 status='pending', created_at=None, resolved_at=None):
        self.id = id
        self.user_id = user_id
        self.action_type = action_type
        self.action_params = action_params
        self.status = status
        self.created_at = created_at
        self.resolved_at = resolved_at

    @staticmethod
    def create(mysql, user_id, action_type, action_params):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO ai_pending_actions (user_id, action_type, action_params) "
                "VALUES (%s, %s, %s)",
                (user_id, action_type, json.dumps(action_params))
            )
            mysql.connection.commit()
            action_id = cursor.lastrowid
            cursor.close()
            return True, action_id
        except Exception:
            mysql.connection.rollback()
            return False, None

    @staticmethod
    def get_by_id(mysql, action_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, action_type, action_params, status, created_at, resolved_at "
                "FROM ai_pending_actions WHERE id = %s AND user_id = %s",
                (action_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return AIPendingAction._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def mark_resolved(mysql, action_id, user_id, status):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE ai_pending_actions SET status = %s, resolved_at = NOW() "
                "WHERE id = %s AND user_id = %s AND status = 'pending'",
                (status, action_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def _from_row(row):
        params = row[3]
        if isinstance(params, str):
            params = json.loads(params)
        return AIPendingAction(
            id=row[0], user_id=row[1], action_type=row[2], action_params=params,
            status=row[4], created_at=row[5], resolved_at=row[6],
        )
