"""
Aura Financial Tracker - Secure Version
Budgets API Routes
Sprint 13: Transfers + Budgets + Savings Goals

Security properties: every route requires @api_login_required; ownership
enforced at the model layer; category_id in category_limits is validated as
belonging to the session user before a limit is attached to it.
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.budget import Budget
from models.category import Category
from routes.main import api_login_required

api_budgets_bp = Blueprint('api_budgets', __name__)


def get_mysql():
    return current_app.extensions['mysql']


def _validate_positive(raw):
    try:
        val = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


@api_budgets_bp.route('/list', methods=['GET'])
@api_login_required
def list_budgets():
    mysql = get_mysql()
    budgets = Budget.get_all_by_user(mysql, session['user_id'])
    return jsonify({'success': True, 'budgets': [_budget_to_dict(b) for b in budgets]}), 200


@api_budgets_bp.route('/<int:budget_id>', methods=['GET'])
@api_login_required
def get_budget(budget_id):
    mysql = get_mysql()
    user_id = session['user_id']
    budget = Budget.get_by_id(mysql, budget_id, user_id)
    if not budget:
        return jsonify({'success': False, 'message': 'Budget not found'}), 404

    limits = Budget.get_category_limits(mysql, budget_id, user_id)
    spending = Budget.get_spending(mysql, budget_id, user_id)

    spending_map = {row[4]: float(row[7]) for row in spending}
    for limit in limits:
        limit['spent'] = spending_map.get(limit['category_id'], 0.0)
        limit['remaining'] = max(limit['limit_amount'] - limit['spent'], 0)

    return jsonify({'success': True, 'budget': _budget_to_dict(budget), 'category_limits': limits}), 200


@api_budgets_bp.route('/create', methods=['POST'])
@api_login_required
def create_budget():
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = session['user_id']

        name = (data.get('name') or '').strip()
        period_type = data.get('period_type', 'monthly')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        total_limit = _validate_positive(data.get('total_limit', 0))

        if not name or len(name) > 100 or period_type not in ('monthly', 'yearly', 'custom'):
            return jsonify({'success': False, 'message': 'name (max 100 characters) and a valid period_type are required'}), 400
        if not start_date or not end_date:
            return jsonify({'success': False, 'message': 'start_date and end_date are required'}), 400
        if total_limit is None:
            return jsonify({'success': False, 'message': 'total_limit must be a positive number'}), 400

        mysql = get_mysql()
        success, message, budget_id = Budget.create(
            mysql, user_id, name, period_type, start_date, end_date, total_limit
        )

        if success:
            for cl in data.get('category_limits', []):
                limit_amount = _validate_positive(cl.get('limit_amount'))
                category_id = cl.get('category_id')
                if not category_id or limit_amount is None:
                    continue
                try:
                    category_id = int(category_id)
                except (TypeError, ValueError):
                    continue
                if Category.get_by_id(mysql, category_id, user_id):
                    Budget.set_category_limit(mysql, budget_id, user_id, category_id, limit_amount)
            return jsonify({'success': True, 'message': message, 'budget_id': budget_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_budgets_bp.route('/<int:budget_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_budget(budget_id):
    mysql = get_mysql()
    success, message = Budget.delete(mysql, budget_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 403 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


def _budget_to_dict(b):
    return {
        'id': b.id,
        'name': b.name,
        'period_type': b.period_type,
        'start_date': str(b.start_date) if b.start_date else None,
        'end_date': str(b.end_date) if b.end_date else None,
        'total_limit': b.total_limit,
        'is_active': b.is_active,
    }
