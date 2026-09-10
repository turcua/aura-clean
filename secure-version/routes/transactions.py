"""
Aura Financial Tracker - Secure Version
Transaction Page Routes
Sprint 11: Core Financial Tracking
"""

from flask import Blueprint, render_template
from routes.main import login_required

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/')
@login_required
def list_transactions():
    """Display transactions list page. Auth enforced by @login_required."""
    return render_template('transactions/list.html')
