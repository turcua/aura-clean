"""
Aura Financial Tracker - Vulnerable Version
Category Traditional Routes (HTML Pages)
Sprint 2: Thunder Breathing - Second Form
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/')
def manage_categories():
    """
    Display category management page
    
    VULNERABILITY: No login required check (relies on session)
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to manage categories', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('categories/manage.html')
