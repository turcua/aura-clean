"""
Aura Financial Tracker - Secure Version
AI Advisor API Routes
Sprint 23: AI Advisor Foundation

Security properties (contrast with vulnerable-version/routes/api/ai_advisor.py):
- Every route requires @api_login_required; user_id always comes from session
- Rate limited (30/hour) — a real Groq API cost control, not just a CTF
  concern; vulnerable-version has no rate limiting at all (VULN-011 pattern)
- Errors returned to the client are generic; nothing from Groq or from an
  internal exception is ever echoed back verbatim
"""

import json
from datetime import date

from flask import Blueprint, jsonify, request, session, current_app

from models.ai_conversation import AIConversation
from models.ai_pending_action import AIPendingAction
from models.transaction import Transaction
from models.budget import Budget
from models.transfer import Transfer
from models.category import Category
from models.account import Account
from models.loan import Loan
from routes.main import api_login_required
from extensions import limiter
from utils.groq_client import send_chat_completion
from utils.ai_context import build_system_prompt
from utils.ai_tools import TOOLS

api_ai_advisor_bp = Blueprint('api_ai_advisor', __name__)

MAX_HISTORY_MESSAGES = 20
DISPLAY_HISTORY_LIMIT = 100
ANOMALOUS_AMOUNT_MULTIPLIER = 3.0  # Sprint 26 follow-up: flag a proposed amount this many times the user's own average


def get_mysql():
    return current_app.extensions['mysql']


@api_ai_advisor_bp.route('/chat', methods=['POST'])
@api_login_required
@limiter.limit("30 per hour", methods=["POST"])
def chat():
    mysql = get_mysql()
    user_id = session['user_id']

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400

    AIConversation.add_message(mysql, user_id, 'user', message)

    system_prompt = build_system_prompt(mysql, user_id)
    since = session.get('ai_chat_since')
    history = AIConversation.get_recent(mysql, user_id, limit=MAX_HISTORY_MESSAGES, since=since)

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in history]

    success, content, tool_calls = send_chat_completion(
        current_app.config.get('GROQ_API_KEY'),
        current_app.config.get('GROQ_MODEL'),
        messages,
        tools=TOOLS,
    )

    if not success:
        return jsonify({'success': False, 'message': content}), 502

    # Security property (contrast with vulnerable-version/routes/api/ai_advisor.py):
    # a tool call is never executed here — it's stored as a pending action,
    # and only POST /confirm-action (with full server-side re-validation)
    # can turn it into a real write. The AI's output is a suggestion, never
    # an authorization.
    pending_actions = []
    if tool_calls:
        for tc in tool_calls:
            try:
                args = json.loads(tc['function']['arguments'])
            except (KeyError, ValueError):
                continue
            action_type = tc['function']['name']
            created, action_id = AIPendingAction.create(mysql, user_id, action_type, args)
            if created:
                pending_actions.append({
                    'id': action_id,
                    'action_type': action_type,
                    'description': _describe_action(action_type, args),
                    'warning': _check_anomalous_amount(mysql, user_id, action_type, args),
                })
        if not content:
            content = "I'd like to take the following action — please confirm below:" \
                if len(pending_actions) == 1 else \
                "I'd like to take the following actions — please confirm below:"

    AIConversation.add_message(mysql, user_id, 'assistant', content or '')

    return jsonify({
        'success': True,
        'message': content,
        'pending_actions': pending_actions,
    }), 200


@api_ai_advisor_bp.route('/confirm-action/<int:action_id>', methods=['POST'])
@api_login_required
def confirm_action(action_id):
    """
    Every parameter is independently re-validated here — never trusted from
    what the AI merely proposed. Ownership (category/account) is re-checked
    against the confirming user, not assumed from the pending row.
    """
    mysql = get_mysql()
    user_id = session['user_id']

    data = request.get_json(silent=True) or {}
    confirmed = bool(data.get('confirm'))

    action = AIPendingAction.get_by_id(mysql, action_id, user_id)
    if not action or action.status != 'pending':
        return jsonify({'success': False, 'message': 'Action not found or already resolved'}), 404

    if not confirmed:
        AIPendingAction.mark_resolved(mysql, action_id, user_id, 'cancelled')
        return jsonify({'success': True, 'message': 'Action cancelled'}), 200

    ok, message = _execute_validated_action(mysql, user_id, action.action_type, action.action_params)
    if ok:
        AIPendingAction.mark_resolved(mysql, action_id, user_id, 'confirmed')
        return jsonify({'success': True, 'message': message}), 200
    return jsonify({'success': False, 'message': message}), 400


def _describe_action(action_type, params):
    if action_type == 'create_transaction':
        extra = []
        if params.get('account_name'):
            extra.append(f"from {params['account_name']}")
        if params.get('category_name'):
            extra.append(f"category {params['category_name']}")
        if params.get('loan_name'):
            extra.append(f"extra payment toward {params['loan_name']}")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        return f"Create {params.get('type', 'transaction')}: {params.get('amount')} — {params.get('description')}{extra_str} ({params.get('transaction_date')})"
    if action_type == 'update_transaction':
        extra = []
        if params.get('type'):
            extra.append(f"type {params['type']}")
        if params.get('amount') is not None:
            extra.append(f"amount {params['amount']}")
        if params.get('description'):
            extra.append(f"description \"{params['description']}\"")
        if params.get('transaction_date'):
            extra.append(f"date {params['transaction_date']}")
        if params.get('category_name'):
            extra.append(f"category {params['category_name']}")
        if params.get('account_name'):
            extra.append(f"account {params['account_name']}")
        if params.get('loan_name'):
            extra.append(f"loan {params['loan_name']}")
        changes = ', '.join(extra) if extra else 'no changes specified'
        return f"Update transaction \"{params.get('match_description')}\" ({params.get('match_transaction_date')}): {changes}"
    if action_type == 'delete_transaction':
        extra = f" ({params.get('match_amount')})" if params.get('match_amount') is not None else ""
        return f"Delete transaction \"{params.get('match_description')}\" ({params.get('match_transaction_date')}){extra}"
    if action_type == 'create_budget':
        return f"Create budget \"{params.get('name')}\": limit {params.get('total_limit')} ({params.get('start_date')} to {params.get('end_date')})"
    if action_type == 'create_transfer':
        return f"Transfer {params.get('amount')} from {params.get('from_account_name')} to {params.get('to_account_name')} — {params.get('description') or 'Transfer'} ({params.get('transfer_date')})"
    return f"Unknown action: {action_type}"


def _check_anomalous_amount(mysql, user_id, action_type, params):
    """
    Sprint 26 follow-up: defense-in-depth on top of the confirmation gate
    itself, not a replacement for it — the gate can still be shown a
    plausible-looking proposal for an injected action (see
    docs/vulnerability-matrix.md's 2026-07-29 addendum). Flags a proposed
    amount that's unusually large relative to the user's own real history,
    giving the human-review step something concrete to notice rather than
    relying purely on reading every card carefully. Returns a warning
    string, or None if nothing looks unusual (or there's no history yet to
    compare against — a brand-new user isn't flagged just for lacking data).
    """
    try:
        amount = float(params.get('amount'))
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None

    if action_type in ('create_transaction', 'update_transaction'):
        avg = Transaction.get_average_amount(mysql, user_id, params.get('type'))
    elif action_type == 'create_transfer':
        avg = Transfer.get_average_amount(mysql, user_id)
    else:
        return None

    if avg is None or avg <= 0 or amount < avg * ANOMALOUS_AMOUNT_MULTIPLIER:
        return None

    return (
        f"This amount is about {round(amount / avg, 1)}x your usual "
        f"{'transfer' if action_type == 'create_transfer' else params.get('type')} "
        f"({round(avg, 2)} on average) — double-check this is really what you want."
    )


def _resolve_by_name(items, name):
    """Case-insensitive exact match on .name; None if no name given or no match.
    items is always fetched scoped to the confirming user_id, so a name that
    doesn't belong to them simply never resolves — ownership enforced by
    construction, not by trusting an id the AI (or the client) supplied."""
    if not name:
        return None
    for item in items:
        if item.name and item.name.strip().lower() == str(name).strip().lower():
            return item.id
    return None


def _execute_validated_action(mysql, user_id, action_type, params):
    """Real validation, independent of whatever the AI proposed — amount
    sanity, date sanity, and account/category resolved fresh from this
    user's own data, never trusted from a raw id in the proposal."""
    if action_type == 'create_transaction':
        tx_type = params.get('type')
        if tx_type not in ('income', 'expense'):
            return False, 'Invalid transaction type'
        try:
            amount = float(params.get('amount'))
        except (TypeError, ValueError):
            return False, 'Invalid amount'
        if amount <= 0:
            return False, 'Amount must be positive'
        try:
            transaction_date = date.fromisoformat(str(params.get('transaction_date')))
        except ValueError:
            return False, 'Invalid transaction date'

        category_id = _resolve_by_name(Category.get_all_by_user(mysql, user_id), params.get('category_name'))
        account_id = _resolve_by_name(Account.get_all_by_user(mysql, user_id), params.get('account_name'))
        loan_id = _resolve_by_name(Loan.get_all_by_user(mysql, user_id), params.get('loan_name'))

        success, message, tx_id = Transaction.create(
            mysql, user_id, category_id, tx_type, amount,
            str(params.get('description') or '')[:255], str(transaction_date), account_id,
            loan_id=loan_id,
        )
        return success, (f"Transaction created (id={tx_id})" if success else message)

    if action_type == 'update_transaction':
        match_date = params.get('match_transaction_date')
        match_desc = params.get('match_description')
        if not match_date or not match_desc:
            return False, 'Missing information to identify the transaction to update'
        try:
            date.fromisoformat(str(match_date))
        except ValueError:
            return False, 'Invalid match date'

        candidates = Transaction.filter_transactions(mysql, user_id, date_from=match_date, date_to=match_date)
        match_desc_norm = str(match_desc).strip().lower()
        candidates = [t for t in candidates if (t.description or '').strip().lower() == match_desc_norm]
        if params.get('match_amount') is not None:
            try:
                match_amount = float(params['match_amount'])
            except (TypeError, ValueError):
                return False, 'Invalid match amount'
            candidates = [t for t in candidates if abs(float(t.amount) - match_amount) < 0.01]
        if not candidates:
            return False, 'Could not find a transaction matching that date and description'
        if len(candidates) > 1:
            return False, 'Multiple transactions match that date and description — include the amount to disambiguate'
        existing = candidates[0]

        tx_type = params.get('type') or existing.type
        if tx_type not in ('income', 'expense'):
            return False, 'Invalid transaction type'

        if params.get('amount') is not None:
            try:
                amount = float(params.get('amount'))
            except (TypeError, ValueError):
                return False, 'Invalid amount'
            if amount <= 0:
                return False, 'Amount must be positive'
        else:
            amount = existing.amount

        if params.get('transaction_date'):
            try:
                transaction_date = date.fromisoformat(str(params.get('transaction_date')))
            except ValueError:
                return False, 'Invalid transaction date'
        else:
            transaction_date = existing.transaction_date

        description = str(params.get('description') or existing.description or '')[:255]

        category_id = (
            _resolve_by_name(Category.get_all_by_user(mysql, user_id), params.get('category_name'))
            if params.get('category_name') else existing.category_id
        )
        account_id = (
            _resolve_by_name(Account.get_all_by_user(mysql, user_id), params.get('account_name'))
            if params.get('account_name') else existing.account_id
        )
        loan_id = (
            _resolve_by_name(Loan.get_all_by_user(mysql, user_id), params.get('loan_name'))
            if params.get('loan_name') else existing.loan_id
        )

        success, message = Transaction.update(
            mysql, existing.id, user_id, category_id, tx_type, amount,
            description, str(transaction_date), account_id, loan_id=loan_id,
        )
        return success, (f"Transaction updated (id={existing.id})" if success else message)

    if action_type == 'delete_transaction':
        match_date = params.get('match_transaction_date')
        match_desc = params.get('match_description')
        if not match_date or not match_desc:
            return False, 'Missing information to identify the transaction to delete'
        try:
            date.fromisoformat(str(match_date))
        except ValueError:
            return False, 'Invalid match date'

        candidates = Transaction.filter_transactions(mysql, user_id, date_from=match_date, date_to=match_date)
        match_desc_norm = str(match_desc).strip().lower()
        candidates = [t for t in candidates if (t.description or '').strip().lower() == match_desc_norm]
        if params.get('match_amount') is not None:
            try:
                match_amount = float(params['match_amount'])
            except (TypeError, ValueError):
                return False, 'Invalid match amount'
            candidates = [t for t in candidates if abs(float(t.amount) - match_amount) < 0.01]
        if not candidates:
            return False, 'Could not find a transaction matching that date and description'
        if len(candidates) > 1:
            return False, 'Multiple transactions match that date and description — include the amount to disambiguate'
        existing = candidates[0]

        return Transaction.delete(mysql, existing.id, user_id)

    if action_type == 'create_budget':
        try:
            total_limit = float(params.get('total_limit'))
        except (TypeError, ValueError):
            return False, 'Invalid budget limit'
        if total_limit <= 0:
            return False, 'Budget limit must be positive'
        try:
            start_date = date.fromisoformat(str(params.get('start_date')))
            end_date = date.fromisoformat(str(params.get('end_date')))
        except ValueError:
            return False, 'Invalid budget dates'
        if end_date <= start_date:
            return False, 'end_date must be after start_date'

        success, message, budget_id = Budget.create(
            mysql, user_id, str(params.get('name') or '')[:100],
            str(params.get('period_type') or 'custom'), str(start_date), str(end_date), total_limit,
        )
        return success, (f"Budget created (id={budget_id})" if success else message)

    if action_type == 'create_transfer':
        try:
            amount = float(params.get('amount'))
        except (TypeError, ValueError):
            return False, 'Invalid amount'
        if amount <= 0:
            return False, 'Amount must be positive'
        try:
            transfer_date = date.fromisoformat(str(params.get('transfer_date')))
        except ValueError:
            return False, 'Invalid transfer date'

        accounts = Account.get_all_by_user(mysql, user_id)
        from_account_id = _resolve_by_name(accounts, params.get('from_account_name'))
        to_account_id = _resolve_by_name(accounts, params.get('to_account_name'))
        if not from_account_id or not to_account_id:
            return False, 'Could not identify one or both accounts by name'
        if from_account_id == to_account_id:
            return False, 'Source and destination accounts must be different'

        success, message, transfer_id = Transfer.create(
            mysql, user_id, from_account_id, to_account_id, amount,
            str(params.get('description') or 'Transfer')[:255], str(transfer_date),
        )
        return success, (f"Transfer created (id={transfer_id})" if success else message)

    return False, f"Unknown action type: {action_type}"


@api_ai_advisor_bp.route('/history', methods=['GET'])
@api_login_required
def history():
    mysql = get_mysql()
    user_id = session['user_id']
    since = session.get('ai_chat_since')
    messages = AIConversation.get_recent(mysql, user_id, limit=DISPLAY_HISTORY_LIMIT, since=since)
    return jsonify({
        'success': True,
        'messages': [_message_to_dict(m) for m in messages],
    }), 200


@api_ai_advisor_bp.route('/clear', methods=['POST'])
@api_login_required
def clear():
    """User-triggered 'Clear conversation' — wipes all stored history, not
    just the current login's window."""
    mysql = get_mysql()
    user_id = session['user_id']
    AIConversation.delete_all(mysql, user_id)
    return jsonify({'success': True, 'message': 'Conversation cleared'}), 200


def _message_to_dict(m):
    return {
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'created_at': str(m.created_at) if m.created_at else None,
    }
