"""
Aura Financial Tracker - Secure Version
Budget Page Routes
Sprint 13: Transfers + Budgets + Savings Goals
"""

from flask import Blueprint, render_template
from routes.main import login_required

budgets_bp = Blueprint('budgets', __name__)


@budgets_bp.route('/')
@login_required
def manage_budgets():
    return render_template('budgets/manage.html')
