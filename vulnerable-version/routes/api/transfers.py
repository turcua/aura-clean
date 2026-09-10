"""
Aura Financial Tracker - Vulnerable Version
Transfers API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
"""

from flask import Blueprint, request, jsonify, session
from models.transfer import Transfer
from utils import flag_engine

api_transfers_bp = Blueprint('api_transfers', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


@api_transfers_bp.route('/list', methods=['GET'])
def list_transfers():
    """VULNERABILITIES: No auth, IDOR, SQL Injection"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400

        mysql = get_mysql()
        transfers = Transfer.get_all_by_user(mysql, user_id)

        # Sprint 44 (VULN-039 flag): listing someone else's transfers via
        # the user_id param is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-039')

        return jsonify({'success': True, 'transfers': [_transfer_to_dict(t) for t in transfers]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_transfers_bp.route('/create', methods=['POST'])
def create_transfer():
    """
    VULNERABILITIES:
    - No auth, No CSRF, SQL Injection, Mass assignment
    - No check that from/to accounts belong to user
    - No check that from_account has sufficient balance
    - No check that from_account != to_account
    """
    try:
        data = request.get_json() if request.is_json else request.form

        user_id = data.get('user_id')
        from_account_id = data.get('from_account_id')
        to_account_id = data.get('to_account_id')
        amount = data.get('amount')
        description = data.get('description', 'Transfer')
        transfer_date = data.get('transfer_date')

        mysql = get_mysql()
        success, message, transfer_id = Transfer.create(
            mysql, user_id, from_account_id, to_account_id, amount, description, transfer_date
        )

        if success:
            # Sprint 44 (VULN-036 flag): a literal quote in the description
            # that the insert still accepted is real injected SQL syntax —
            # a legitimate description essentially never contains one.
            if description and "'" in str(description):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-036')
            return jsonify({'success': True, 'message': message, 'transfer_id': transfer_id}), 201
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_transfers_bp.route('/<int:transfer_id>/delete', methods=['POST', 'DELETE'])
def delete_transfer(transfer_id):
    """VULNERABILITIES: No auth, IDOR, SQL Injection, No CSRF"""
    try:
        mysql = get_mysql()
        success, message = Transfer.delete(mysql, transfer_id)

        if success:
            return jsonify({'success': True, 'message': message}), 200
        return jsonify({'success': False, 'message': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _transfer_to_dict(t):
    return {
        'id': t.id,
        'user_id': t.user_id,  # VULN: Exposed
        'from_account_id': t.from_account_id,
        'to_account_id': t.to_account_id,
        'from_transaction_id': t.from_transaction_id,
        'to_transaction_id': t.to_transaction_id,
        'amount': t.amount,
        'description': t.description,
        'transfer_date': str(t.transfer_date) if t.transfer_date else None
    }
