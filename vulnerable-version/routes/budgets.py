"""
Aura Financial Tracker - Vulnerable Version
Budgets UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""

from flask import Blueprint, render_template, session, redirect, url_for

budgets_bp = Blueprint('budgets', __name__)


@budgets_bp.route('/')
def manage_budgets():
    """VULNERABILITY: Minimal auth check"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('budgets/manage.html')
