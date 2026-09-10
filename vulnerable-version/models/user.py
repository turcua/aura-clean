"""
Aura Financial Tracker - Vulnerable Version
User Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 1: Water Breathing - First Form
"""

from flask import current_app
from flask_mysqldb import MySQL
import hashlib
import pyotp
from datetime import datetime
import random

class User:
    """User model with intentional security vulnerabilities"""

    def __init__(self, user_id=None, username=None, email=None, password=None, totp_enabled=False):
        self.id = user_id
        self.username = username
        self.email = email
        self.password = password  # VULN: Stores plaintext password
        self.created_at = None
        self.last_login = None
        self.is_active = True
        self.totp_enabled = totp_enabled
    
    @staticmethod
    def hash_password(password):
        """
        VULNERABILITY: Uses weak MD5 hashing (easily crackable)
        """
        return hashlib.md5(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, stored_password):
        """
        VULNERABILITY: Compares plaintext passwords directly
        """
        # Sometimes uses MD5, sometimes plaintext (inconsistent security)
        if len(stored_password) == 32:  # MD5 hash length
            return User.hash_password(password) == stored_password
        else:
            return password == stored_password  # VULN: Plaintext comparison
    
    @staticmethod
    def validate_password_strength(password):
        """
        VULNERABILITY: No real password validation
        """
        # Always returns True - accepts any password
        return True, ""
    
    @staticmethod
    def create_user(mysql, username, email, password):
        """
        VULNERABILITY: SQL Injection through string concatenation
        VULNERABILITY: Stores passwords in plaintext
        VULNERABILITY: No input validation
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection - using string concatenation instead of parameterized queries
            query = f'INSERT INTO users (username, email, password, is_active) VALUES ("{username}", "{email}", "{password}", TRUE)'
            
            cursor.execute(query)
            mysql.connection.commit()
            user_id = cursor.lastrowid
            cursor.close()
            
            return True, "User created successfully", user_id
            
        except Exception as e:
            # VULN: Detailed error message leaks database information
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def authenticate(mysql, username, password):
        """
        VULNERABILITY: SQL Injection in authentication
        VULNERABILITY: No rate limiting (brute force attacks)
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection vulnerability through string concatenation
            query = f"SELECT id, username, email, password, totp_enabled FROM users WHERE username = '{username}' AND password = '{password}'"

            cursor.execute(query)
            user_data = cursor.fetchone()

            if not user_data:
                cursor.close()
                return False, "Invalid username or password", None

            user_id, db_username, db_email, db_password, totp_enabled = user_data

            # VULN: Plaintext password comparison
            if password == db_password or User.hash_password(password) == db_password:
                # Update last login
                update_query = f"UPDATE users SET last_login = '{datetime.now()}' WHERE id = {user_id}"
                cursor.execute(update_query)
                mysql.connection.commit()
                cursor.close()

                # Create user object
                user = User(user_id, db_username, db_email, db_password, totp_enabled=bool(totp_enabled))
                return True, "Login successful", user
            else:
                cursor.close()
                return False, "Invalid username or password", None
                
        except Exception as e:
            # VULN: Detailed error messages
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def create_session(mysql, user_id, ip_address, user_agent):
        """
        VULNERABILITY: Predictable session tokens
        VULNERABILITY: No expiration
        """
        try:
            # VULN: Predictable session token (just user_id + random number)
            session_token = f"session_{user_id}_{random.randint(1000, 9999)}"
            
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection in session creation
            query = f"INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, is_valid) VALUES ({user_id}, '{session_token}', '{ip_address}', '{user_agent}', TRUE)"
            
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            
            return True, session_token
            
        except Exception as e:
            return False, None
    
    @staticmethod
    def validate_session(mysql, session_token):
        """
        VULNERABILITY: No session expiration check
        VULNERABILITY: SQL Injection in validation
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection vulnerability
            query = f"SELECT user_id FROM user_sessions WHERE session_token = '{session_token}' AND is_valid = TRUE"
            
            cursor.execute(query)
            session_data = cursor.fetchone()
            cursor.close()
            
            if not session_data:
                return False, None
            
            user_id = session_data[0]
            return True, user_id
            
        except Exception:
            return False, None
    
    @staticmethod
    def invalidate_session(mysql, session_token):
        """
        VULNERABILITY: SQL Injection in logout
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection
            query = f"UPDATE user_sessions SET is_valid = FALSE WHERE session_token = '{session_token}'"
            
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_user_by_id(mysql, user_id):
        """
        VULNERABILITY: SQL Injection
        """
        try:
            cursor = mysql.connection.cursor()
            
            # VULN: SQL Injection
            query = f"SELECT id, username, email, password, totp_enabled FROM users WHERE id = {user_id} AND is_active = TRUE"

            cursor.execute(query)
            user_data = cursor.fetchone()
            cursor.close()

            if user_data:
                return User(user_data[0], user_data[1], user_data[2], user_data[3], totp_enabled=bool(user_data[4]))
            return None

        except Exception:
            return None

    @staticmethod
    def generate_reset_token(mysql, email):
        """
        Sprint 52 (ENH-03).
        VULNERABILITY: weak/predictable reset token — same style as
        create_session()'s predictable session_{user_id}_{random 4-digit}
        token above, not a cryptographically random value. A 4-digit
        space is trivially brute-forceable once the user_id is known (and
        user_id is itself guessable/enumerable elsewhere in this app).
        VULNERABILITY: SQL Injection via string concatenation.
        VULNERABILITY: returns whether the email was actually found — the
        caller (routes/auth.py) exposes this directly in its response,
        letting an attacker enumerate registered emails one probe at a time.
        Returns (found, token) — token is None if found is False.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT id FROM users WHERE email = '{email}' AND is_active = TRUE"
            cursor.execute(query)
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False, None

            user_id = row[0]
            # VULN: predictable token, matching create_session()'s style
            token = f"reset_{user_id}_{random.randint(1000, 9999)}"
            # VULN: expires is stored but never actually checked in
            # verify_reset_token() below — the column exists, the
            # enforcement doesn't.
            expires = datetime.now()
            query = f"UPDATE users SET reset_token = '{token}', reset_token_expires = '{expires}' WHERE id = {user_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, token
        except Exception:
            return False, None

    @staticmethod
    def verify_reset_token(mysql, token):
        """
        VULNERABILITY: SQL Injection. VULNERABILITY: no expiry check at
        all — reset_token_expires is stored but never read here, so a
        token remains valid forever once issued.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT id FROM users WHERE reset_token = '{token}' AND is_active = TRUE"
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    def reset_password(mysql, token, new_password):
        """
        VULNERABILITY: SQL Injection, plaintext password storage (matching
        create_user()'s existing style), no real password validation
        (matching validate_password_strength()'s existing always-True).

        Bug fixed 2026-08-13 (found via real testing): this originally
        MD5-hashed new_password before storing it, matching hash_password()'s
        style — but authenticate()'s own query filters directly on
        `password = '{password}'` in SQL, comparing the stored value to the
        submitted plaintext. Since create_user() stores plaintext (not a
        hash), that filter only ever matches when the stored value is also
        plaintext — a hashed value stored here meant the login query itself
        never found the row at all, locking the user out of their own
        just-reset password. Storing plaintext directly instead, consistent
        with how every other password in this table is actually stored and
        actually checked.
        """
        user_id = User.verify_reset_token(mysql, token)
        if not user_id:
            return False, "This reset link is invalid or has expired"

        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection. VULNERABILITY: plaintext password storage.
            query = (
                f"UPDATE users SET password = '{new_password}', reset_token = NULL, "
                f"reset_token_expires = NULL WHERE id = {user_id}"
            )
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True, "Password has been reset successfully"
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def setup_totp(mysql, user_id):
        """Sprint 52 (ENH-04). VULNERABILITY: SQL Injection."""
        try:
            secret = pyotp.random_base32()
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"UPDATE users SET totp_secret = '{secret}' WHERE id = {user_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return secret
        except Exception:
            return None

    @staticmethod
    def confirm_totp_setup(mysql, user_id, code):
        """VULNERABILITY: SQL Injection."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT totp_secret FROM users WHERE id = {user_id}"
            cursor.execute(query)
            row = cursor.fetchone()
            if not row or not row[0]:
                cursor.close()
                return False

            if not pyotp.TOTP(row[0]).verify(code):
                cursor.close()
                return False

            query = f"UPDATE users SET totp_enabled = TRUE WHERE id = {user_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            return False

    @staticmethod
    def verify_totp_code(mysql, user_id, code):
        """
        VULNERABILITY: SQL Injection.
        VULNERABILITY (the real point of ENH-04's weakness): the actual
        brute-force protection gap isn't in this method — it's that
        routes/auth.py's verify_2fa() never rate-limits calls into it, so a
        6-digit code (1 in 1,000,000) becomes practically guessable given
        enough unthrottled attempts, matching this app's MAX_LOGIN_ATTEMPTS
        = 999999 theme for password login.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT totp_secret FROM users WHERE id = {user_id} AND totp_enabled = TRUE"
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            if not row or not row[0]:
                return False
            return pyotp.TOTP(row[0]).verify(code)
        except Exception:
            return False

    @staticmethod
    def disable_totp(mysql, user_id):
        """VULNERABILITY: SQL Injection."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"UPDATE users SET totp_secret = NULL, totp_enabled = FALSE WHERE id = {user_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            return False

    @staticmethod
    def get_stat_card_order(mysql, user_id):
        """
        Sprint 53 (UI-02, VULN-086).
        VULNERABILITY: SQL Injection via string concatenation.
        VULNERABILITY: IDOR — no check that user_id is the caller's own;
        ownership enforcement (or lack of it) lives entirely in the route.
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"SELECT stat_card_order FROM users WHERE id = {user_id}"
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    def set_stat_card_order(mysql, user_id, order_str):
        """VULNERABILITY: SQL Injection. VULNERABILITY: IDOR — any user_id
        the caller supplies gets written, no ownership check."""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            query = f"UPDATE users SET stat_card_order = '{order_str}' WHERE id = {user_id}"
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            return False

    @staticmethod
    def get_all_ids(mysql):
        """Sprint 25: scheduler-internal — every active user's id."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM users WHERE is_active = TRUE")
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows]
        except Exception:
            return []
