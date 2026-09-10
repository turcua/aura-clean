"""
Aura Financial Tracker - Secure Version
Transaction API Routes
Sprint 11: Core Financial Tracking

Security properties (contrast with vulnerable-version/routes/api/transactions.py):
- Every route requires @api_login_required
- user_id always comes from session, never from the request body/params
- Ownership enforced at the model layer (id = %s AND user_id = %s)
- category_id (if provided) is validated as visible to the session user
  before being attached to a transaction — prevents filing a transaction
  under another user's private category
- amount is validated as a non-negative number server-side
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.transaction import Transaction
from models.category import Category
from models.account import Account
from models.loan import Loan
from routes.main import api_login_required

api_transactions_bp = Blueprint('api_transactions', __name__)


def get_mysql():
    return current_app.extensions['mysql']


def _validate_amount(raw):
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        return None
    if amount < 0:
        return None
    return round(amount, 2)


def _validate_category(mysql, category_id, user_id):
    """Returns category_id if it's None or visible to this user, else False."""
    if category_id in (None, '', 'null'):
        return None
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False
    category = Category.get_by_id(mysql, category_id, user_id)
    return category_id if category else False


def _validate_account(mysql, account_id, user_id):
    """Returns account_id if it's None or owned by this user, else False (Sprint 12)."""
    if account_id in (None, '', 'null'):
        return None
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return False
    account = Account.get_by_id(mysql, account_id, user_id)
    return account_id if account else False


def _validate_loan(mysql, loan_id, user_id):
    """Returns loan_id if it's None or owned by this user, else False (Sprint 28)."""
    if loan_id in (None, '', 'null'):
        return None
    try:
        loan_id = int(loan_id)
    except (TypeError, ValueError):
        return False
    loan = Loan.get_by_id(mysql, loan_id, user_id)
    return loan_id if loan else False


@api_transactions_bp.route('/create', methods=['POST'])
@api_login_required
def create_transaction():
    """Create a transaction owned by the session user."""
    try:
        data = request.get_json() if request.is_json else request.form
        type = data.get('type')
        amount = _validate_amount(data.get('amount'))
        description = (data.get('description') or '').strip()
        transaction_date = data.get('transaction_date')
        mysql = get_mysql()
        category_id = _validate_category(mysql, data.get('category_id'), session['user_id'])
        account_id = _validate_account(mysql, data.get('account_id'), session['user_id'])
        loan_id = _validate_loan(mysql, data.get('loan_id'), session['user_id'])

        if type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'type must be income or expense'}), 400
        if amount is None:
            return jsonify({'success': False, 'message': 'amount must be a non-negative number'}), 400
        if not transaction_date:
            return jsonify({'success': False, 'message': 'transaction_date is required'}), 400
        if category_id is False:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if loan_id is False:
            return jsonify({'success': False, 'message': 'Invalid loan'}), 400
        if len(description) > 255:
            return jsonify({'success': False, 'message': 'description is too long (max 255 characters)'}), 400

        success, message, transaction_id = Transaction.create(
            mysql, session['user_id'], category_id, type, amount, description, transaction_date,
            account_id=account_id, loan_id=loan_id, payment_type=('extra' if loan_id else None)
        )

        if success:
            return jsonify({'success': True, 'message': message, 'transaction_id': transaction_id}), 201
        return jsonify({'success': False, 'message': message}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/<int:transaction_id>', methods=['GET'])
@api_login_required
def get_transaction(transaction_id):
    """Get a single transaction — visible only if owned by the session user."""
    try:
        mysql = get_mysql()
        transaction = Transaction.get_by_id(mysql, transaction_id, session['user_id'])
        if not transaction:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404

        category_name = None
        if transaction.category_id:
            category = Category.get_by_id(mysql, transaction.category_id, session['user_id'])
            category_name = category.name if category else None

        currency = 'RON'
        if transaction.account_id:
            account = Account.get_by_id(mysql, transaction.account_id, session['user_id'])
            currency = account.currency if account else 'RON'

        return jsonify({'success': True, 'transaction': _transaction_to_dict(transaction, category_name, currency=currency)}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/<int:transaction_id>/update', methods=['PUT', 'POST'])
@api_login_required
def update_transaction(transaction_id):
    """Update — model layer enforces id = %s AND user_id = %s ownership."""
    try:
        data = request.get_json() if request.is_json else request.form
        type = data.get('type')
        amount = _validate_amount(data.get('amount'))
        description = (data.get('description') or '').strip()
        transaction_date = data.get('transaction_date')
        mysql = get_mysql()
        category_id = _validate_category(mysql, data.get('category_id'), session['user_id'])
        account_id = _validate_account(mysql, data.get('account_id'), session['user_id'])
        loan_id = _validate_loan(mysql, data.get('loan_id'), session['user_id'])

        if type not in ('income', 'expense'):
            return jsonify({'success': False, 'message': 'type must be income or expense'}), 400
        if amount is None:
            return jsonify({'success': False, 'message': 'amount must be a non-negative number'}), 400
        if not transaction_date:
            return jsonify({'success': False, 'message': 'transaction_date is required'}), 400
        if category_id is False:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400
        if account_id is False:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400
        if loan_id is False:
            return jsonify({'success': False, 'message': 'Invalid loan'}), 400

        success, message = Transaction.update(
            mysql, transaction_id, session['user_id'], category_id, type, amount, description, transaction_date,
            account_id=account_id, loan_id=loan_id, payment_type=('extra' if loan_id else None)
        )

        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/<int:transaction_id>/delete', methods=['DELETE', 'POST'])
@api_login_required
def delete_transaction(transaction_id):
    """Delete — model layer enforces id = %s AND user_id = %s ownership."""
    try:
        mysql = get_mysql()
        success, message = Transaction.delete(mysql, transaction_id, session['user_id'])

        if success:
            return jsonify({'success': True, 'message': message}), 200
        status = 403 if 'permission' in message else 400
        return jsonify({'success': False, 'message': message}), status
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/list', methods=['GET'])
@api_login_required
def list_transactions():
    """
    List the session user's transactions, with optional filters and (Sprint
    21) pagination. Pagination only engages if the caller explicitly sends
    ?page= or ?per_page= — existing callers that only send ?limit= (e.g. the
    dashboard's recent_transactions widget) keep their original, unpaginated
    behavior untouched.
    """
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        category_id_raw = request.args.get('category_id')
        account_id_raw = request.args.get('account_id')
        loan_id_raw = request.args.get('loan_id')
        type = request.args.get('type')
        limit = request.args.get('limit')
        page_raw = request.args.get('page')
        per_page_raw = request.args.get('per_page')
        # ENH-06/Sprint 50: transfers excluded by default, matching every
        # aggregate total (BUG-18) — pass ?include_transfers=1 to see them.
        include_transfers = request.args.get('include_transfers') in ('1', 'true', 'True')

        category_id = None
        if category_id_raw:
            ids = [int(x) for x in category_id_raw.split(',') if x.strip().isdigit()]
            category_id = ids or None

        account_id = None
        if account_id_raw:
            ids = [int(x) for x in account_id_raw.split(',') if x.strip().isdigit()]
            account_id = ids or None

        loan_id = int(loan_id_raw) if loan_id_raw and loan_id_raw.isdigit() else None

        mysql = get_mysql()
        has_filters = bool(date_from or date_to or category_id or account_id or loan_id or type)
        paginated = page_raw is not None or per_page_raw is not None
        pagination_meta = None

        if paginated:
            try:
                page = max(int(page_raw), 1) if page_raw else 1
            except (TypeError, ValueError):
                page = 1
            try:
                per_page = min(max(int(per_page_raw), 1), 100) if per_page_raw else 25
            except (TypeError, ValueError):
                per_page = 25
            offset = (page - 1) * per_page

            if has_filters:
                transactions = Transaction.filter_transactions(
                    mysql, session['user_id'], date_from, date_to, category_id, type, account_id,
                    loan_id=loan_id, limit=per_page, offset=offset, include_transfers=include_transfers
                )
                total = Transaction.count_filtered(
                    mysql, session['user_id'], date_from, date_to, category_id, type, account_id,
                    loan_id=loan_id, include_transfers=include_transfers
                )
            else:
                transactions = Transaction.get_all_by_user(
                    mysql, session['user_id'], limit=per_page, offset=offset, include_transfers=include_transfers
                )
                total = Transaction.count_by_user(mysql, session['user_id'], include_transfers=include_transfers)

            total_pages = max((total + per_page - 1) // per_page, 1)
            pagination_meta = {'page': page, 'per_page': per_page, 'total': total, 'total_pages': total_pages}
        elif has_filters:
            transactions = Transaction.filter_transactions(
                mysql, session['user_id'], date_from, date_to, category_id, type, account_id,
                loan_id=loan_id, include_transfers=include_transfers
            )
        else:
            transactions = Transaction.get_all_by_user(mysql, session['user_id'], limit, include_transfers=include_transfers)

        # Batch-load categories/accounts once instead of one query per row
        categories = {c.id: c for c in Category.get_all_by_user(mysql, session['user_id'])}
        accounts = {a.id: a for a in Account.get_all_by_user(mysql, session['user_id'])}

        transaction_list = []
        for t in transactions:
            category = categories.get(t.category_id)
            account = accounts.get(t.account_id)
            transaction_list.append(_transaction_to_dict(
                t, category.name if category else None, category.color if category else None,
                currency=account.currency if account else 'RON'
            ))

        response = {'success': True, 'count': len(transaction_list), 'transactions': transaction_list}
        if pagination_meta:
            response.update(pagination_meta)
        return jsonify(response), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/summary', methods=['GET'])
@api_login_required
def get_summary():
    """Financial summary (total income, expenses, balance) for the session user."""
    try:
        mysql = get_mysql()
        summary = Transaction.get_summary(mysql, session['user_id'])
        return jsonify({'success': True, 'summary': summary}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/monthly-summary', methods=['GET'])
@api_login_required
def get_monthly_summary():
    """Monthly income/expense totals for the bar chart."""
    try:
        months = request.args.get('months', 6)
        try:
            months = max(1, min(int(months), 24))
        except (TypeError, ValueError):
            months = 6
        mysql = get_mysql()
        data = Transaction.get_monthly_summary(mysql, session['user_id'], months)
        return jsonify({'success': True, 'data': data}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


@api_transactions_bp.route('/category-breakdown', methods=['GET'])
@api_login_required
def get_category_breakdown():
    """Expense-by-category totals for the donut chart."""
    try:
        mysql = get_mysql()
        data = Transaction.get_category_breakdown(mysql, session['user_id'])
        return jsonify({'success': True, 'data': data}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


def _transaction_to_dict(t, category_name=None, category_color=None, currency='RON'):
    return {
        'id': t.id,
        'category_id': t.category_id,
        'category_name': category_name,
        'category_color': category_color,
        'account_id': t.account_id,
        'loan_id': t.loan_id,
        'type': t.type,
        'amount': t.amount,
        'description': t.description,
        'transaction_date': str(t.transaction_date) if t.transaction_date else None,
        'currency': currency,
        'is_transfer': t.is_transfer,
    }
