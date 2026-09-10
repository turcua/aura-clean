"""
Aura Financial Tracker - Vulnerable Version
AI Conversation Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 23: AI Advisor Foundation
"""


class AIConversation:
    def __init__(self, id=None, user_id=None, role=None, content=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.role = role
        self.content = content
        self.created_at = created_at

    @staticmethod
    def add_message(mysql, user_id, role, content):
        """
        VULNERABILITY: SQL Injection — role/content interpolated directly.
        A crafted chat message can break out of the INSERT statement.
        """
        try:
            cursor = mysql.connection.cursor()
            content_escaped = content.replace("'", "''")  # naive, not real escaping
            # VULN: SQL Injection
            cursor.execute(
                f"INSERT INTO ai_conversations (user_id, role, content) "
                f"VALUES ({user_id}, '{role}', '{content_escaped}')"
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_recent(mysql, user_id, limit=20, since=None):
        """
        VULNERABILITY: SQL Injection via user_id/limit/since.
        VULNERABILITY: IDOR — no ownership check, any user_id returns that
        user's conversation history (VULN-075).
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            since_clause = f"AND created_at >= '{since}' " if since else ""
            cursor.execute(
                f"SELECT id, user_id, role, content, created_at FROM ai_conversations "
                f"WHERE user_id = {user_id} {since_clause}ORDER BY created_at DESC, id DESC LIMIT {limit}"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [AIConversation._from_row(r) for r in reversed(rows)]
        except Exception:
            return []

    @staticmethod
    def delete_all(mysql, user_id):
        """
        VULNERABILITY: IDOR — user_id from request, can wipe another user's
        entire conversation history (VULN-075).
        VULNERABILITY: SQL Injection.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"DELETE FROM ai_conversations WHERE user_id = {user_id}")
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete_older_than(mysql, days=90):
        """Scheduler-internal retention cleanup — not called from a route."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE FROM ai_conversations WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
                (int(days),)
            )
            mysql.connection.commit()
            deleted = cursor.rowcount
            cursor.close()
            return deleted
        except Exception:
            mysql.connection.rollback()
            return 0

    @staticmethod
    def _from_row(row):
        return AIConversation(
            id=row[0], user_id=row[1], role=row[2], content=row[3], created_at=row[4],
        )
