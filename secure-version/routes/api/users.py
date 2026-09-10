"""
Aura Financial Tracker - Secure Version
Users API Routes
Sprint 53 (UI-02): per-user UI preferences — the first server-persisted
preference in either version (theme/sidebar-collapsed state are both
localStorage-only).
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.user import User
from routes.main import api_login_required

api_users_bp = Blueprint('api_users', __name__)

STAT_CARD_KEYS = {'income', 'expenses', 'balance', 'budget'}


def get_mysql():
    return current_app.extensions['mysql']


@api_users_bp.route('/stat-card-order', methods=['GET'])
@api_login_required
def get_stat_card_order():
    mysql = get_mysql()
    order_str = User.get_stat_card_order(mysql, session['user_id'])
    order = order_str.split(',') if order_str else None
    return jsonify({'success': True, 'order': order}), 200


@api_users_bp.route('/stat-card-order', methods=['POST'])
@api_login_required
def set_stat_card_order():
    data = request.get_json() if request.is_json else request.form
    order = data.get('order', [])

    if not isinstance(order, list) or set(order) != STAT_CARD_KEYS:
        return jsonify({'success': False, 'message': 'order must contain exactly: income, expenses, balance, budget'}), 400

    mysql = get_mysql()
    success = User.set_stat_card_order(mysql, session['user_id'], ','.join(order))
    if success:
        return jsonify({'success': True, 'message': 'Stat card order updated'}), 200
    return jsonify({'success': False, 'message': 'Could not save stat card order'}), 400
