"""
Aura Financial Tracker - Vulnerable Version
Savings Goals API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""

from flask import Blueprint, request, jsonify, session
from models.savings_goal import SavingsGoal
from utils import flag_engine

api_goals_bp = Blueprint('api_goals', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_goals_bp.route('/list', methods=['GET'])
def list_goals():
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        goals = SavingsGoal.get_all_by_user(mysql, user_id)
        return jsonify({'success': True, 'goals': [_goal_to_dict(g) for g in goals]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_goals_bp.route('/<int:goal_id>', methods=['GET'])
def get_goal(goal_id):
    """VULNERABILITIES: No auth, IDOR"""
    try:
        mysql = get_mysql()
        goal = SavingsGoal.get_by_id(mysql, goal_id)
        if goal:
            # Sprint 44 (VULN-041 flag): genuinely reading someone else's
            # goal via the IDOR is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(goal.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-041')
            return jsonify({'success': True, 'goal': _goal_to_dict(goal)}), 200
        return jsonify({'success': False, 'message': 'Goal not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_goals_bp.route('/create', methods=['POST'])
def create_goal():
    """VULNERABILITIES: No auth, No CSRF, SQL Injection, Mass assignment, No validation"""
    try:
        data = request.get_json() if request.is_json else request.form
        name = data.get('name', '')

        mysql = get_mysql()
        success, message, goal_id = SavingsGoal.create(
            mysql,
            data.get('user_id'),
            data.get('account_id') or None,
            name,
            data.get('target_amount', 0),
            data.get('current_amount', 0),
            data.get('target_date') or None,
            data.get('monthly_target') or None
        )

        if success:
            # Sprint 44 (VULN-038 flag): a literal quote in the name field
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate goal name essentially never contains one.
            if name and "'" in str(name):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-038')
            return jsonify({'success': True, 'message': message, 'goal_id': goal_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_goals_bp.route('/<int:goal_id>/update', methods=['POST', 'PUT'])
def update_goal(goal_id):
    """
    VULNERABILITIES: No auth, IDOR, SQL Injection, Mass assignment
    VULNERABILITY: BUG-008 - status not auto-set to 'achieved' even at 100%
    """
    try:
        data = request.get_json() if request.is_json else request.form

        mysql = get_mysql()
        success, message = SavingsGoal.update(
            mysql, goal_id,
            data.get('user_id'),
            data.get('account_id') or None,
            data.get('name', ''),
            data.get('target_amount', 0),
            data.get('current_amount', 0),
            data.get('target_date') or None,
            data.get('monthly_target') or None,
            data.get('status', 'active')
        )

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_goals_bp.route('/<int:goal_id>/progress', methods=['POST'])
def add_progress(goal_id):
    """
    Add contribution to a savings goal.
    VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF
    VULNERABILITY: BUG-008 - does not auto-achieve goal at 100%
    """
    try:
        data = request.get_json() if request.is_json else request.form
        amount = data.get('amount', 0)

        mysql = get_mysql()
        success, message = SavingsGoal.add_progress(mysql, goal_id, amount)

        if success:
            # Sprint 44 (VULN-045 flag, weak fit like VULN-034/035 —
            # business-logic bugs don't leak data): credited when the goal
            # has genuinely reached/exceeded its target but status is still
            # not 'achieved' — the exact scenario the bug describes, not
            # just any contribution.
            updated_goal = SavingsGoal.get_by_id(mysql, goal_id)
            if updated_goal and updated_goal.status != 'achieved' and \
               float(updated_goal.current_amount) >= float(updated_goal.target_amount) > 0:
                attacker_id = session.get('user_id')
                if attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-045')
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_goals_bp.route('/<int:goal_id>/delete', methods=['POST', 'DELETE'])
def delete_goal(goal_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF"""
    try:
        mysql = get_mysql()
        success, message = SavingsGoal.delete(mysql, goal_id)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _goal_to_dict(g):
    return {
        'id': g.id,
        'user_id': g.user_id,  # VULN: Exposed
        'account_id': g.account_id,
        'name': g.name,
        'target_amount': g.target_amount,
        'current_amount': g.current_amount,
        'progress_percent': g.progress_percent,
        'remaining_amount': g.remaining_amount,
        'target_date': str(g.target_date) if g.target_date else None,
        'monthly_target': g.monthly_target,
        'status': g.status
    }
