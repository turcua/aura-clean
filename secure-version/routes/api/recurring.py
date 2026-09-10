"""
Aura Financial Tracker - Secure Version
Recurring Transactions API Routes
Sprint 12: Accounts + Recurring Transactions

Security properties (contrast with vulnerable-version/routes/api/recurring.py):
- Every route requires @api_login_required (including /trigger — the
  vulnerable version leaves this completely open)
- user_id always from session
- Ownership enforced at the model layer
- account_id and category_id validated as belonging to the session user
  before being attached to a recurring transaction
- 'transfer' type intentionally not supported yet — the Transfer model
  lands in Sprint 13
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.recurring_transaction import RecurringTransaction
from models.account import Account
from models.category import Category
from models.loan import Loan
from routes.main import api_login_required

api_recurring_bp = Blueprint('api_recurring', __name__)


def get_mysql():
    return current_app.extensions['mysql']


def _validate_account_id(mysql, account_id, user_id):
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return False
    return account_id if Account.get_by_id(mysql, account_id, user_id) else False


def _validate_category_id(mysql, category_id, user_id):
    if category_id in (None, '', 'null'):
        return None
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False
    return category_id if Category.get_by_id(mysql, category_id, user_id) else False


def _validate_loan_id(mysql, loan_id, user_id):
    """Sprint 51 (ENH-12) — same optional-field pattern as _validate_category_id()."""
    if loan_id in (None, '', 'null'):
        return None
    try:
        loan_id = int(loan_id)
    except (TypeError, ValueError):
        return False
    return loan_id if Loan.get_by_id(mysql, loan_id, user_id) else False


def _validate_amount(raw):
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        return None
    return round(amount, 2) if amount > 0 else None


@api_recurring_bp.route('/list', methods=['GET'])
@api_login_required
def list_recurring():
    mysql = get_mysql()
    items = RecurringTransaction.get_all_by_user(mysql, session['user_id'])
    accounts = {a.id: a for a in Account.get_all_by_user(mysql, session['user_id'])}
    return jsonify({'success': True, 'recurring': [
        _rt_to_dict(r, currency=accounts[r.account_id].currency if r.account_id in accounts else 'RON')
        for r in items
    ]}), 200


@api_recurring_bp.route('/templates', methods=['GET'])
@api_login_required
def list_templates():
    mysql = get_mysql()
    templates = RecurringTransaction.get_templates_by_user(mysql, session['user_id'])
    accounts = {a.id: a for a in Account.get_all_by_user(mysql, session['user_id'])}
    return jsonify({'success': True, 'templates': [
        _rt_to_dict(t, currency=accounts[t.account_id].currency if t.account_id in accounts else 'RON')
        for t in templates
    ]}), 200


@api_recurring_bp.route('/<int:rt_id>', methods=['GET'])
@api_login_required
def get_recurring(rt_id):
    mysql = get_mysql()
    rt = RecurringTransaction.get_by_id(mysql, rt_id, session['user_id'])
    if rt:
        currency = 'RON'
        if rt.account_id:
            account = Account.get_by_id(mysql, rt.account_id, session['user_id'])
            currency = account.currency if account else 'RON'
        return jsonify({'success': True, 'recurring': _rt_to_dict(rt, currency=currency)}), 200
    return jsonify({'success': False, 'message': 'Recurring transaction not found'}), 404


@api_recurring_bp.route('/create', methods=['POST'])
@api_login_required
def create_recurring():
    try:
        data = request.get_json() if request.is_json else request.form
        mysql = get_mysql()
        user_id = session['user_id']

        account_id = _validate_account_id(mysql, data.get('account_id'), user_id)
        category_id = _validate_category_id(mysql, data.get('category_id'), user_id)
        loan_id = _validate_loan_id(mysql, data.get('loan_id'), user_id)
        type = data.get('type')
        amount = _validate_amount(data.get('amount'))
        description = (data.get('description') or '').strip()
        frequency = data.get('frequency')
        start_date = data.get('start_date')
        end_date = data.get('end_date') or None
        is_template = str(data.get('is_template', False)).lower() in ('true', '1', 'yes')

        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if category_id is False:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        if loan_id is False:
            return jsonify({'success': False, 'message': 'Invalid loan'}), 400
        if type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'type must be income or expense'}), 400
        if amount is None:
            return jsonify({'success': False, 'message': 'amount must be a positive number'}), 400
        if frequency not in ('daily', 'weekly', 'monthly', 'yearly'):
            return jsonify({'success': False, 'message': 'Invalid frequency'}), 400
        if not is_template and not start_date:
            return jsonify({'success': False, 'message': 'start_date is required'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        success, message, rt_id = RecurringTransaction.create(
            mysql, user_id, account_id, category_id, type, amount, description,
            frequency, start_date or None, end_date, is_template=is_template, loan_id=loan_id
        )
        if success:
            return jsonify({'success': True, 'message': message, 'id': rt_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_recurring_bp.route('/from-template/<int:template_id>', methods=['POST'])
@api_login_required
def create_from_template(template_id):
    try:
        data = request.get_json() if request.is_json else request.form
        mysql = get_mysql()
        user_id = session['user_id']

        template = RecurringTransaction.get_by_id(mysql, template_id, user_id)
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404

        from datetime import date as _date
        start_date = data.get('start_date') or str(_date.today())
        end_date = data.get('end_date') or None

        success, message, rt_id = RecurringTransaction.create(
            mysql, user_id, template.account_id, template.category_id, template.type,
            template.amount, template.description, template.frequency,
            start_date, end_date, is_template=False, loan_id=template.loan_id
        )
        if success:
            return jsonify({'success': True, 'message': 'Recurring transaction created from template', 'id': rt_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_recurring_bp.route('/<int:rt_id>/update', methods=['POST', 'PUT'])
@api_login_required
def update_recurring(rt_id):
    try:
        data = request.get_json() if request.is_json else request.form
        mysql = get_mysql()
        user_id = session['user_id']

        account_id = _validate_account_id(mysql, data.get('account_id'), user_id)
        category_id = _validate_category_id(mysql, data.get('category_id'), user_id)
        loan_id = _validate_loan_id(mysql, data.get('loan_id'), user_id)
        type = data.get('type')
        amount = _validate_amount(data.get('amount'))
        frequency = data.get('frequency')
        description = (data.get('description') or '').strip()

        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if category_id is False:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        if loan_id is False:
            return jsonify({'success': False, 'message': 'Invalid loan'}), 400
        if type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'type must be income or expense'}), 400
        if amount is None:
            return jsonify({'success': False, 'message': 'amount must be a positive number'}), 400
        if frequency not in ('daily', 'weekly', 'monthly', 'yearly'):
            return jsonify({'success': False, 'message': 'Invalid frequency'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        success, message = RecurringTransaction.update(
            mysql, rt_id, user_id, account_id, category_id, type, amount,
            description, frequency,
            data.get('start_date'), data.get('end_date') or None, loan_id=loan_id
        )
        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_recurring_bp.route('/<int:rt_id>/toggle', methods=['POST'])
@api_login_required
def toggle_recurring(rt_id):
    data = request.get_json() if request.is_json else request.form
    is_active = str(data.get('is_active', True)).lower() in ('true', '1')
    mysql = get_mysql()
    success = RecurringTransaction.set_active(mysql, rt_id, session['user_id'], is_active)
    if success:
        status = "activated" if is_active else "paused"
        return jsonify({'success': True, 'message': f'Recurring transaction {status}'}), 200
    return jsonify({'success': False, 'message': 'Recurring transaction not found or not yours'}), 403


@api_recurring_bp.route('/<int:rt_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_recurring(rt_id):
    mysql = get_mysql()
    success, message = RecurringTransaction.delete(mysql, rt_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 403 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


@api_recurring_bp.route('/trigger', methods=['POST'])
@api_login_required
def trigger_generation():
    """
    Manually trigger recurring transaction generation for ALL users' due items
    (same system-wide job the hourly scheduler runs). Requires login — the
    vulnerable version leaves this endpoint completely open to anyone.
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
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


def _rt_to_dict(r, currency='RON'):
    return {
        'id': r.id,
        'account_id': r.account_id,
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
        'loan_id': r.loan_id,
    }
