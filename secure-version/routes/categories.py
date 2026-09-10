"""
Aura Financial Tracker - Secure Version
Category Page Routes
Sprint 11: Core Financial Tracking
"""

from flask import Blueprint, render_template
from routes.main import login_required

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/')
@login_required
def manage_categories():
    """Display category management page. Auth enforced by @login_required."""
    return render_template('categories/manage.html')
