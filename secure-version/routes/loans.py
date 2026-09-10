"""
Aura Financial Tracker - Secure Version
Loan Intelligence Page Routes
Sprint 30: Beast Breathing - Devour
"""

from flask import Blueprint, render_template
from routes.main import login_required

loans_bp = Blueprint('loans', __name__)


@loans_bp.route('/')
@login_required
def manage_loans():
    return render_template('loans/manage.html')
