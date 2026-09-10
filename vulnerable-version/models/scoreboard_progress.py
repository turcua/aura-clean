"""
Aura Financial Tracker - Vulnerable Version
Scoreboard Progress Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 42: Sound Breathing - Constant Resounding Slashes
"""


class ScoreboardProgress:
    @staticmethod
    def mark(mysql, user_id, vuln_id, source='self_report'):
        """VULNERABILITY: SQL Injection, IDOR/mass assignment — user_id is
        whatever the caller passed in, never checked against the session
        (see routes/api/scoreboard.py — VULN-082)."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"INSERT INTO scoreboard_progress (user_id, vuln_id, source) "
                f"VALUES ({user_id}, '{vuln_id}', '{source}') "
                f"ON DUPLICATE KEY UPDATE found_at = found_at"
            )
            mysql.connection.commit()
            cursor.close()
            return True, "Marked as found"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def unmark(mysql, user_id, vuln_id):
        """VULNERABILITY: SQL Injection, IDOR — no ownership check on user_id."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"DELETE FROM scoreboard_progress WHERE user_id = {user_id} AND vuln_id = '{vuln_id}'"
            )
            mysql.connection.commit()
            cursor.close()
            return True, "Unmarked"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def get_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection, IDOR — any user_id returns that user's progress."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT vuln_id, found_at, source FROM scoreboard_progress WHERE user_id = {user_id}"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'vuln_id': r[0], 'found_at': r[1], 'source': r[2]} for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_my_flags(mysql, user_id):
        """Safe, parameterized — deliberately NOT the same code path as
        get_by_user() above. That one is VULN-082 (IDOR+SQLi, publicly
        reachable with any user_id); if flag_value were added to its
        SELECT, anyone could read anyone's real flag secrets through the
        existing vulnerability without solving anything themselves,
        trivializing the whole CTF. This method is only ever called with
        session['user_id'] from a login-required route."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT vuln_id, found_at, source, flag_value FROM scoreboard_progress WHERE user_id = %s",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'vuln_id': r[0], 'found_at': r[1], 'source': r[2], 'flag_value': r[3]} for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_unnotified(mysql, user_id):
        """Safe, parameterized — solved findings the popup hasn't announced
        yet, per the account (server-side truth, not a browser's
        localStorage — see notified_at's own migration comment for why
        that mattered)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT vuln_id, source, flag_value FROM scoreboard_progress "
                "WHERE user_id = %s AND notified_at IS NULL",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'vuln_id': r[0], 'source': r[1], 'flag_value': r[2]} for r in rows]
        except Exception:
            return []

    @staticmethod
    def mark_notified(mysql, user_id, vuln_id):
        """Safe, parameterized — called once the popup has actually shown
        this finding to the account it belongs to."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE scoreboard_progress SET notified_at = NOW() "
                "WHERE user_id = %s AND vuln_id = %s",
                (user_id, vuln_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def find_by_flag_value(mysql, flag_value):
        """Safe, parameterized — used to validate a manually-submitted flag."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT vuln_id FROM scoreboard_progress WHERE flag_value = %s LIMIT 1",
                (flag_value,)
            )
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    def credit_flag(mysql, user_id, vuln_id, flag_value):
        """Safe, parameterized — credits `user_id` (always session['user_id']
        of the submitter, never request-controlled) with a flag already
        known to be valid (see find_by_flag_value)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO scoreboard_progress (user_id, vuln_id, source, flag_value) "
                "VALUES (%s, %s, 'flag', %s) "
                "ON DUPLICATE KEY UPDATE flag_value = VALUES(flag_value), source = 'flag'",
                (user_id, vuln_id, flag_value)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_leaderboard(mysql, limit=20):
        """Public by design (Sprint 42 scope decision 4) — no auth required to read this."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT u.username, COUNT(*) AS found_count "
                "FROM scoreboard_progress sp "
                "JOIN users u ON u.id = sp.user_id "
                "GROUP BY sp.user_id, u.username "
                "ORDER BY found_count DESC "
                f"LIMIT {int(limit)}"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{'username': r[0], 'found_count': r[1]} for r in rows]
        except Exception:
            return []
