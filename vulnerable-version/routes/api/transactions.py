"""
Aura Financial Tracker - Vulnerable Version
Transaction API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 2: Thunder Breathing - Second Form

API Endpoints for AJAX operations - Returns JSON responses
"""

from flask import Blueprint, request, jsonify, session
from models.transaction import Transaction
from models.category import Category
from models.account import Account
from utils import flag_engine

# Create API blueprint
api_transactions_bp = Blueprint('api_transactions', __name__)

def get_mysql():
    """Get MySQL instance from current app"""
    from flask import current_app
    return current_app.extensions['mysql']

# ============================================================================
# CREATE TRANSACTION
# ============================================================================
@api_transactions_bp.route('/create', methods=['POST'])
def create_transaction():
    """
    Create a new transaction (AJAX endpoint)
    
    VULNERABILITIES:
    - No authentication check (anyone can create transactions)
    - SQL Injection in all fields
    - XSS in description field
    - Mass assignment (user_id can be manipulated)
    - No CSRF protection
    - No input validation
    """
    try:
        # VULN: No authentication check
        # VULN: No CSRF token validation
        
        # Get data from request (JSON or form data)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        user_id = data.get('user_id')
        category_id = data.get('category_id')
        account_id = data.get('account_id')
        loan_id = data.get('loan_id')  # Sprint 28 — no ownership check, same as everything else here
        type = data.get('type')
        amount = data.get('amount')
        description = data.get('description', '')
        transaction_date = data.get('transaction_date')

        # VULN: No input validation (accepts any values)
        # VULN: No ownership check (user_id from request, not session)

        mysql = get_mysql()
        success, message, transaction_id = Transaction.create(
            mysql, user_id, category_id, type, amount, description, transaction_date,
            account_id=account_id, loan_id=loan_id, payment_type=('extra' if loan_id else None)
        )
        
        if success:
            # Sprint 43 (VULN-022 flag): the write succeeding under a
            # user_id that isn't the caller's own logged-in session is the
            # proof — credited to whoever actually sent the request.
            attacker_id = session.get('user_id')
            if attacker_id and str(user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-022')

            # Sprint 43 (VULN-024 flag): a genuine cross-site CSRF request
            # (an auto-submitting form on an attacker's own page) arrives
            # as form data with an Origin/Referer pointing at a different
            # host than this app — and this endpoint has no CSRF token to
            # stop it. A normal same-origin AJAX call never has a foreign
            # Origin, so this specifically catches the CSRF case.
            origin = request.headers.get('Origin') or request.headers.get('Referer') or ''
            if not request.is_json and origin and request.host not in origin:
                victim_id = session.get('user_id')
                if victim_id:
                    flag_engine.mark_solved_with_flag(mysql, victim_id, 'VULN-024')

            # Sprint 44 (VULN-015 flag): amount/category_id are expected to
            # be pure numeric — a non-numeric value the insert still
            # accepted is real injected SQL syntax, not coincidental valid
            # input (same signal already proven on VULN-072/006).
            amount_str = str(amount) if amount is not None else ''
            if (amount_str and not amount_str.replace('.', '', 1).isdigit()) or \
               (category_id and not str(category_id).isdigit()):
                sqli_attacker_id = session.get('user_id')
                if sqli_attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, sqli_attacker_id, 'VULN-015')

            return jsonify({
                'success': True,
                'message': message,
                'transaction_id': transaction_id
            }), 201
        else:
            # VULN: Detailed error messages leak database info
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        # VULN: Stack trace in response
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# GET SINGLE TRANSACTION
# ============================================================================
@api_transactions_bp.route('/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """
    Get a single transaction by ID
    
    VULNERABILITIES:
    - No authentication check
    - IDOR - Can access any transaction regardless of ownership
    - SQL Injection in transaction_id (via model)
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification
        
        mysql = get_mysql()
        transaction = Transaction.get_by_id(mysql, transaction_id)

        if transaction:
            # Sprint 44 (VULN-018 flag): genuinely reading someone else's
            # transaction via the IDOR is the proof.
            attacker_id = session.get('user_id')
            if attacker_id and str(transaction.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-018')

            # Get category name if exists
            category_name = None
            if transaction.category_id:
                category = Category.get_by_id(mysql, transaction.category_id)
                if category:
                    category_name = category.name

            currency = 'RON'
            if transaction.account_id:
                account = Account.get_by_id(mysql, transaction.account_id)
                if account:
                    currency = account.currency

            return jsonify({
                'success': True,
                'transaction': {
                    'id': transaction.id,
                    'user_id': transaction.user_id,  # VULN: Exposing user_id
                    'category_id': transaction.category_id,
                    'category_name': category_name,
                    'account_id': transaction.account_id,
                    'loan_id': transaction.loan_id,
                    'type': transaction.type,
                    'amount': float(transaction.amount),
                    'description': transaction.description,
                    'transaction_date': str(transaction.transaction_date),
                    'currency': currency
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# UPDATE TRANSACTION
# ============================================================================
@api_transactions_bp.route('/<int:transaction_id>/update', methods=['PUT', 'POST'])
def update_transaction(transaction_id):
    """
    Update a transaction
    
    VULNERABILITIES:
    - No authentication check
    - IDOR - Can update any transaction
    - SQL Injection in all fields
    - Mass assignment (can change user_id)
    - No CSRF protection
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification
        
        # Get data from request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        user_id = data.get('user_id')
        category_id = data.get('category_id')
        account_id = data.get('account_id')
        loan_id = data.get('loan_id')  # Sprint 30 — no ownership check, same as everything else here
        type = data.get('type')
        amount = data.get('amount')
        description = data.get('description', '')
        transaction_date = data.get('transaction_date')

        # VULN: No input validation
        # VULN: Can update user_id (mass assignment)

        mysql = get_mysql()
        old_tx = Transaction.get_by_id(mysql, transaction_id)
        success, message = Transaction.update(
            mysql, transaction_id, user_id, category_id, type, amount, description, transaction_date,
            account_id=account_id, loan_id=loan_id, payment_type=('extra' if loan_id else None)
        )

        if success:
            # Sprint 44 (VULN-081 flag, weak fit like other business-logic
            # findings — doesn't leak data, so this is a weaker signal):
            # updating the amount on an account-linked transaction is the
            # exact scenario the bug describes — this endpoint never calls
            # Account.update_balance(), so the account's real balance
            # silently drifts from what it should be.
            if old_tx and old_tx.account_id and amount is not None and str(amount) != str(old_tx.amount):
                attacker_id = session.get('user_id')
                if attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-081')

            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# DELETE TRANSACTION
# ============================================================================
@api_transactions_bp.route('/<int:transaction_id>/delete', methods=['DELETE', 'POST'])
def delete_transaction(transaction_id):
    """
    Delete a transaction

    VULNERABILITIES:
    - No authentication check
    - IDOR - Can delete any transaction
    - SQL Injection in transaction_id
    - No CSRF protection
    """
    try:
        # VULN: No authentication check
        # VULN: No ownership verification

        mysql = get_mysql()
        old_tx = Transaction.get_by_id(mysql, transaction_id)
        success, message = Transaction.delete(mysql, transaction_id)

        if success:
            # Sprint 44 (VULN-081 flag): deleting an account-linked
            # transaction is the other half of the same reconciliation gap.
            if old_tx and old_tx.account_id:
                attacker_id = session.get('user_id')
                if attacker_id:
                    flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-081')

            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# LIST TRANSACTIONS (WITH FILTERS)
# ============================================================================
@api_transactions_bp.route('/list', methods=['GET'])
def list_transactions():
    """
    List transactions for a user with optional filters and (Sprint 21) pagination

    VULNERABILITIES:
    - SQL Injection in all filter parameters (including page/per_page)
    - IDOR - Can list any user's transactions
    - Reflected XSS in filter parameters
    - No pagination cap — per_page is never clamped, so ?per_page=999999999
      still fetches everything in one response (DoS with large datasets)
    """
    try:
        # Get filter parameters from query string
        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        category_id = request.args.get('category_id')
        account_id = request.args.get('account_id')  # Sprint 50/ENH-05 — no validation, same pattern as category_id
        loan_id = request.args.get('loan_id')  # Sprint 30 — no validation, same pattern as category_id
        type = request.args.get('type')
        limit = request.args.get('limit')
        page_raw = request.args.get('page')
        per_page_raw = request.args.get('per_page')
        # ENH-06/Sprint 50: transfers excluded by default, matching every
        # aggregate total (BUG-18) — pass ?include_transfers=1 to see them.
        include_transfers = request.args.get('include_transfers') in ('1', 'true', 'True')

        # VULN: No authentication check
        # VULN: No ownership verification (can access any user_id)

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id is required'
            }), 400

        mysql = get_mysql()
        has_filters = bool(date_from or date_to or category_id or account_id or loan_id or type)
        paginated = page_raw is not None or per_page_raw is not None
        pagination_meta = None

        if paginated:
            # VULN: page/per_page not validated or clamped — negative, zero,
            # or absurdly large values pass straight through to the model
            page = int(page_raw) if page_raw else 1
            per_page = int(per_page_raw) if per_page_raw else 25
            offset = (page - 1) * per_page

            if has_filters:
                transactions = Transaction.filter_transactions(
                    mysql, user_id, date_from, date_to, category_id, type,
                    loan_id=loan_id, limit=per_page, offset=offset, include_transfers=include_transfers,
                    account_id=account_id
                )
                total = Transaction.count_filtered(
                    mysql, user_id, date_from, date_to, category_id, type, loan_id=loan_id,
                    include_transfers=include_transfers, account_id=account_id
                )
            else:
                transactions = Transaction.get_all_by_user(
                    mysql, user_id, limit=per_page, offset=offset, include_transfers=include_transfers
                )
                total = Transaction.count_by_user(mysql, user_id, include_transfers=include_transfers)

            total_pages = max((total + per_page - 1) // per_page, 1) if per_page else 1
            pagination_meta = {'page': page, 'per_page': per_page, 'total': total, 'total_pages': total_pages}
        # Apply filters if provided
        elif has_filters:
            transactions = Transaction.filter_transactions(
                mysql, user_id, date_from, date_to, category_id, type, loan_id=loan_id,
                include_transfers=include_transfers, account_id=account_id
            )
        else:
            transactions = Transaction.get_all_by_user(mysql, user_id, limit, include_transfers=include_transfers)

        # Format response
        transaction_list = []
        for t in transactions:
            # Get category name if exists
            category_name = None
            category_color = None
            if t.category_id:
                category = Category.get_by_id(mysql, t.category_id)
                if category:
                    category_name = category.name
                    category_color = category.color

            currency = 'RON'
            if t.account_id:
                account = Account.get_by_id(mysql, t.account_id)
                if account:
                    currency = account.currency

            transaction_list.append({
                'id': t.id,
                'user_id': t.user_id,  # VULN: Exposing user_id
                'category_id': t.category_id,
                'category_name': category_name,
                'category_color': category_color,
                'account_id': t.account_id,
                'loan_id': t.loan_id,
                'type': t.type,
                'amount': float(t.amount),
                'description': t.description,  # VULN: XSS if not escaped in frontend
                'transaction_date': str(t.transaction_date),
                'currency': currency,
                'is_transfer': t.is_transfer,
            })

        # Sprint 44 (VULN-017 flag): a non-numeric category_id that the
        # filter query still executed successfully with is real injected
        # SQL syntax, not coincidental valid input (same signal as VULN-072).
        if category_id and not str(category_id).isdigit():
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-017')

        response = {
            'success': True,
            'count': len(transaction_list),
            'transactions': transaction_list
        }
        if pagination_meta:
            response.update(pagination_meta)
        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# GET SUMMARY (DASHBOARD DATA)
# ============================================================================
@api_transactions_bp.route('/summary', methods=['GET'])
def get_summary():
    """
    Get financial summary for a user (total income, expenses, balance)
    
    VULNERABILITIES:
    - SQL Injection in user_id
    - IDOR - Can view any user's summary
    - Information disclosure
    """
    try:
        user_id = request.args.get('user_id')
        
        # VULN: No authentication check
        # VULN: No ownership verification
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id is required'
            }), 400
        
        mysql = get_mysql()
        summary = Transaction.get_summary(mysql, user_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500
