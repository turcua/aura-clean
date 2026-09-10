"""
Aura Financial Tracker - Secure Version
Savings Goal Page Routes
Sprint 13: Transfers + Budgets + Savings Goals
"""

from flask import Blueprint, render_template
from routes.main import login_required

goals_bp = Blueprint('goals', __name__)


@goals_bp.route('/')
@login_required
def manage_goals():
    return render_template('goals/manage.html')
