"""
Aura Financial Tracker - Secure Version
Savings Goals API Routes
Sprint 13: Transfers + Budgets + Savings Goals

Security properties: every route requires @api_login_required; ownership
enforced at the model layer; account_id validated as belonging to the
session user before being attached to a goal.
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.savings_goal import SavingsGoal
from models.account import Account
from routes.main import api_login_required

api_goals_bp = Blueprint('api_goals', __name__)


def get_mysql():
    return current_app.extensions['mysql']


def _validate_account(mysql, account_id, user_id):
    if account_id in (None, '', 'null'):
        return None
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return False
    return account_id if Account.get_by_id(mysql, account_id, user_id) else False


def _validate_amount(raw, allow_zero=True):
    try:
        val = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    if val < 0 or (val == 0 and not allow_zero):
        return None
    return val


@api_goals_bp.route('/list', methods=['GET'])
@api_login_required
def list_goals():
    mysql = get_mysql()
    goals = SavingsGoal.get_all_by_user(mysql, session['user_id'])
    return jsonify({'success': True, 'goals': [_goal_to_dict(g) for g in goals]}), 200


@api_goals_bp.route('/<int:goal_id>', methods=['GET'])
@api_login_required
def get_goal(goal_id):
    mysql = get_mysql()
    goal = SavingsGoal.get_by_id(mysql, goal_id, session['user_id'])
    if goal:
        return jsonify({'success': True, 'goal': _goal_to_dict(goal)}), 200
    return jsonify({'success': False, 'message': 'Goal not found'}), 404


@api_goals_bp.route('/create', methods=['POST'])
@api_login_required
def create_goal():
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = session['user_id']
        mysql = get_mysql()

        name = (data.get('name') or '').strip()
        target_amount = _validate_amount(data.get('target_amount'), allow_zero=False)
        current_amount = _validate_amount(data.get('current_amount', 0))
        account_id = _validate_account(mysql, data.get('account_id'), user_id)
        target_date = data.get('target_date') or None
        monthly_target = data.get('monthly_target') or None

        if not name or len(name) > 100:
            return jsonify({'success': False, 'message': 'name is required (max 100 characters)'}), 400
        if target_amount is None:
            return jsonify({'success': False, 'message': 'target_amount must be a positive number'}), 400
        if current_amount is None:
            return jsonify({'success': False, 'message': 'current_amount must be a non-negative number'}), 400
        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400

        success, message, goal_id = SavingsGoal.create(
            mysql, user_id, account_id, name, target_amount, current_amount, target_date, monthly_target
        )
        if success:
            return jsonify({'success': True, 'message': message, 'goal_id': goal_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_goals_bp.route('/<int:goal_id>/update', methods=['POST', 'PUT'])
@api_login_required
def update_goal(goal_id):
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = session['user_id']
        mysql = get_mysql()

        name = (data.get('name') or '').strip()
        target_amount = _validate_amount(data.get('target_amount'), allow_zero=False)
        current_amount = _validate_amount(data.get('current_amount', 0))
        account_id = _validate_account(mysql, data.get('account_id'), user_id)
        target_date = data.get('target_date') or None
        monthly_target = data.get('monthly_target') or None
        status = data.get('status', 'active')

        if not name or len(name) > 100 or target_amount is None or current_amount is None:
            return jsonify({'success': False, 'message': 'Invalid input'}), 400
        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if status not in ('active', 'achieved', 'paused'):
            return jsonify({'success': False, 'message': 'Invalid status'}), 400

        success, message = SavingsGoal.update(
            mysql, goal_id, user_id, account_id, name, target_amount, current_amount,
            target_date, monthly_target, status
        )
        if success:
            return jsonify({'success': True, 'message': message}), 200
        status_code = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status_code
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_goals_bp.route('/<int:goal_id>/progress', methods=['POST'])
@api_login_required
def add_progress(goal_id):
    try:
        data = request.get_json() if request.is_json else request.form
        amount = _validate_amount(data.get('amount'), allow_zero=False)
        if amount is None:
            return jsonify({'success': False, 'message': 'amount must be a positive number'}), 400

        mysql = get_mysql()
        success, message = SavingsGoal.add_progress(mysql, goal_id, session['user_id'], amount)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_goals_bp.route('/<int:goal_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_goal(goal_id):
    mysql = get_mysql()
    success, message = SavingsGoal.delete(mysql, goal_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 403 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


def _goal_to_dict(g):
    return {
        'id': g.id,
        'account_id': g.account_id,
        'name': g.name,
        'target_amount': g.target_amount,
        'current_amount': g.current_amount,
        'progress_percent': g.progress_percent,
        'remaining_amount': g.remaining_amount,
        'target_date': str(g.target_date) if g.target_date else None,
        'monthly_target': g.monthly_target,
        'status': g.status,
    }
