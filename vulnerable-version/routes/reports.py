"""
Aura Financial Tracker - Vulnerable Version
Reports UI Route (WITH INTENTIONAL VULNERABILITIES)
Sprint 5: Shadow Ledger
"""

from flask import Blueprint, render_template, session, redirect, url_for

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
def reports_index():
    """VULNERABILITY: Minimal auth check"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('reports/index.html')
