"""
Aura Financial Tracker - Vulnerable Version
Recurring Transactions API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 3: Shadow Extractor
"""

from flask import Blueprint, request, jsonify, session
from models.recurring_transaction import RecurringTransaction
from models.account import Account
from utils import flag_engine

api_recurring_bp = Blueprint('api_recurring', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_recurring_bp.route('/list', methods=['GET'])
def list_recurring():
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        items = RecurringTransaction.get_all_by_user(mysql, user_id)
        result = []
        for r in items:
            currency = 'RON'
            if r.account_id:
                account = Account.get_by_id(mysql, r.account_id)
                if account:
                    currency = account.currency
            result.append(_rt_to_dict(r, currency=currency))
        return jsonify({'success': True, 'recurring': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/<int:rt_id>', methods=['GET'])
def get_recurring(rt_id):
    """VULNERABILITIES: No auth, IDOR"""
    try:
        mysql = get_mysql()
        rt = RecurringTransaction.get_by_id(mysql, rt_id)
        if rt:
            # Sprint 44 (VULN-031 flag): genuinely reading someone else's
            # recurring transaction via the IDOR is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(rt.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-031')

            currency = 'RON'
            if rt.account_id:
                account = Account.get_by_id(mysql, rt.account_id)
                if account:
                    currency = account.currency
            return jsonify({'success': True, 'recurring': _rt_to_dict(rt, currency=currency)}), 200
        return jsonify({'success': False, 'message': 'Recurring transaction not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/create', methods=['POST'])
def create_recurring():
    """
    VULNERABILITIES:
    - No auth, No CSRF, SQL Injection, Mass assignment, No input validation
    ENH-002: accepts is_template flag to save as template
    """
    try:
        data = request.get_json() if request.is_json else request.form

        user_id = data.get('user_id')
        account_id = data.get('account_id')
        to_account_id = data.get('to_account_id') or None
        category_id = data.get('category_id') or None
        type = data.get('type')
        amount = data.get('amount')
        description = data.get('description', '')
        frequency = data.get('frequency')
        start_date = data.get('start_date')
        end_date = data.get('end_date') or None
        is_template = data.get('is_template', False)
        if isinstance(is_template, str):
            is_template = is_template.lower() in ('true', '1', 'yes')
        loan_id = data.get('loan_id') or None  # Sprint 51 (ENH-12) — no ownership check, matching category_id above

        mysql = get_mysql()
        success, message, rt_id = RecurringTransaction.create(
            mysql, user_id, account_id, to_account_id, category_id,
            type, amount, description, frequency, start_date, end_date,
            is_template=is_template, loan_id=loan_id
        )

        if success:
            # Sprint 44 (VULN-029 flag): a literal quote in the description
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate description essentially never contains one.
            if description and "'" in str(description):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-029')
            return jsonify({'success': True, 'message': message, 'id': rt_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    List template recurring transactions for a user.
    VULNERABILITIES: No auth, IDOR, SQL Injection
    ENH-002: Recurring transaction templates
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        templates = RecurringTransaction.get_templates_by_user(mysql, user_id)
        result = []
        for t in templates:
            currency = 'RON'
            if t.account_id:
                account = Account.get_by_id(mysql, t.account_id)
                if account:
                    currency = account.currency
            result.append(_rt_to_dict(t, currency=currency))
        return jsonify({'success': True, 'templates': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/from-template/<int:template_id>', methods=['POST'])
def create_from_template(template_id):
    """
    Create a live recurring transaction from a saved template.
    VULNERABILITIES: No auth, IDOR (any template_id works), SQL Injection, No CSRF
    ENH-002: Recurring transaction templates
    """
    try:
        from datetime import date as _date
        data = request.get_json() if request.is_json else request.form
        mysql = get_mysql()

        # VULN: IDOR — no ownership check on template
        template = RecurringTransaction.get_by_id(mysql, template_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404

        start_date = data.get('start_date') or str(_date.today())
        end_date = data.get('end_date') or None
        user_id = data.get('user_id') or template.user_id  # VULN: Mass assignment

        success, message, rt_id = RecurringTransaction.create(
            mysql,
            user_id=user_id,
            account_id=template.account_id,
            to_account_id=template.to_account_id,
            category_id=template.category_id,
            type=template.type,
            amount=template.amount,
            description=template.description,
            frequency=template.frequency,
            start_date=start_date,
            end_date=end_date,
            is_template=False,
            loan_id=template.loan_id
        )

        if success:
            return jsonify({'success': True, 'message': 'Recurring transaction created from template', 'id': rt_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/<int:rt_id>/update', methods=['POST', 'PUT'])
def update_recurring(rt_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, Mass assignment, No CSRF"""
    try:
        data = request.get_json() if request.is_json else request.form
        rt_user_id = data.get('user_id')

        mysql = get_mysql()
        success, message = RecurringTransaction.update(
            mysql, rt_id,
            rt_user_id,
            data.get('account_id'),
            data.get('to_account_id') or None,
            data.get('category_id') or None,
            data.get('type'),
            data.get('amount'),
            data.get('description', ''),
            data.get('frequency'),
            data.get('start_date'),
            data.get('end_date') or None,
            loan_id=data.get('loan_id') or None
        )

        if success:
            # Sprint 44 (VULN-033 flag): the write succeeding under a
            # user_id that isn't the caller's own logged-in session is the
            # proof — same pattern already proven on VULN-022.
            attacker_id = session.get('user_id')
            if attacker_id and str(rt_user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-033')
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/<int:rt_id>/toggle', methods=['POST'])
def toggle_recurring(rt_id):
    """
    Pause or resume a recurring transaction.
    VULNERABILITIES: No auth, IDOR, No CSRF
    """
    try:
        data = request.get_json() if request.is_json else request.form
        is_active = data.get('is_active', True)

        mysql = get_mysql()
        success = RecurringTransaction.set_active(mysql, rt_id, is_active)

        if success:
            status = "activated" if is_active else "paused"
            return jsonify({'success': True, 'message': f'Recurring transaction {status}'}), 200
        return jsonify({'success': False, 'message': 'Failed to toggle status'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/<int:rt_id>/delete', methods=['POST', 'DELETE'])
def delete_recurring(rt_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF"""
    try:
        mysql = get_mysql()
        success, message = RecurringTransaction.delete(mysql, rt_id)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_recurring_bp.route('/trigger', methods=['POST'])
def trigger_generation():
    """
    Manually trigger recurring transaction generation.
    VULNERABILITY: No authentication required - any visitor can trigger
    VULNERABILITY: No rate limiting - can be called repeatedly
    VULNERABILITY: Exposes internal scheduler state in response
    """
    try:
        from datetime import date
        from scheduler import run_recurring_job

        mysql = get_mysql()
        count = run_recurring_job(mysql)

        return jsonify({
            'success': True,
            'message': f'Generated {count} transactions',
            'triggered_at': str(date.today()),
            'note': 'VULN: This endpoint requires no authentication'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _rt_to_dict(r, currency='RON'):
    return {
        'id': r.id,
        'user_id': r.user_id,  # VULN: Exposed
        'account_id': r.account_id,
        'to_account_id': r.to_account_id,
        'category_id': r.category_id,
        'type': r.type,
        'amount': r.amount,
        'description': r.description,
        'frequency': r.frequency,
        'start_date': str(r.start_date) if r.start_date else None,
        'end_date': str(r.end_date) if r.end_date else None,
        'next_run_date': str(r.next_run_date) if r.next_run_date else None,
        'last_run_date': str(r.last_run_date) if r.last_run_date else None,
        'is_active': r.is_active,
        'is_template': r.is_template,
        'currency': currency,
        'loan_id': r.loan_id
    }
