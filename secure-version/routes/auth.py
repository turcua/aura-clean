"""
Aura Financial Tracker - Secure Version
Authentication Routes
Sprint 1: Water Breathing - First Form
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_mysqldb import MySQL
from models.user import User
from routes.main import login_required
from extensions import limiter
from datetime import datetime
from utils.mailer import send_email
import re
import pyotp
import qrcode
import io
import base64

auth_bp = Blueprint('auth', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    return current_app.extensions['mysql']

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format - only alphanumeric and underscore"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '/', '\\']
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text.strip()

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=["POST"])
def register():
    """
    User registration with input validation and CSRF protection.
    Sprint 15: rate-limited to 5 POSTs/hour per IP — this is on top of, not a
    replacement for, the per-account lockout in User.authenticate(); it
    throttles registration-spam/enumeration from a single IP regardless of
    which username is being tried.
    """
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Input validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        # Validate username format
        if not validate_username(username):
            flash('Username must be 3-20 characters long and contain only letters, numbers, and underscores', 'danger')
            return render_template('register.html')
        
        # Validate email format
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return render_template('register.html')
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Sanitize inputs
        username = sanitize_input(username)
        email = sanitize_input(email)
        
        # Create user
        mysql = get_mysql()
        success, message, user_id = User.create_user(mysql, username, email, password)
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    """
    Sprint 52 (ENH-03). Always shows the same generic confirmation message
    regardless of whether the email actually matched an account — the
    difference would let an attacker enumerate registered emails one probe
    at a time. Rate-limited same as register(), on top of (not instead of)
    that generic-response protection, since a slow enough attacker could
    otherwise still time responses or watch for delivery.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:
            mysql = get_mysql()
            token = User.generate_reset_token(mysql, email)
            if token:
                reset_link = url_for('auth.reset_password', token=token, _external=True)
                send_email(
                    email,
                    'Aura — Password Reset Request',
                    f'Someone requested a password reset for this account.\n\n'
                    f'Reset your password: {reset_link}\n\n'
                    f'This link expires in {current_app.config["PASSWORD_RESET_TOKEN_EXPIRY_MINUTES"]} minutes. '
                    f'If you did not request this, you can safely ignore this email.'
                )
        flash('If that email is registered, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=["POST"])
def reset_password(token):
    """Sprint 52 (ENH-03)."""
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

    # GET: verify the token up front so an expired/invalid link shows a
    # clear message instead of a form that will only fail on submit.
    if not User.verify_reset_token(mysql, token):
        flash('This reset link is invalid or has expired', 'danger')
        return redirect(url_for('auth.forgot_password'))

    return render_template('reset_password.html', token=token)


def _complete_login(mysql, user):
    """
    Sprint 52: factored out of login() so both the no-2FA path and the
    post-verify_2fa() path share the exact same session-creation logic —
    previously this only existed inline in login().
    """
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')

    session_created, session_token = User.create_session(mysql, user.id, ip_address, user_agent)

    if session_created:
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['session_token'] = session_token
        session['is_admin'] = user.is_admin
        session['ai_chat_since'] = datetime.utcnow().isoformat()
        session.pop('pending_2fa_user_id', None)

        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        flash('Failed to create session. Please try again.', 'danger')
        return render_template('login.html')


@auth_bp.route('/2fa/verify', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def verify_2fa():
    """
    Sprint 52 (ENH-04) — the login-time TOTP challenge. Only reachable via
    the pending_2fa_user_id set by login() right after a correct password;
    there's no other way to reach a real session for an account with 2FA
    enabled. Rate-limited same as login() itself, so a 6-digit code can't
    be brute-forced any faster than a password could.
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


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    """
    User login with rate limiting.
    Sprint 15: rate-limited to 10 POSTs/minute per IP — this is on top of, not
    a replacement for, the per-account lockout in User.authenticate(); it
    throttles credential-stuffing against many different usernames from a
    single IP, which a per-account lockout alone doesn't prevent.
    """
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Input validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('login.html')
        
        # Sanitize username
        username = sanitize_input(username)
        
        # Authenticate user
        mysql = get_mysql()
        success, message, user = User.authenticate(mysql, username, password)

        if success:
            # Sprint 52 (ENH-04): password check passed, but if 2FA is
            # enabled the real session isn't created yet — a pending state
            # gates on the TOTP code first. Nothing session-wise beyond this
            # pending marker is trusted until verify_2fa() succeeds.
            if user.totp_enabled:
                session['pending_2fa_user_id'] = user.id
                return redirect(url_for('auth.verify_2fa'))

            return _complete_login(mysql, user)
        else:
            flash(message, 'danger')
            return render_template('login.html')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """User logout - invalidate session"""
    
    session_token = session.get('session_token')
    
    if session_token:
        mysql = get_mysql()
        User.invalidate_session(mysql, session_token)
    
    # Clear session
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.index'))


def _qr_data_uri(secret, username):
    """Sprint 52 (ENH-04) — renders the TOTP provisioning URI as an inline
    base64 PNG, avoiding a separate image-serving route/session-state just
    to display a setup QR code once."""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=current_app.config['TOTP_ISSUER_NAME'])
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


@auth_bp.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """
    Sprint 52 (ENH-04). GET generates (or regenerates) a pending secret and
    shows its QR code — totp_enabled stays FALSE until the code below is
    confirmed, so refreshing this page or abandoning it never silently
    turns 2FA on. POST verifies the first code and enables it.
    """
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
    """Sprint 52 (ENH-04) — requires the current TOTP code, not just being
    logged in, so a hijacked/left-open session alone can't turn 2FA off."""
    mysql = get_mysql()
    user_id = session['user_id']
    code = request.form.get('code', '').strip()

    if User.verify_totp_code(mysql, user_id, code):
        User.disable_totp(mysql, user_id)
        flash('Two-factor authentication has been disabled.', 'success')
    else:
        flash('Invalid authentication code — 2FA was not disabled.', 'danger')
    return redirect(url_for('main.profile'))
