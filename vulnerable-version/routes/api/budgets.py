"""
Aura Financial Tracker - Vulnerable Version
Budgets API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""

from flask import Blueprint, request, jsonify, session
from models.budget import Budget
from utils import flag_engine

api_budgets_bp = Blueprint('api_budgets', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_budgets_bp.route('/list', methods=['GET'])
def list_budgets():
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        budgets = Budget.get_all_by_user(mysql, user_id)
        return jsonify({'success': True, 'budgets': [_budget_to_dict(b) for b in budgets]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_budgets_bp.route('/<int:budget_id>', methods=['GET'])
def get_budget(budget_id):
    """VULNERABILITIES: No auth, IDOR"""
    try:
        mysql = get_mysql()
        budget = Budget.get_by_id(mysql, budget_id)
        if not budget:
            return jsonify({'success': False, 'message': 'Budget not found'}), 404

        # Sprint 44 (VULN-040 flag): genuinely reading someone else's
        # budget via the IDOR is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(budget.user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-040')

        limits = Budget.get_category_limits(mysql, budget_id)
        spending = Budget.get_spending(mysql, budget_id)

        spending_map = {}
        for row in spending:
            spending_map[row[4]] = float(row[7])

        for limit in limits:
            limit['spent'] = spending_map.get(limit['category_id'], 0.0)
            limit['remaining'] = max(limit['limit_amount'] - limit['spent'], 0)

        return jsonify({
            'success': True,
            'budget': _budget_to_dict(budget),
            'category_limits': limits
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_budgets_bp.route('/create', methods=['POST'])
def create_budget():
    """VULNERABILITIES: No auth, No CSRF, SQL Injection, Mass assignment, No validation"""
    try:
        data = request.get_json() if request.is_json else request.form

        user_id = data.get('user_id')
        name = data.get('name', '')
        period_type = data.get('period_type', 'monthly')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        total_limit = data.get('total_limit', 0)

        mysql = get_mysql()
        success, message, budget_id = Budget.create(
            mysql, user_id, name, period_type, start_date, end_date, total_limit
        )

        if success:
            # Save category limits if provided
            category_limits = data.get('category_limits', [])
            for cl in category_limits:
                Budget.set_category_limit(mysql, budget_id, cl.get('category_id'), cl.get('limit_amount', 0))

            # Sprint 44 (VULN-037 flag): a literal quote in the name field
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate budget name essentially never contains one.
            if name and "'" in str(name):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-037')

            return jsonify({'success': True, 'message': message, 'budget_id': budget_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_budgets_bp.route('/<int:budget_id>/update', methods=['POST', 'PUT'])
def update_budget(budget_id):
    """
    VULNERABILITIES: No auth, IDOR, SQL Injection, Mass assignment
    VULNERABILITY: BUG-005 - set_category_limit always INSERTs, never UPDATEs
    """
    try:
        data = request.get_json() if request.is_json else request.form

        mysql = get_mysql()
        success, message = Budget.update(
            mysql, budget_id,
            data.get('user_id'),
            data.get('name', ''),
            data.get('period_type', 'monthly'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('total_limit', 0)
        )

        if success:
            # VULN: BUG-005 - this always INSERTs category limits, creating duplicates
            category_limits = data.get('category_limits', [])
            for cl in category_limits:
                Budget.set_category_limit(mysql, budget_id, cl.get('category_id'), cl.get('limit_amount', 0))

            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_budgets_bp.route('/<int:budget_id>/category-limit/delete', methods=['POST'])
def delete_category_limit(budget_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        data = request.get_json() if request.is_json else request.form
        bc_id = data.get('bc_id')

        mysql = get_mysql()
        success = Budget.delete_category_limit(mysql, bc_id)

        if success:
            return jsonify({'success': True, 'message': 'Category limit removed'}), 200
        return jsonify({'success': False, 'message': 'Failed to remove'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_budgets_bp.route('/<int:budget_id>/delete', methods=['POST', 'DELETE'])
def delete_budget(budget_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF"""
    try:
        mysql = get_mysql()
        success, message = Budget.delete(mysql, budget_id)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _budget_to_dict(b):
    return {
        'id': b.id,
        'user_id': b.user_id,  # VULN: Exposed
        'name': b.name,
        'period_type': b.period_type,
        'start_date': str(b.start_date) if b.start_date else None,
        'end_date': str(b.end_date) if b.end_date else None,
        'total_limit': b.total_limit,
        'is_active': b.is_active
    }
