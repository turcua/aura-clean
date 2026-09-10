"""
Aura Financial Tracker - Vulnerable Version
Accounts UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 3 & 4: Shadow Extractor
"""

from flask import Blueprint, render_template, session, redirect, url_for

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/')
def manage_accounts():
    """
    VULNERABILITY: No proper login check (only checks session key existence)
    VULNERABILITY: user_id passed to template directly from session without validation
    """
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('accounts/manage.html')
