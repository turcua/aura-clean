"""
Aura Financial Tracker - Vulnerable Version
Exchange Rates UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 17: Multi-Currency (static rates)
"""

from flask import Blueprint, render_template, session, redirect, url_for

exchange_rates_bp = Blueprint('exchange_rates', __name__)


@exchange_rates_bp.route('/')
def manage_exchange_rates():
    """VULNERABILITY: Minimal auth check"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('exchange_rates/manage.html')
