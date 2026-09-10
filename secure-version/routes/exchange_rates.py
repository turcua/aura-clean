"""
Aura Financial Tracker - Secure Version
Exchange Rates Page Routes
Sprint 17: Multi-Currency (static rates)
"""

from flask import Blueprint, render_template
from routes.main import login_required

exchange_rates_bp = Blueprint('exchange_rates', __name__)


@exchange_rates_bp.route('/')
@login_required
def manage_exchange_rates():
    return render_template('exchange_rates/manage.html')
