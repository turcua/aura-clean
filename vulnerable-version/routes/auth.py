"""
Aura Financial Tracker - Vulnerable Version
Authentication Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 1: Water Breathing - First Form
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_mysqldb import MySQL
from models.user import User
from routes.main import login_required
from datetime import datetime
from utils import flag_engine
from utils.mailer import send_email
import pyotp
import qrcode
import io
import base64

auth_bp = Blueprint('auth', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    return current_app.extensions['mysql']

# VULNERABILITY: No input validation functions
# VULNERABILITY: No CSRF protection

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    VULNERABILITY: No input validation
    VULNERABILITY: No CSRF protection
    VULNERABILITY: SQL Injection possible
    """
    
    if request.method == 'POST':
        # VULN: Direct access to form data without validation
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        
        # VULN: No validation, no sanitization
        # VULN: No password confirmation check
        
        # Create user (vulnerable to SQL injection)
        mysql = get_mysql()
        success, message, user_id = User.create_user(mysql, username, email, password)

        if success:
            # Sprint 44 (VULN-003 flag): registering with a genuinely weak
            # password succeeding is the proof — credited to the new
            # account itself (no session exists yet at registration time;
            # they'll see it once they log in).
            if password and len(password) < 6:
                flag_engine.mark_solved_with_flag(mysql, user_id, 'VULN-003')

            # Sprint 44 (VULN-007 flag): a literal quote in username/email
            # that the insert still accepted is real injected SQL syntax —
            # legitimate values essentially never contain one.
            if ("'" in str(username)) or ("'" in str(email)):
                flag_engine.mark_solved_with_flag(mysql, user_id, 'VULN-007')

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # VULN: Detailed error messages leak information
            flash(message, 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Sprint 52 (ENH-03).
    VULNERABILITY: no rate limiting — this endpoint can be hammered to
    enumerate/spam without any throttling, matching this app's existing
    no-rate-limiting theme.
    VULNERABILITY: user enumeration — the response message directly
    reveals whether the submitted email is a registered account, unlike
    secure-version's identical generic response either way.
    """
    if request.method == 'POST':
        email = request.form.get('email', '')
        mysql = get_mysql()
        found, token = User.generate_reset_token(mysql, email)

        if found:
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            send_email(
                email,
                'Aura — Password Reset Request',
                f'Someone requested a password reset for this account.\n\n'
                f'Reset your password: {reset_link}\n\n'
                f'This link does not expire.'
            )
            # VULN: confirms the email exists
            flash('A password reset link has been sent to that email.', 'info')
        else:
            # VULN: confirms the email does NOT exist — the asymmetry
            # between this branch and the one above is the enumeration bug.
            flash('No account found with that email.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Sprint 52 (ENH-03). VULNERABILITY: no rate limiting on submission attempts."""
    mysql = get_mysql()

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', token=token)

        success, message = User.reset_password(mysql, token, password)
        if success:
            flash('Your password has been reset. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        flash(message, 'danger')
        return render_template('reset_password.html', token=token)

    if not User.verify_reset_token(mysql, token):
        flash('This reset link is invalid', 'danger')
        return redirect(url_for('auth.forgot_password'))

    return render_template('reset_password.html', token=token)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    VULNERABILITY: SQL Injection in authentication
    VULNERABILITY: No rate limiting (brute force)
    VULNERABILITY: No CSRF protection
    """
    
    if request.method == 'POST':
        # VULN: No input validation
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # VULN: No sanitization
        
        # Authenticate user (vulnerable to SQL injection)
        mysql = get_mysql()
        success, message, user = User.authenticate(mysql, username, password)

        if success:
            # Sprint 52 (ENH-04): same pending-2FA gate as secure-version.
            if user.totp_enabled:
                session['pending_2fa_user_id'] = user.id
                session['pending_2fa_username'] = user.username
                return redirect(url_for('auth.verify_2fa'))

            # Sprint 43 (VULN-006 flag): a real password essentially
            # never contains a literal quote used as SQL syntax —
            # credentials that do, combined with a successful login,
            # are the signature of a boolean-bypass injection rather
            # than a normal correct-password login.
            if "'" in username or "'" in password:
                flag_engine.mark_solved_with_flag(mysql, user.id, 'VULN-006')

            return _complete_login(mysql, user)
        else:
            # VULN: Error messages may leak information
            flash(message, 'danger')
            return render_template('login.html')

    return render_template('login.html')


def _complete_login(mysql, user):
    """Sprint 52 — factored out of login() so both the no-2FA path and the
    post-verify_2fa() path share the same session-creation logic."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')

    session_created, session_token = User.create_session(mysql, user.id, ip_address, user_agent)

    if session_created:
        # VULN: Insecure session configuration
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['session_token'] = session_token
        # VULN: Storing password in session
        session['password'] = user.password
        session['ai_chat_since'] = datetime.utcnow().isoformat()
        session.pop('pending_2fa_user_id', None)
        session.pop('pending_2fa_username', None)

        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        flash('Failed to create session. Please try again.', 'danger')
        return render_template('login.html')


@auth_bp.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    """
    Sprint 52 (ENH-04).
    VULNERABILITY: no rate limiting on submission attempts — a 6-digit TOTP
    code is brute-forceable given enough unthrottled tries, matching this
    app's existing MAX_LOGIN_ATTEMPTS = 999999 theme for password login.
    """
    user_id = session.get('pending_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        mysql = get_mysql()
        if User.verify_totp_code(mysql, user_id, code):
            user = User.get_user_by_id(mysql, user_id)
            return _complete_login(mysql, user)
        flash('Invalid authentication code', 'danger')
        return render_template('verify_2fa.html')

    return render_template('verify_2fa.html')


@auth_bp.route('/logout')
def logout():
    """
    VULNERABILITY: No session validation before logout
    """
    
    session_token = session.get('session_token')
    
    if session_token:
        mysql = get_mysql()
        User.invalidate_session(mysql, session_token)
    
    # Clear session
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.index'))


def _qr_data_uri(secret, username):
    """Sprint 52 (ENH-04) — same approach as secure-version."""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=current_app.config['TOTP_ISSUER_NAME'])
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


@auth_bp.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Sprint 52 (ENH-04). VULNERABILITY: login_required here only checks
    session existence, not token validity — same weak gate as every other
    "logged in" page in this version (see routes/main.py's login_required)."""
    mysql = get_mysql()
    user_id = session['user_id']

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if User.confirm_totp_setup(mysql, user_id, code):
            flash('Two-factor authentication is now enabled.', 'success')
            return redirect(url_for('main.profile'))
        flash('Invalid code — please try again.', 'danger')

    secret = User.setup_totp(mysql, user_id)
    qr_data_uri = _qr_data_uri(secret, session['username'])
    return render_template('setup_2fa.html', secret=secret, qr_data_uri=qr_data_uri)


@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Sprint 52 (ENH-04)."""
    mysql = get_mysql()
    user_id = session['user_id']
    code = request.form.get('code', '').strip()

    if User.verify_totp_code(mysql, user_id, code):
        User.disable_totp(mysql, user_id)
        flash('Two-factor authentication has been disabled.', 'success')
    else:
        flash('Invalid authentication code — 2FA was not disabled.', 'danger')
    return redirect(url_for('main.profile'))

# VULNERABILITY: Debug endpoint that leaks session information
@auth_bp.route('/debug/session')
def debug_session():
    """
    VULNERABILITY: Information disclosure - exposes session data
    Sprint 23 (VULN-076): also dumps app.config — a realistic "the debug
    endpoint accumulates more exposed fields over time" mistake. This is
    what makes GROQ_API_KEY (and SECRET_KEY, DATABASE_PASSWORD, etc.)
    reachable despite config.py itself never logging or returning it.
    """
    from flask import current_app
    config_dump = {k: v for k, v in current_app.config.items()}

    # Sprint 43 (VULN-004 flag): planted directly in the dumped config,
    # alongside SECRET_KEY/GROQ_API_KEY/etc — the whole point of this
    # endpoint's vulnerability is realistic accumulation of exposed fields.
    mysql = get_mysql()
    attacker_id = session.get('user_id')
    flag = (flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-004')
            if attacker_id else flag_engine.plant_secret(mysql))
    config_dump['CTF_FLAG'] = flag

    return f"<h1>Session Debug</h1><pre>{session}</pre><h1>Config Debug</h1><pre>{config_dump}</pre>"
