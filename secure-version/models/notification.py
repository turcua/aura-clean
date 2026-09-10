"""
Aura Financial Tracker - Secure Version
Notification Model
Sprint 21: In-App Notifications

Security properties (contrast with vulnerable-version/models/notification.py):
- All queries parameterized — no f-string SQL anywhere
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s) on
  every read/update — vulnerable-version's mark_read()/dismiss() accept any
  notification_id with no ownership check (IDOR)
- Dedup enforced at the DB level via UNIQUE(user_id, dedupe_key) — a
  duplicate insert fails atomically rather than relying on a
  SELECT-then-INSERT race (which vulnerable-version does)
"""


class Notification:
    def __init__(self, id=None, user_id=None, type=None, title=None, message=None,
                 dedupe_key=None, is_read=False, dismissed_at=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.type = type
        self.title = title
        self.message = message
        self.dedupe_key = dedupe_key
        self.is_read = is_read
        self.dismissed_at = dismissed_at
        self.created_at = created_at

    @staticmethod
    def create_if_not_exists(mysql, user_id, type_, title, message, dedupe_key):
        """
        Scheduler-internal. Relies on UNIQUE(user_id, dedupe_key) — a repeat
        call for the same underlying event (same budget category still over
        limit, same bill not yet paid) hits the constraint and is treated as
        a no-op, not an error.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO notifications (user_id, type, title, message, dedupe_key) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, type_, title, message, dedupe_key)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            mysql.connection.rollback()
            if 'Duplicate entry' in str(e):
                return False
            return False

    @staticmethod
    def get_visible_by_user(mysql, user_id, limit=50):
        """Not-dismissed notifications for user_id, newest first."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, type, title, message, dedupe_key, is_read, dismissed_at, created_at "
                "FROM notifications WHERE user_id = %s AND dismissed_at IS NULL "
                "ORDER BY created_at DESC LIMIT %s",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [Notification._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_unread_count(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE AND dismissed_at IS NULL",
                (user_id,)
            )
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    @staticmethod
    def mark_read(mysql, notification_id, user_id, is_read=True):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE notifications SET is_read = %s WHERE id = %s AND user_id = %s",
                (is_read, notification_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def dismiss(mysql, notification_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE notifications SET dismissed_at = NOW() WHERE id = %s AND user_id = %s",
                (notification_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete_all(mysql, user_id):
        """Permanently deletes every notification for user_id (not a soft
        dismiss — this actually removes the rows)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def mark_all_read(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE",
                (user_id,)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def _from_row(row):
        return Notification(
            id=row[0], user_id=row[1], type=row[2], title=row[3], message=row[4],
            dedupe_key=row[5], is_read=bool(row[6]), dismissed_at=row[7], created_at=row[8],
        )
