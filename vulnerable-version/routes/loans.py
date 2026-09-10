"""
Aura Financial Tracker - Vulnerable Version
Loan Intelligence UI Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 30: Beast Breathing - Devour
"""

from flask import Blueprint, render_template, session, redirect, url_for

loans_bp = Blueprint('loans', __name__)


@loans_bp.route('/')
def manage_loans():
    """
    VULNERABILITY: No proper login check (only checks session key existence),
    matching every other page route in this version (see accounts.py).
    """
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('loans/manage.html')
