"""
Aura Financial Tracker - Secure Version
Impersonation Log Model
Sprint 57 (ENH-02, group 6): audit trail for the admin "View As" feature.
"""


class ImpersonationLog:
    @staticmethod
    def create(mysql, admin_id, target_user_id):
        """Logs the start of an impersonation session. Returns the new
        log row's id (needed by mark_ended() later), or None on failure —
        the caller should still proceed with the impersonation itself even
        if logging fails (never let audit-log bookkeeping block the
        underlying action), but the id is unavailable to close out later
        in that case."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO impersonation_log (admin_id, target_user_id) VALUES (%s, %s)",
                (admin_id, target_user_id)
            )
            mysql.connection.commit()
            log_id = cursor.lastrowid
            cursor.close()
            return log_id
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def mark_ended(mysql, log_id):
        if not log_id:
            return
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE impersonation_log SET ended_at = NOW() WHERE id = %s", (log_id,))
            mysql.connection.commit()
            cursor.close()
        except Exception:
            mysql.connection.rollback()

    @staticmethod
    def get_recent(mysql, limit=25):
        """Sprint 57: admin panel's audit view — most recent impersonation
        events, joined to both usernames for display. Includes
        still-active sessions (ended_at IS NULL) so an admin who forgot to
        "Return to Admin" (closed the tab instead) is visible, not hidden."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT il.id, a.username AS admin_username, t.username AS target_username, "
                "il.started_at, il.ended_at "
                "FROM impersonation_log il "
                "JOIN users a ON a.id = il.admin_id "
                "JOIN users t ON t.id = il.target_user_id "
                "ORDER BY il.started_at DESC LIMIT %s",
                (int(limit),)
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []
