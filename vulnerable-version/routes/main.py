"""
Aura Financial Tracker - Vulnerable Version
Main Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 1: Water Breathing - First Form
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from functools import wraps
from models.user import User
from utils import flag_engine

main_bp = Blueprint('main', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    return current_app.extensions['mysql']

def login_required(f):
    """
    VULNERABILITY: Weak session validation
    Only checks if user_id exists in session, doesn't validate token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # VULN: Only checks session existence, not validity
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        # VULN: No actual session token validation
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
    User dashboard
    VULNERABILITY: No proper session validation
    """
    username = session.get('username', 'User')
    
    # Get user details
    mysql = get_mysql()
    user = User.get_user_by_id(mysql, session['user_id'])
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('dashboard.html', username=username, user=user)

@main_bp.route('/profile')
@login_required
def profile():
    """
    User profile page
    VULNERABILITY: Insecure Direct Object Reference (IDOR)
    """
    # VULN: Can access any user's profile by manipulating user_id parameter
    user_id = request.args.get('user_id', session['user_id'])

    mysql = get_mysql()
    user = User.get_user_by_id(mysql, user_id)

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Sprint 43 (VULN-008 flag): genuinely viewing someone else's profile
    # via the IDOR is the proof — no pre-seeded "victim" data required.
    if str(user_id) != str(session['user_id']):
        flag_engine.mark_solved_with_flag(mysql, session.get('user_id'), 'VULN-008')

    # Sprint 43 (VULN-001 flag): the plaintext password is shown right on
    # this page (profile.html) regardless of whose profile it is — the
    # vulnerability is the disclosure itself, not who it's disclosed to.
    flag_engine.mark_solved_with_flag(mysql, session.get('user_id'), 'VULN-001')

    return render_template('profile.html', user=user)

# VULNERABILITY: Admin panel with no authentication check
@main_bp.route('/admin')
def admin():
    """
    VULNERABILITY: Admin panel accessible without proper authorization
    VULNERABILITY: SQL Injection in user listing
    """
    mysql = get_mysql()
    cursor = mysql.connection.cursor()
    
    # VULN: No authentication check
    # VULN: SQL Injection if search parameter is used
    search = request.args.get('search', '')
    
    if search:
        # VULN: SQL Injection vulnerability
        query = f"SELECT id, username, email, password FROM users WHERE username LIKE '%{search}%'"
    else:
        query = "SELECT id, username, email, password FROM users"
    
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()

    # Sprint 43 (VULN-002 flag): reaching this page at all is the proof —
    # there's no authorization check of any kind, session or not.
    flag_engine.mark_solved_with_flag(mysql, session.get('user_id'), 'VULN-002')

    return render_template('admin.html', users=users)
