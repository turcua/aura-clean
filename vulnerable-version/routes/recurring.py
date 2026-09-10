"""
Aura Financial Tracker - Vulnerable Version
Recurring Transactions UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 3: Shadow Extractor
"""

from flask import Blueprint, render_template, session, redirect, url_for

recurring_bp = Blueprint('recurring', __name__)


@recurring_bp.route('/')
def manage_recurring():
    """VULNERABILITY: Minimal auth check, no role verification"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('recurring/manage.html')
