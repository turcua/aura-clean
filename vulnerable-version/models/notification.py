"""
Aura Financial Tracker - Vulnerable Version
Notification Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 21: In-App Notifications
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
        Scheduler-internal.
        VULNERABILITY: no UNIQUE constraint backing this — a SELECT-then-INSERT
        check in application code only (TOCTOU race if the job ever ran
        concurrently), consistent with this version's established pattern
        of skipping DB-level integrity enforcement.
        VULNERABILITY: SQL Injection — title/message/dedupe_key interpolated directly.
        title/message get a naive quote-doubling pass (Sprint 25) — the same
        "not real escaping" treatment already applied to
        models/ai_conversation.py's add_message() — needed because Sprint 25's
        AI-narrated insight messages contain ordinary apostrophes constantly
        ("I've", "you're") and were breaking the INSERT outright before this.
        Doubling a quote stops accidental breakage from ordinary text, not a
        deliberately crafted payload that accounts for it — the injection
        stays fully real via dedupe_key and any payload that doesn't rely on
        a lone unescaped apostrophe.
        """
        try:
            title_escaped = title.replace("'", "''")
            message_escaped = message.replace("'", "''")
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT id FROM notifications WHERE user_id = {user_id} AND dedupe_key = '{dedupe_key}'"
            )
            if cursor.fetchone():
                cursor.close()
                return False
            cursor.execute(
                f"INSERT INTO notifications (user_id, type, title, message, dedupe_key) "
                f"VALUES ({user_id}, '{type_}', '{title_escaped}', '{message_escaped}', '{dedupe_key}')"
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_visible_by_user(mysql, user_id, limit=50):
        """
        VULNERABILITY: SQL Injection via user_id/limit
        VULNERABILITY: IDOR — no ownership check, any user_id returns that user's notifications
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM notifications WHERE user_id = {user_id} AND dismissed_at IS NULL "
                f"ORDER BY created_at DESC LIMIT {limit}"
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
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT COUNT(*) FROM notifications WHERE user_id = {user_id} "
                f"AND is_read = FALSE AND dismissed_at IS NULL"
            )
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

    @staticmethod
    def mark_read(mysql, notification_id, is_read=True):
        """VULNERABILITY: IDOR — no ownership check, any notification_id can be marked read/unread"""
        try:
            cursor = mysql.connection.cursor()
            flag = 1 if is_read else 0
            # VULN: SQL Injection
            cursor.execute(f"UPDATE notifications SET is_read = {flag} WHERE id = {notification_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def dismiss(mysql, notification_id):
        """VULNERABILITY: IDOR — no ownership check"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"UPDATE notifications SET dismissed_at = NOW() WHERE id = {notification_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete_all(mysql, user_id):
        """
        Permanently deletes every notification for user_id.
        VULNERABILITY: IDOR — user_id from request, can delete another user's
        notifications entirely (not just dismiss them)
        VULNERABILITY: SQL Injection
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"DELETE FROM notifications WHERE user_id = {user_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def mark_all_read(mysql, user_id):
        """VULNERABILITY: IDOR — user_id from request, can mark another user's notifications read"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"UPDATE notifications SET is_read = TRUE WHERE user_id = {user_id} AND is_read = FALSE")
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
