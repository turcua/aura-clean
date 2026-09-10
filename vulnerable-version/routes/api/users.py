"""
Aura Financial Tracker - Vulnerable Version
Users API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 53 (UI-02): per-user UI preferences.
"""

from flask import Blueprint, request, jsonify, session
from models.user import User
from utils import flag_engine

api_users_bp = Blueprint('api_users', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_users_bp.route('/stat-card-order', methods=['GET'])
def get_stat_card_order():
    """
    VULNERABILITIES:
    - No authentication check
    - IDOR: returns any user's saved order via user_id param
    - SQL Injection via user_id (see User.get_stat_card_order)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        order_str = User.get_stat_card_order(mysql, user_id)
        order = order_str.split(',') if order_str else None

        own_id = session.get('user_id')
        if own_id and str(own_id) != str(user_id) and order:
            flag_engine.mark_solved_with_flag(mysql, own_id, 'VULN-086')

        return jsonify({'success': True, 'order': order}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_users_bp.route('/stat-card-order', methods=['POST'])
def set_stat_card_order():
    """
    VULNERABILITIES:
    - No authentication check
    - No CSRF protection
    - IDOR: writes any user's order via user_id in the payload
    - SQL Injection via user_id and order (see User.set_stat_card_order)
    """
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        order = data.get('order', [])

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        success = User.set_stat_card_order(mysql, user_id, ','.join(order) if isinstance(order, list) else str(order))

        if success:
            attacker_id = session.get('user_id')
            if attacker_id and str(user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-086')
            return jsonify({'success': True, 'message': 'Stat card order updated'}), 200
        return jsonify({'success': False, 'message': 'Could not save stat card order'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
