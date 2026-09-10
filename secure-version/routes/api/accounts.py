"""
Aura Financial Tracker - Secure Version
Accounts API Routes
Sprint 12: Accounts + Recurring Transactions

Security properties: every route requires @api_login_required; user_id always
from session; ownership enforced at the model layer (id = %s AND user_id = %s).
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.account import Account
from models.currency import Currency
from routes.main import api_login_required

api_accounts_bp = Blueprint('api_accounts', __name__)

VALID_TYPES = ('checking', 'savings', 'credit_card', 'investment', 'cash')


def get_mysql():
    return current_app.extensions['mysql']


def _validate_balance(raw):
    try:
        return round(float(raw), 2)
    except (TypeError, ValueError):
        return None


def _parse_interest_fields(data, account_type):
    """
    Sprint 57 (ENH-11). Returns (interest_rate_annual, interest_accrual_frequency, error_message).
    Interest is savings-only by scope — a non-savings type forces both to
    NULL regardless of what the request sent, rather than erroring, so
    switching an account's type away from 'savings' cleanly drops any
    interest config instead of leaving it stranded and unreachable through
    the UI.
    """
    if account_type != 'savings':
        return None, None, None

    raw_rate = data.get('interest_rate_annual')
    if raw_rate in (None, ''):
        return None, None, None

    try:
        rate = round(float(raw_rate), 3)
    except (TypeError, ValueError):
        return None, None, 'interest_rate_annual must be a number'
    if rate < 0 or rate > 100:
        return None, None, 'interest_rate_annual must be between 0 and 100'

    frequency = data.get('interest_accrual_frequency')
    if frequency not in ('daily', 'monthly'):
        return None, None, 'interest_accrual_frequency must be "daily" or "monthly" when a rate is set'

    return rate, frequency, None


@api_accounts_bp.route('/list', methods=['GET'])
@api_login_required
def list_accounts():
    mysql = get_mysql()
    accounts = Account.get_all_by_user(mysql, session['user_id'])
    return jsonify({'success': True, 'accounts': [_account_to_dict(a) for a in accounts]}), 200


@api_accounts_bp.route('/<int:account_id>', methods=['GET'])
@api_login_required
def get_account(account_id):
    mysql = get_mysql()
    account = Account.get_by_id(mysql, account_id, session['user_id'])
    if account:
        return jsonify({'success': True, 'account': _account_to_dict(account)}), 200
    return jsonify({'success': False, 'message': 'Account not found'}), 404


@api_accounts_bp.route('/create', methods=['POST'])
@api_login_required
def create_account():
    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        type = data.get('type', 'checking')
        initial_balance = _validate_balance(data.get('initial_balance', 0))
        description = (data.get('description') or '').strip()
        include_in_budget = str(data.get('include_in_budget', True)).lower() in ('true', '1', 'on')
        currency = data.get('currency', 'RON')

        if not name or len(name) > 100:
            return jsonify({'success': False, 'message': 'name is required (max 100 characters)'}), 400
        if type not in VALID_TYPES:
            return jsonify({'success': False, 'message': 'Invalid account type'}), 400
        if initial_balance is None:
            return jsonify({'success': False, 'message': 'initial_balance must be a number'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        mysql = get_mysql()
        if currency not in {c.code for c in Currency.get_all(mysql)}:
            return jsonify({'success': False, 'message': 'Invalid currency'}), 400

        interest_rate, interest_frequency, interest_error = _parse_interest_fields(data, type)
        if interest_error:
            return jsonify({'success': False, 'message': interest_error}), 400

        success, message, account_id = Account.create(
            mysql, session['user_id'], name, type, initial_balance, description, include_in_budget, currency,
            interest_rate, interest_frequency
        )
        if success:
            return jsonify({'success': True, 'message': message, 'account_id': account_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_accounts_bp.route('/<int:account_id>/update', methods=['POST', 'PUT'])
@api_login_required
def update_account(account_id):
    try:
        data = request.get_json() if request.is_json else request.form
        name = (data.get('name') or '').strip()
        type = data.get('type', 'checking')
        include_in_budget = str(data.get('include_in_budget', True)).lower() in ('true', '1', 'on')
        description = (data.get('description') or '').strip()
        currency = data.get('currency', 'RON')

        if not name or len(name) > 100:
            return jsonify({'success': False, 'message': 'name is required (max 100 characters)'}), 400
        if type not in VALID_TYPES:
            return jsonify({'success': False, 'message': 'Invalid account type'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        mysql = get_mysql()
        if currency not in {c.code for c in Currency.get_all(mysql)}:
            return jsonify({'success': False, 'message': 'Invalid currency'}), 400

        interest_rate, interest_frequency, interest_error = _parse_interest_fields(data, type)
        if interest_error:
            return jsonify({'success': False, 'message': interest_error}), 400

        success, message = Account.update(
            mysql, account_id, session['user_id'], name, type, include_in_budget, description, currency,
            interest_rate, interest_frequency
        )
        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_accounts_bp.route('/<int:account_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_account(account_id):
    mysql = get_mysql()
    success, message = Account.delete(mysql, account_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 403 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


@api_accounts_bp.route('/reorder', methods=['POST'])
@api_login_required
def reorder_accounts():
    """Sprint 53 (UI-01). Ownership check happens inside Account.reorder()
    before any write, so a payload naming someone else's account id is
    rejected wholesale rather than partially applied."""
    try:
        data = request.get_json() if request.is_json else request.form
        order = data.get('order', [])
        order = [int(x) for x in order]
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'order must be a list of account ids'}), 400

    mysql = get_mysql()
    success, message = Account.reorder(mysql, session['user_id'], order)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


@api_accounts_bp.route('/summary', methods=['GET'])
@api_login_required
def get_summary():
    mysql = get_mysql()
    net_worth = Account.get_net_worth(mysql, session['user_id'])
    budget_balance = Account.get_budget_balance(mysql, session['user_id'])
    return jsonify({'success': True, 'net_worth': net_worth, 'budget_balance': budget_balance}), 200


def _account_to_dict(a):
    return {
        'id': a.id,
        'name': a.name,
        'type': a.type,
        'initial_balance': a.initial_balance,
        'current_balance': a.current_balance,
        'include_in_budget': a.include_in_budget,
        'description': a.description,
        'is_active': a.is_active,
        'currency': a.currency,
        'interest_rate_annual': a.interest_rate_annual,
        'interest_accrual_frequency': a.interest_accrual_frequency,
    }
