"""
Aura Financial Tracker - Secure Version
Transfers API Routes
Sprint 13: Transfers + Budgets + Savings Goals

Security properties (contrast with vulnerable-version/routes/api/transfers.py):
- Every route requires @api_login_required
- user_id always from session
- Both accounts validated as owned by the session user before Transfer.create()
- from_account_id != to_account_id and amount > 0 validated server-side
  (also enforced at the schema level via CHECK constraints)
- Insufficient-balance check before allowing the transfer — the vulnerable
  version allows unlimited overdraft by design; this is a genuine business
  rule improvement, not just a security fix
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.transfer import Transfer
from models.account import Account
from routes.main import api_login_required

api_transfers_bp = Blueprint('api_transfers', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_transfers_bp.route('/list', methods=['GET'])
@api_login_required
def list_transfers():
    mysql = get_mysql()
    transfers = Transfer.get_all_by_user(mysql, session['user_id'])
    return jsonify({'success': True, 'transfers': [_transfer_to_dict(t) for t in transfers]}), 200


@api_transfers_bp.route('/create', methods=['POST'])
@api_login_required
def create_transfer():
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = session['user_id']

        try:
            from_account_id = int(data.get('from_account_id'))
            to_account_id = int(data.get('to_account_id'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Invalid account'}), 400

        try:
            amount = round(float(data.get('amount')), 2)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'amount must be a number'}), 400

        description = (data.get('description') or 'Transfer').strip()
        transfer_date = data.get('transfer_date')

        if from_account_id == to_account_id:
            return jsonify({'success': False, 'message': 'From and To accounts must be different'}), 400
        if amount <= 0:
            return jsonify({'success': False, 'message': 'amount must be positive'}), 400
        if not transfer_date:
            return jsonify({'success': False, 'message': 'transfer_date is required'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        mysql = get_mysql()
        from_account = Account.get_by_id(mysql, from_account_id, user_id)
        to_account = Account.get_by_id(mysql, to_account_id, user_id)
        if not from_account or not to_account:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if from_account.current_balance < amount:
            return jsonify({'success': False, 'message': 'Insufficient balance in the source account'}), 400

        success, message, transfer_id = Transfer.create(
            mysql, user_id, from_account_id, to_account_id, amount, description, transfer_date
        )
        if success:
            return jsonify({'success': True, 'message': message, 'transfer_id': transfer_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transfers_bp.route('/<int:transfer_id>/delete', methods=['POST', 'DELETE'])
@api_login_required
def delete_transfer(transfer_id):
    mysql = get_mysql()
    success, message = Transfer.delete(mysql, transfer_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': message}), 200
    status = 403 if 'permission' in message else 400
    return jsonify({'success': False, 'message': message}), status


def _transfer_to_dict(t):
    return {
        'id': t.id,
        'from_account_id': t.from_account_id,
        'to_account_id': t.to_account_id,
        'amount': t.amount,
        'description': t.description,
        'transfer_date': str(t.transfer_date) if t.transfer_date else None,
    }
