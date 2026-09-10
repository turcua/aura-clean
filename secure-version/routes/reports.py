"""
Aura Financial Tracker - Secure Version
Reports Page Route
Sprint 14: Export/Import + Reports + Multi-Dashboard System
"""

from flask import Blueprint, render_template
from routes.main import login_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def reports_index():
    return render_template('reports/index.html')
