"""
Aura Financial Tracker - Secure Version
Main Routes
Sprint 1: Water Breathing - First Form
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, jsonify
from functools import wraps
from models.user import User

main_bp = Blueprint('main', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    return current_app.extensions['mysql']

def login_required(f):
    """
    Decorator to require login for protected page routes.
    Validates session token on each request; redirects to login on failure.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))

        # Validate session token
        mysql = get_mysql()
        is_valid, user_id = User.validate_session(mysql, session['session_token'])

        if not is_valid or user_id != session['user_id']:
            session.clear()
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function

def api_login_required(f):
    """
    Decorator to require login for JSON API routes.
    Same session/token validation as login_required, but returns a 401 JSON
    error instead of an HTML redirect — a redirect would break fetch().json()
    on the frontend, since it would follow through to the login page's HTML.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        mysql = get_mysql()
        is_valid, user_id = User.validate_session(mysql, session['session_token'])

        if not is_valid or user_id != session['user_id']:
            session.clear()
            return jsonify({'success': False, 'message': 'Session expired, please log in again'}), 401

        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    """
    Sprint 57 (ENH-02): same session/token validation as api_login_required,
    plus an is_admin check, for the new admin-panel action endpoints
    (routes/api/admin.py). session['is_admin'] is safe to trust here for
    the same reason the /admin page route already trusts it: it's only
    ever set at login time from a fresh DB read (routes/auth.py), never
    from anything client-supplied.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401

        mysql = get_mysql()
        is_valid, user_id = User.validate_session(mysql, session['session_token'])

        if not is_valid or user_id != session['user_id']:
            session.clear()
            return jsonify({'success': False, 'message': 'Session expired, please log in again'}), 401

        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    """Home page"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    User dashboard - requires authentication.
    Sprint 14: the multi-dashboard/widget system is fetched entirely client-side
    via /api/dashboards/* and /api/transactions/summary — no server-rendered
    stats or transaction list needed here (contrast with the Sprint 11 version,
    which passed summary/recent_transactions into the template directly).
    """
    username = session.get('username', 'User')

    mysql = get_mysql()
    user = User.get_user_by_id(mysql, session['user_id'])

    if not user:
        session.clear()
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('dashboard.html', username=username, user=user)

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    mysql = get_mysql()
    user = User.get_user_by_id(mysql, session['user_id'])

    if not user:
        session.clear()
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('profile.html', user=user)

@main_bp.route('/admin')
@login_required
def admin():
    """
    Sprint 34: contrast with vulnerable-version's /admin (VULN-002) — gated
    behind login *and* an is_admin check (not just "any logged-in user"),
    and never selects/displays password hashes (see User.get_all_users).
    session['is_admin'] is trusted here because it's only ever set at login
    time from a fresh DB read (routes/auth.py), not from anything client-
    supplied.
    """
    if not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('main.dashboard'))

    mysql = get_mysql()
    users = User.get_all_users(mysql)
    return render_template('admin.html', users=users)
