"""
Aura Financial Tracker - Vulnerable Version
Savings Goals UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""

from flask import Blueprint, render_template, session, redirect, url_for

goals_bp = Blueprint('goals', __name__)


@goals_bp.route('/')
def manage_goals():
    """VULNERABILITY: Minimal auth check"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('goals/manage.html')
