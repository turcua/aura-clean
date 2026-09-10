"""
Aura Financial Tracker - Vulnerable Version
Accounts API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 3 & 4: Shadow Extractor
"""

from flask import Blueprint, request, jsonify, session
from models.account import Account
from utils import flag_engine

api_accounts_bp = Blueprint('api_accounts', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_accounts_bp.route('/list', methods=['GET'])
def list_accounts():
    """
    VULNERABILITIES:
    - No authentication check
    - IDOR: returns any user's accounts via user_id param
    - SQL Injection via user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        accounts = Account.get_all_by_user(mysql, user_id)

        # Sprint 43 (VULN-034 flag, attempted — business-logic bugs don't
        # leak data, so this is a weaker signal than the other patterns):
        # credited when the caller's own account list actually contains
        # the mix (some budget-included, some not) that makes
        # get_budget_balance()'s silent exclusion meaningfully different
        # from a naive full sum — the scenario the bug applies to, not
        # proof anyone noticed the discrepancy.
        own_id = session.get('user_id')
        if own_id and str(own_id) == str(user_id):
            flags = {bool(a.include_in_budget) for a in accounts}
            if len(flags) > 1:
                flag_engine.mark_solved_with_flag(mysql, own_id, 'VULN-034')

        return jsonify({
            'success': True,
            'accounts': [_account_to_dict(a) for a in accounts]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/<int:account_id>', methods=['GET'])
def get_account(account_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        mysql = get_mysql()
        account = Account.get_by_id(mysql, account_id)
        if account:
            # Sprint 44 (VULN-030 flag): genuinely reading someone else's
            # account via the IDOR is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(account.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-030')
            return jsonify({'success': True, 'account': _account_to_dict(account)}), 200
        return jsonify({'success': False, 'message': 'Account not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/create', methods=['POST'])
def create_account():
    """
    VULNERABILITIES:
    - No authentication check
    - No CSRF protection
    - SQL Injection in all fields
    - Mass assignment (user_id from request payload)
    - No input validation
    """
    try:
        data = request.get_json() if request.is_json else request.form

        user_id = data.get('user_id')
        name = data.get('name', '')
        type = data.get('type', 'checking')
        initial_balance = data.get('initial_balance', 0)
        description = data.get('description', '')
        include_in_budget = data.get('include_in_budget', True)
        currency = data.get('currency', 'RON')
        # Sprint 57 (ENH-11): no server-side check that type is actually
        # 'savings', no bound on the rate value — same "no input
        # validation" convention as every other field here.
        interest_rate_annual = data.get('interest_rate_annual')
        interest_accrual_frequency = data.get('interest_accrual_frequency')

        mysql = get_mysql()
        success, message, account_id = Account.create(
            mysql, user_id, name, type, initial_balance, description, include_in_budget, currency,
            interest_rate_annual, interest_accrual_frequency
        )

        if success:
            # Sprint 44 (VULN-028 flag): a literal quote in the name field
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate account name essentially never contains one.
            if name and "'" in str(name):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-028')
            return jsonify({'success': True, 'message': message, 'account_id': account_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/<int:account_id>/update', methods=['POST', 'PUT'])
def update_account(account_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, Mass assignment, No CSRF"""
    try:
        data = request.get_json() if request.is_json else request.form

        user_id = data.get('user_id')
        name = data.get('name', '')
        type = data.get('type', 'checking')
        include_in_budget = data.get('include_in_budget', True)
        description = data.get('description', '')
        currency = data.get('currency', 'RON')
        interest_rate_annual = data.get('interest_rate_annual')
        interest_accrual_frequency = data.get('interest_accrual_frequency')

        mysql = get_mysql()
        success, message = Account.update(
            mysql, account_id, user_id, name, type, include_in_budget, description, currency,
            interest_rate_annual, interest_accrual_frequency
        )

        if success:
            # Sprint 44 (VULN-032 flag): the write succeeding under a
            # user_id that isn't the caller's own logged-in session is the
            # proof — same pattern already proven on VULN-022.
            attacker_id = session.get('user_id')
            if attacker_id and str(user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-032')
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/<int:account_id>/delete', methods=['POST', 'DELETE'])
def delete_account(account_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF, BUG-004"""
    try:
        mysql = get_mysql()

        # Sprint 44 (VULN-035 flag, weak fit like VULN-034 — business-logic
        # bugs don't leak data): checked BEFORE deleting whether this
        # account actually has transactions, so credit only fires when the
        # soft-delete genuinely orphans something, not on every delete.
        had_transactions = False
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_id = %s", (account_id,))
            row = cursor.fetchone()
            cursor.close()
            had_transactions = bool(row and row[0] > 0)
        except Exception:
            had_transactions = False

        success, message = Account.delete(mysql, account_id)

        if success and had_transactions:
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-035')

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/reorder', methods=['POST'])
def reorder_accounts():
    """
    VULNERABILITIES:
    - No authentication check
    - IDOR: no ownership check — any account id in the payload gets
      reordered regardless of who actually owns it
    - SQL Injection via account ids (see Account.reorder)
    """
    try:
        data = request.get_json() if request.is_json else request.form
        order = data.get('order', [])

        mysql = get_mysql()
        success, message = Account.reorder(mysql, order)

        if success:
            # Sprint 53 (VULN-085 flag): genuinely reordering an account
            # that belongs to someone other than the caller is the proof —
            # same pattern as VULN-030's cross-account GET.
            attacker_id = session.get('user_id')
            if attacker_id:
                for account_id in order:
                    account = Account.get_by_id(mysql, account_id)
                    if account and str(account.user_id) != str(attacker_id):
                        flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-085')
                        break
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_accounts_bp.route('/summary', methods=['GET'])
def get_summary():
    """
    Returns net worth and budget balance for a user.
    VULNERABILITIES: No auth, IDOR, SQL Injection
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        net_worth = Account.get_net_worth(mysql, user_id)
        budget_balance = Account.get_budget_balance(mysql, user_id)

        return jsonify({
            'success': True,
            'net_worth': net_worth,
            'budget_balance': budget_balance
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _account_to_dict(a):
    return {
        'id': a.id,
        'user_id': a.user_id,  # VULN: Exposing user_id
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
