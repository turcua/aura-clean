"""
Aura Financial Tracker - Secure Version
Recurring Transaction Page Routes
Sprint 12: Accounts + Recurring Transactions
"""

from flask import Blueprint, render_template
from routes.main import login_required

recurring_bp = Blueprint('recurring', __name__)


@recurring_bp.route('/')
@login_required
def manage_recurring():
    return render_template('recurring/manage.html')
