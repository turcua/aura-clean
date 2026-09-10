"""
Aura Financial Tracker - Secure Version
Account Page Routes
Sprint 12: Accounts + Recurring Transactions
"""

from flask import Blueprint, render_template
from routes.main import login_required

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/')
@login_required
def manage_accounts():
    return render_template('accounts/manage.html')
