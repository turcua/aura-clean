"""
Aura Financial Tracker - Vulnerable Version
AI Tool Definitions + Execution (WITH INTENTIONAL VULNERABILITIES)
Sprint 26: Excessive Agency

VULNERABILITY (VULN-079): execute_tool_call() runs whatever Groq decided to
call, immediately, with no user confirmation and no re-validation beyond
whatever the model itself sent. user_id comes from the request (same
established IDOR pattern as every other endpoint in this version) — never
independently verified against a session. Chains directly with VULN-077:
a poisoned transaction description can cause this to fire on a completely
unrelated future chat message, with no attacker present at exploitation time.
"""

import json

from models.transaction import Transaction
from models.budget import Budget
from models.transfer import Transfer
from models.account import Account
from models.category import Category
from models.loan import Loan

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_transaction",
            "description": "Create a new income or expense transaction for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["income", "expense"]},
                    "amount": {"type": ["number", "string"], "description": "Positive amount"},
                    "description": {"type": "string"},
                    "transaction_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "category_name": {"type": "string", "description": "Exact category name from the Available categories list, if the user specified or implied one"},
                    "account_name": {"type": "string", "description": "Exact account name from the Accounts list, if the user specified or implied one"},
                    "loan_name": {"type": "string", "description": "Exact loan name from the Loans list, if this transaction is an extra payment toward a loan"},
                },
                "required": ["type", "amount", "description", "transaction_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_transaction",
            "description": "Update an existing transaction. Identify it using its current date and description exactly as shown in the Transactions list (add the amount too if that alone doesn't uniquely identify one transaction), then supply only the fields that should change. Only call this once the user has told you a specific new value for at least one field — if their request doesn't say what should change (e.g. just \"edit that transaction\"), ask them what to change instead of guessing or inventing a value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_transaction_date": {"type": "string", "description": "The transaction's CURRENT date (YYYY-MM-DD), exactly as shown in the Transactions list — used to find it"},
                    "match_description": {"type": "string", "description": "The transaction's CURRENT description, exactly as shown in the Transactions list — used to find it"},
                    "match_amount": {"type": ["number", "string"], "description": "The transaction's CURRENT amount — only needed if date+description alone don't uniquely identify one transaction"},
                    "type": {"type": "string", "enum": ["income", "expense"], "description": "New type, if it should change"},
                    "amount": {"type": ["number", "string"], "description": "New amount, if it should change"},
                    "description": {"type": "string", "description": "New description, if it should change"},
                    "transaction_date": {"type": "string", "description": "New date (YYYY-MM-DD), if it should change"},
                    "category_name": {"type": "string", "description": "New exact category name from the Available categories list, if it should change"},
                    "account_name": {"type": "string", "description": "New exact account name from the Accounts list, if it should change"},
                    "loan_name": {"type": "string", "description": "New exact loan name from the Loans list, if it should change"},
                },
                "required": ["match_transaction_date", "match_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction",
            "description": "Delete an existing transaction. Identify it using its date and description exactly as shown in the Transactions list (add the amount too if that alone doesn't uniquely identify one transaction).",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_transaction_date": {"type": "string", "description": "The transaction's date (YYYY-MM-DD), exactly as shown in the Transactions list — used to find it"},
                    "match_description": {"type": "string", "description": "The transaction's description, exactly as shown in the Transactions list — used to find it"},
                    "match_amount": {"type": ["number", "string"], "description": "The transaction's amount — only needed if date+description alone don't uniquely identify one transaction"},
                },
                "required": ["match_transaction_date", "match_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_budget",
            "description": "Create a new budget for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "period_type": {"type": "string", "enum": ["monthly", "weekly", "yearly", "custom"]},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "total_limit": {"type": ["number", "string"], "description": "Positive spending limit"},
                },
                "required": ["name", "period_type", "start_date", "end_date", "total_limit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_transfer",
            "description": "Transfer money from one of the user's accounts to another. Use this instead of create_transaction whenever the user describes moving money between their own accounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_account_name": {"type": "string", "description": "Exact source account name from the Accounts list"},
                    "to_account_name": {"type": "string", "description": "Exact destination account name from the Accounts list"},
                    "amount": {"type": ["number", "string"], "description": "Positive amount, in the source account's currency"},
                    "description": {"type": "string"},
                    "transfer_date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["from_account_name", "to_account_name", "amount", "transfer_date"],
            },
        },
    },
]


def _resolve_by_name(items, name):
    """Case-insensitive exact match on .name; None if no name given or no match."""
    if not name:
        return None
    for item in items:
        if item.name and item.name.strip().lower() == name.strip().lower():
            return item.id
    return None


def execute_tool_call(mysql, user_id, tool_call):
    """
    VULNERABILITY: executes immediately, no confirmation, no bounds/ownership
    re-validation. Returns a plain-text result string to feed back to the model.
    """
    name = tool_call['function']['name']
    try:
        args = json.loads(tool_call['function']['arguments'])
    except (KeyError, ValueError):
        return "Error: could not parse tool arguments"

    if name == 'create_transaction':
        category_id = _resolve_by_name(Category.get_all_by_user(mysql, user_id), args.get('category_name'))
        account_id = _resolve_by_name(Account.get_all_by_user(mysql, user_id), args.get('account_name'))
        loan_id = _resolve_by_name(Loan.get_all_by_user(mysql, user_id), args.get('loan_name'))
        success, message, tx_id = Transaction.create(
            mysql, user_id,
            category_id, args.get('type'), args.get('amount'),
            args.get('description'), args.get('transaction_date'),
            account_id, loan_id=loan_id,
        )
        return f"Transaction created (id={tx_id})" if success else f"Failed: {message}"

    if name == 'update_transaction':
        candidates = Transaction.filter_transactions(
            mysql, user_id,
            date_from=args.get('match_transaction_date'),
            date_to=args.get('match_transaction_date'),
        )
        match_desc = (args.get('match_description') or '').strip().lower()
        candidates = [t for t in candidates if (t.description or '').strip().lower() == match_desc]
        if args.get('match_amount') is not None:
            try:
                match_amount = float(args['match_amount'])
                candidates = [t for t in candidates if abs(float(t.amount) - match_amount) < 0.01]
            except (TypeError, ValueError):
                pass
        if not candidates:
            return "Failed: could not find a transaction matching that date and description"
        if len(candidates) > 1:
            return "Failed: multiple transactions match that date and description — include the amount to disambiguate"
        existing = candidates[0]

        category_id = _resolve_by_name(Category.get_all_by_user(mysql, user_id), args.get('category_name')) \
            if args.get('category_name') else existing.category_id
        account_id = _resolve_by_name(Account.get_all_by_user(mysql, user_id), args.get('account_name')) \
            if args.get('account_name') else existing.account_id
        loan_id = _resolve_by_name(Loan.get_all_by_user(mysql, user_id), args.get('loan_name')) \
            if args.get('loan_name') else existing.loan_id

        success, message = Transaction.update(
            mysql, existing.id, user_id, category_id,
            args.get('type') or existing.type,
            args.get('amount') if args.get('amount') is not None else existing.amount,
            args.get('description') or existing.description,
            args.get('transaction_date') or existing.transaction_date,
            account_id, loan_id=loan_id,
        )
        return f"Transaction updated (id={existing.id})" if success else f"Failed: {message}"

    if name == 'delete_transaction':
        candidates = Transaction.filter_transactions(
            mysql, user_id,
            date_from=args.get('match_transaction_date'),
            date_to=args.get('match_transaction_date'),
        )
        match_desc = (args.get('match_description') or '').strip().lower()
        candidates = [t for t in candidates if (t.description or '').strip().lower() == match_desc]
        if args.get('match_amount') is not None:
            try:
                match_amount = float(args['match_amount'])
                candidates = [t for t in candidates if abs(float(t.amount) - match_amount) < 0.01]
            except (TypeError, ValueError):
                pass
        if not candidates:
            return "Failed: could not find a transaction matching that date and description"
        if len(candidates) > 1:
            return "Failed: multiple transactions match that date and description — include the amount to disambiguate"
        existing = candidates[0]

        success, message = Transaction.delete(mysql, existing.id)
        return f"Transaction deleted (id={existing.id})" if success else f"Failed: {message}"

    if name == 'create_budget':
        success, message, budget_id = Budget.create(
            mysql, user_id,
            args.get('name'), args.get('period_type'),
            args.get('start_date'), args.get('end_date'), args.get('total_limit'),
        )
        return f"Budget created (id={budget_id})" if success else f"Failed: {message}"

    if name == 'create_transfer':
        accounts = Account.get_all_by_user(mysql, user_id)
        from_account_id = _resolve_by_name(accounts, args.get('from_account_name'))
        to_account_id = _resolve_by_name(accounts, args.get('to_account_name'))
        if not from_account_id or not to_account_id:
            return "Failed: could not identify one or both accounts by name"
        success, message, transfer_id = Transfer.create(
            mysql, user_id, from_account_id, to_account_id,
            args.get('amount'), args.get('description'), args.get('transfer_date'),
        )
        return f"Transfer created (id={transfer_id})" if success else f"Failed: {message}"

    return f"Error: unknown tool {name}"
