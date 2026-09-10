"""
Aura Financial Tracker - Secure Version
User Model
Sprint 1: Water Breathing - First Form
"""

from flask import current_app
from flask_mysqldb import MySQL
import bcrypt
import pyotp
from datetime import datetime, timedelta
import secrets

class User:
    """User model with secure password handling"""

    def __init__(self, user_id=None, username=None, email=None, password_hash=None, is_admin=False, totp_enabled=False):
        self.id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = None
        self.last_login = None
        self.is_active = True
        self.failed_login_attempts = 0
        self.is_admin = is_admin
        self.totp_enabled = totp_enabled
    
    @staticmethod
    def hash_password(password):
        """
        Hash a password using bcrypt (secure)
        Returns: hashed password as string
        """
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds for good security
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        """
        Verify a password against its hash
        Returns: True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password meets security requirements
        Returns: (is_valid, error_message)
        """
        config = current_app.config
        
        if len(password) < config['MIN_PASSWORD_LENGTH']:
            return False, f"Password must be at least {config['MIN_PASSWORD_LENGTH']} characters long"
        
        if config['REQUIRE_UPPERCASE'] and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if config['REQUIRE_LOWERCASE'] and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if config['REQUIRE_DIGITS'] and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        if config['REQUIRE_SPECIAL_CHARS'] and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            return False, "Password must contain at least one special character"
        
        return True, ""
    
    @staticmethod
    def create_user(mysql, username, email, password):
        """
        Create a new user with secure password storage
        Returns: (success, message, user_id)
        """
        # Validate password strength
        is_valid, error_msg = User.validate_password_strength(password)
        if not is_valid:
            return False, error_msg, None
        
        # Hash the password
        password_hash = User.hash_password(password)
        
        try:
            cursor = mysql.connection.cursor()
            
            # Check if username or email already exists
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            existing_user = cursor.fetchone()
            
            if existing_user:
                cursor.close()
                return False, "Username or email already exists", None
            
            # Insert new user (using parameterized query - SQL injection protection)
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, is_active, failed_login_attempts)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, email, password_hash, True, 0)
            )
            
            mysql.connection.commit()
            user_id = cursor.lastrowid
            cursor.close()
            
            return True, "User created successfully", user_id
            
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def authenticate(mysql, username, password):
        """
        Authenticate a user with rate limiting.
        Returns: (success, message, user_object)

        Sprint 15 fix: lockout now expires after Config.LOGIN_TIMEOUT_MINUTES —
        previously failed_login_attempts >= MAX_LOGIN_ATTEMPTS locked the account
        permanently (LOGIN_TIMEOUT_MINUTES was defined in config.py but never
        actually read anywhere), directing the user to "contact support" with no
        support channel to contact. locked_until now records when the lockout
        was applied plus the timeout; once that passes, the next login attempt
        auto-resets failed_login_attempts and proceeds normally.
        """
        try:
            cursor = mysql.connection.cursor()

            # Fetch user by username (parameterized query)
            cursor.execute(
                "SELECT id, username, email, password_hash, failed_login_attempts, locked_until, is_admin, totp_enabled "
                "FROM users WHERE username = %s AND is_active = TRUE",
                (username,)
            )
            user_data = cursor.fetchone()

            if not user_data:
                cursor.close()
                return False, "Invalid username or password", None

            user_id, db_username, db_email, password_hash, failed_attempts, locked_until, is_admin, totp_enabled = user_data

            # Check if account is still within its lockout window
            if locked_until is not None:
                if datetime.now() < locked_until:
                    remaining = int((locked_until - datetime.now()).total_seconds() // 60) + 1
                    cursor.close()
                    return False, f"Account locked due to multiple failed login attempts. Try again in {remaining} minute(s).", None
                # Lockout window has passed — auto-unlock before proceeding
                cursor.execute(
                    "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = %s",
                    (user_id,)
                )
                mysql.connection.commit()
                failed_attempts = 0

            # Verify password
            if User.verify_password(password, password_hash):
                # Successful login - reset failed attempts and update last login
                cursor.execute(
                    "UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login = %s WHERE id = %s",
                    (datetime.now(), user_id)
                )
                mysql.connection.commit()
                cursor.close()

                # Create user object
                user = User(user_id, db_username, db_email, password_hash, is_admin=bool(is_admin), totp_enabled=bool(totp_enabled))
                return True, "Login successful", user
            else:
                # Failed login - increment failed attempts; lock if threshold reached
                max_attempts = current_app.config['MAX_LOGIN_ATTEMPTS']
                timeout_minutes = current_app.config['LOGIN_TIMEOUT_MINUTES']
                new_failed_attempts = failed_attempts + 1

                if new_failed_attempts >= max_attempts:
                    lock_until = datetime.now() + timedelta(minutes=timeout_minutes)
                    cursor.execute(
                        "UPDATE users SET failed_login_attempts = %s, locked_until = %s WHERE id = %s",
                        (new_failed_attempts, lock_until, user_id)
                    )
                    mysql.connection.commit()
                    cursor.close()
                    return False, f"Account locked due to multiple failed login attempts. Try again in {timeout_minutes} minute(s).", None

                cursor.execute(
                    "UPDATE users SET failed_login_attempts = %s WHERE id = %s",
                    (new_failed_attempts, user_id)
                )
                mysql.connection.commit()
                cursor.close()

                return False, "Invalid username or password", None

        except Exception as e:
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def create_session(mysql, user_id, ip_address, user_agent):
        """
        Create a secure session for the user
        Returns: (success, session_token)

        Security audit fix: expired sessions were previously only ever
        invalidated lazily, on the next validate_session() call against that
        exact token — a token nobody ever presents again (e.g. an abandoned
        browser tab) stayed in the table forever. This deletes this user's
        own already-expired rows on every new login, bounding growth without
        needing a separate cleanup job. Scoped to user_id, so it can never
        touch another user's sessions.
        """
        try:
            # Generate cryptographically secure session token
            session_token = secrets.token_urlsafe(32)

            # Calculate expiration time
            expires_at = datetime.now() + current_app.config['PERMANENT_SESSION_LIFETIME']

            cursor = mysql.connection.cursor()
            cursor.execute(
                "DELETE FROM user_sessions WHERE user_id = %s AND expires_at < %s",
                (user_id, datetime.now())
            )
            cursor.execute(
                """
                INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at, is_valid)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, session_token, ip_address, user_agent, expires_at, True)
            )
            mysql.connection.commit()
            cursor.close()

            return True, session_token

        except Exception as e:
            mysql.connection.rollback()
            return False, None
    
    @staticmethod
    def validate_session(mysql, session_token):
        """
        Validate a session token
        Returns: (is_valid, user_id)
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                """
                SELECT user_id, expires_at FROM user_sessions 
                WHERE session_token = %s AND is_valid = TRUE
                """,
                (session_token,)
            )
            session_data = cursor.fetchone()
            cursor.close()
            
            if not session_data:
                return False, None
            
            user_id, expires_at = session_data
            
            # Check if session has expired
            if datetime.now() > expires_at:
                # Invalidate expired session
                User.invalidate_session(mysql, session_token)
                return False, None
            
            return True, user_id
            
        except Exception:
            return False, None
    
    @staticmethod
    def invalidate_session(mysql, session_token):
        """
        Invalidate a session (logout)
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE user_sessions SET is_valid = FALSE WHERE session_token = %s",
                (session_token,)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_user_by_id(mysql, user_id):
        """
        Get user by ID
        Returns: User object or None
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, username, email, password_hash, is_admin, totp_enabled FROM users WHERE id = %s AND is_active = TRUE",
                (user_id,)
            )
            user_data = cursor.fetchone()
            cursor.close()

            if user_data:
                return User(
                    user_data[0], user_data[1], user_data[2], user_data[3],
                    is_admin=bool(user_data[4]), totp_enabled=bool(user_data[5]),
                )
            return None

        except Exception:
            return None

    @staticmethod
    def generate_reset_token(mysql, email):
        """
        Sprint 52 (ENH-03). Cryptographically random, single-use, time-limited
        (PASSWORD_RESET_TOKEN_EXPIRY_MINUTES). Returns the token if a matching
        active user exists, or None if not — the caller (routes/auth.py) must
        send the same generic response either way, so this method's return
        value is never itself exposed to the client; only whether to attempt
        sending an email.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND is_active = TRUE",
                (email,)
            )
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return None

            token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(minutes=current_app.config['PASSWORD_RESET_TOKEN_EXPIRY_MINUTES'])
            cursor.execute(
                "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s",
                (token, expires, row[0])
            )
            mysql.connection.commit()
            cursor.close()
            return token
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def verify_reset_token(mysql, token):
        """Returns the user_id for a valid, unexpired token, or None."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, reset_token_expires FROM users "
                "WHERE reset_token = %s AND is_active = TRUE",
                (token,)
            )
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return None
            user_id, expires = row
            if expires is None or datetime.now() > expires:
                return None
            return user_id
        except Exception:
            return None

    @staticmethod
    def reset_password(mysql, token, new_password):
        """
        Validates the token again (defense in depth, not just trusting a
        prior verify_reset_token() call), sets the new password, and clears
        the token so it can't be reused. Returns (success, message).
        """
        user_id = User.verify_reset_token(mysql, token)
        if not user_id:
            return False, "This reset link is invalid or has expired"

        is_valid, error_msg = User.validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg

        try:
            password_hash = User.hash_password(new_password)
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL "
                "WHERE id = %s",
                (password_hash, user_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True, "Password has been reset successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not reset password"

    @staticmethod
    def setup_totp(mysql, user_id):
        """
        Sprint 52 (ENH-04). Generates a new secret and stores it, but leaves
        totp_enabled untouched — a secret alone doesn't gate login, only
        confirm_totp_setup() below flipping totp_enabled to TRUE does. This
        means starting setup twice in a row is safe (the second call just
        overwrites the first's not-yet-confirmed secret) and an abandoned
        setup never silently enables 2FA. Returns the secret (base32,
        needed by the caller to render the QR code).
        """
        try:
            secret = pyotp.random_base32()
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET totp_secret = %s WHERE id = %s",
                (secret, user_id)
            )
            mysql.connection.commit()
            cursor.close()
            return secret
        except Exception:
            mysql.connection.rollback()
            return None

    @staticmethod
    def confirm_totp_setup(mysql, user_id, code):
        """Verifies the submitted code against the pending secret and, if
        correct, flips totp_enabled to TRUE. Returns bool."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT totp_secret FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if not row or not row[0]:
                cursor.close()
                return False

            if not pyotp.TOTP(row[0]).verify(code):
                cursor.close()
                return False

            cursor.execute("UPDATE users SET totp_enabled = TRUE WHERE id = %s", (user_id,))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def verify_totp_code(mysql, user_id, code):
        """Verifies a code against an already-enabled 2FA secret — used at
        login time and before disabling. Returns bool; False if 2FA isn't
        actually enabled for this user, so this can't be used to "verify" a
        code for an account that never turned 2FA on."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT totp_secret FROM users WHERE id = %s AND totp_enabled = TRUE",
                (user_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            if not row or not row[0]:
                return False
            return pyotp.TOTP(row[0]).verify(code)
        except Exception:
            return False

    @staticmethod
    def disable_totp(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET totp_secret = NULL, totp_enabled = FALSE WHERE id = %s",
                (user_id,)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_stat_card_order(mysql, user_id):
        """Sprint 53 (UI-02). Returns the saved comma-separated key list
        (e.g. "income,expenses,balance,budget"), or None if never set."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT stat_card_order FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Exception:
            return None

    @staticmethod
    def set_stat_card_order(mysql, user_id, order_str):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET stat_card_order = %s WHERE id = %s",
                (order_str, user_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_all_users(mysql):
        """
        Sprint 34, widened Sprint 57 (ENH-02): for the admin panel — every
        user's id/username/email/created_at/is_admin/is_active/
        locked_until/failed_login_attempts/last_login. Never selects
        password_hash: unlike vulnerable's /admin (VULN-002), this panel
        has no reason to display credentials at all, hashed or not, and
        shouldn't just because vulnerable's does.

        Widened to include inactive (locked-out/deactivated) users too —
        the old `WHERE is_active = TRUE` filter meant an admin could never
        actually see, let alone reactivate, an account they'd locked or
        that had locked itself out via failed logins. The extra columns
        are what make the new lock-status/failed-attempts/last-login
        columns on the admin page possible at all; they already existed on
        the table, just were never selected here.
        """
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, username, email, created_at, is_admin, is_active, "
                "locked_until, failed_login_attempts, last_login FROM users "
                "ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def set_admin_status(mysql, user_id, is_admin):
        """Sprint 57 (ENH-02): admin-panel promote/demote. `is_admin` is
        re-read from the DB fresh on every login (routes/auth.py), so this
        takes effect the next time the affected user logs in — an already
        logged-in session keeps whatever admin status it had at login time
        until it re-authenticates, same as every other session['is_admin']
        read in this codebase."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE users SET is_admin = %s WHERE id = %s", (bool(is_admin), user_id))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def set_active_status(mysql, user_id, is_active):
        """Sprint 57 (ENH-02): admin-panel lock/unlock. Deactivating also
        clears any stale lockout counters so a re-activated account isn't
        immediately re-locked by leftover failed_login_attempts/
        locked_until state from before. Login itself already filters on
        is_active = TRUE (User.login), so deactivating here takes effect
        immediately, not just on next login — the account simply can't
        authenticate at all while inactive."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET is_active = %s, failed_login_attempts = 0, locked_until = NULL WHERE id = %s",
                (bool(is_active), user_id)
            )
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def delete_user(mysql, user_id):
        """Sprint 57 (ENH-02): admin-panel hard delete. Every FK referencing
        users(id) in this schema is ON DELETE CASCADE (transactions,
        accounts, loans, budgets, goals, etc. — see database/init-secure-*.sql),
        so this genuinely removes the user and everything they own, not a
        soft-delete. Irreversible; the route calling this is responsible
        for requiring real confirmation before it's ever reached."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def invalidate_all_sessions(mysql, user_id):
        """Sprint 57 (ENH-02): admin-panel force-expire. Reuses the
        existing user_sessions table (already backing
        validate_session()/invalidate_session() for normal logout) rather
        than adding new session-tracking machinery — just widens the
        invalidation from "one token" to "every session this user has,"
        so all of their devices/tabs are forced to re-authenticate on
        their next request."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE user_sessions SET is_valid = FALSE WHERE user_id = %s", (user_id,))
            mysql.connection.commit()
            cursor.close()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_all_ids(mysql):
        """Sprint 25: scheduler-internal — every active user's id, for jobs
        that need to iterate all users (e.g. the AI-insight job)."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM users WHERE is_active = TRUE")
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows]
        except Exception:
            return []
