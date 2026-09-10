"""
Aura Financial Tracker - Vulnerable Version
Transaction Traditional Routes (HTML Pages)
Sprint 2: Thunder Breathing - Second Form
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/')
def list_transactions():
    """
    Display transactions list page
    
    VULNERABILITY: No login required check (but relies on session)
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to view transactions', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('transactions/list.html')
