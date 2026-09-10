"""
Aura Financial Tracker - Secure Version
AI Tool Definitions
Sprint 26: Excessive Agency

Security properties (contrast with vulnerable-version/utils/ai_tools.py):
- This file defines the tool schemas only — there is no execute function
  here. Solis proposing a tool call never executes anything by itself;
  routes/api/ai_advisor.py stores it as a pending action, and only
  POST /confirm-action can actually run it, after independently
  re-validating every parameter server-side. The AI's output is treated as
  an untrusted suggestion, never as an authorization.
"""

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
