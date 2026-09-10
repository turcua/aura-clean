"""
Aura Financial Tracker - Secure Version
AI Conversation Model
Sprint 23: AI Advisor Foundation

Security properties (contrast with vulnerable-version/models/ai_conversation.py):
- All queries parameterized — no f-string SQL anywhere
- Ownership enforced in the SQL WHERE clause (user_id = %s) on every read —
  vulnerable-version's get_recent() takes user_id as a plain, unvalidated
  argument sourced from client input at the route layer (IDOR)
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
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO ai_conversations (user_id, role, content) VALUES (%s, %s, %s)",
                (user_id, role, content)
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
        Most recent `limit` messages for user_id, returned oldest-first (the
        order a chat completions API expects for replaying conversation
        history) — the query itself orders DESC to get the most recent rows,
        then the result is reversed in Python.

        `since` (ISO timestamp string, optional): only messages from this
        point forward — used to scope both the displayed panel history and
        the AI's replayed context to "this login", per session['ai_chat_since'].
        """
        try:
            cursor = mysql.connection.cursor()
            if since:
                cursor.execute(
                    "SELECT id, user_id, role, content, created_at FROM ai_conversations "
                    "WHERE user_id = %s AND created_at >= %s ORDER BY created_at DESC, id DESC LIMIT %s",
                    (user_id, since, int(limit))
                )
            else:
                cursor.execute(
                    "SELECT id, user_id, role, content, created_at FROM ai_conversations "
                    "WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT %s",
                    (user_id, int(limit))
                )
            rows = cursor.fetchall()
            cursor.close()
            return [AIConversation._from_row(r) for r in reversed(rows)]
        except Exception:
            return []

    @staticmethod
    def delete_all(mysql, user_id):
        """User-triggered 'Clear conversation' — permanently deletes every
        stored message for user_id, not just the current login's window."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM ai_conversations WHERE user_id = %s", (user_id,))
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
    def get_usage_stats(mysql):
        """
        Sprint 57 (ENH-02, group 4): per-user message counts for the admin
        panel's AI usage visibility — deliberately message counts, not
        token counts. Real token usage was never captured anywhere in this
        app (Groq's response.usage is discarded in utils/groq_client.py),
        so there's no historical token data to report; explicit user
        decision (2026-09-02) to ship message-count visibility now rather
        than add token tracking, which would need a migration and could
        only cover messages going forward, never the past. LEFT JOIN so
        users with zero AI usage still show up (as 0), not just active ones.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT u.id, u.username, "
                "COUNT(CASE WHEN ac.role = 'user' THEN 1 END) AS prompts_sent, "
                "COUNT(ac.id) AS total_messages, "
                "MAX(ac.created_at) AS last_activity "
                "FROM users u LEFT JOIN ai_conversations ac ON ac.user_id = u.id "
                "GROUP BY u.id, u.username "
                "ORDER BY total_messages DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def _from_row(row):
        return AIConversation(
            id=row[0], user_id=row[1], role=row[2], content=row[3], created_at=row[4],
        )
