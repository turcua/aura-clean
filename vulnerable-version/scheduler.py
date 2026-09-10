"""
Aura Financial Tracker - Vulnerable Version
APScheduler - Recurring Transaction Generator (WITH INTENTIONAL VULNERABILITIES)
Sprint 3: Shadow Extractor

VULNERABILITY: Scheduler processes ALL users' recurring transactions in one job
VULNERABILITY: No per-user isolation or rate limiting
VULNERABILITY: Manual trigger endpoint requires no authentication
VULNERABILITY: Detailed error output leaks internal state
"""

from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from models.recurring_transaction import RecurringTransaction
from models.transaction import Transaction
from models.transfer import Transfer
from models.budget import Budget
from models.notification import Notification
from models.ai_conversation import AIConversation
from models.user import User
# Sprint 51 (ENH-12): same cross-module reuse already precedented by
# utils/ai_context.py's use of compute_loan_status().
from routes.api.loans import compute_loan_status

BILL_REMINDER_DAYS_AHEAD = 3
AI_CONVERSATION_RETENTION_DAYS = 90
# Sprint 57 (ENH-17): fixed statutory withholding rate on savings interest,
# not a per-account field — mirrors secure-version.
INTEREST_TAX_RATE_PCT = 10


def run_recurring_job(mysql):
    """
    Core logic: find all due recurring transactions and generate them.
    Returns the count of transactions generated.
    VULNERABILITY: Processes all users globally with no isolation
    VULNERABILITY: SQL Injection in date parameter (via model)
    """
    today = date.today()
    generated = 0

    try:
        due = RecurringTransaction.get_due(mysql, today)
    except Exception:
        return 0

    for rt in due:
        try:
            if rt.type in ('income', 'expense'):
                # Sprint 51 (ENH-12): loan-linked recurring transactions use
                # the loan's current computed installment instead of the
                # static rt.amount. Falls back to rt.amount on any lookup
                # failure — never skip generating the transaction over this.
                amount = rt.amount
                if rt.loan_id:
                    try:
                        status = compute_loan_status(mysql, rt.loan_id)
                        if status and status.get('current_installment') is not None:
                            amount = status['current_installment']
                    except Exception:
                        pass

                success, _, tx_id = Transaction.create(
                    mysql,
                    user_id=rt.user_id,
                    category_id=rt.category_id,
                    type=rt.type,
                    amount=amount,
                    description=rt.description or f'Recurring: {rt.frequency}',
                    transaction_date=str(today),
                    account_id=rt.account_id,
                    is_transfer=False,
                    recurring_transaction_id=rt.id,
                    # Sprint 51 (ENH-13): same reasoning as secure-version.
                    loan_id=rt.loan_id,
                    payment_type='scheduled' if rt.loan_id else None,
                )
                if success:
                    generated += 1

            elif rt.type == 'transfer' and rt.to_account_id:
                success, _, tf_id = Transfer.create(
                    mysql,
                    user_id=rt.user_id,
                    from_account_id=rt.account_id,
                    to_account_id=rt.to_account_id,
                    amount=rt.amount,
                    description=rt.description or 'Recurring Transfer',
                    transfer_date=str(today),
                    recurring_transaction_id=rt.id
                )
                if success:
                    generated += 1

            # Calculate and store next run date
            next_run = RecurringTransaction.calculate_next_run(today, rt.frequency)

            # Deactivate if past end_date
            if rt.end_date and next_run > rt.end_date:
                RecurringTransaction.set_active(mysql, rt.id, False)
            else:
                RecurringTransaction.mark_executed(mysql, rt.id, today, next_run)

        except Exception:
            # VULNERABILITY: Silent failure - skips errored transactions without alerting
            continue

    return generated


def run_notification_job(mysql):
    """
    Sprint 21. Generates budget-overrun and upcoming-bill notifications for
    every user.
    VULNERABILITY: category names and recurring-transaction descriptions
    (both user-controlled) flow straight into notification title/message,
    which Notification.create_if_not_exists() then interpolates into raw
    SQL (VULN-073) and which the frontend later renders via innerHTML
    (VULN-074) — the same values chained through two separate sinks.
    """
    created = 0
    today = date.today()

    try:
        for budget_id, user_id, category_id, category_name, limit_amount, spent in Budget.get_all_active_spending(mysql):
            limit_amount = float(limit_amount or 0)
            spent = float(spent or 0)
            if limit_amount <= 0 or spent <= limit_amount:
                continue
            name = category_name or 'Uncategorized'
            title = f'Budget exceeded: {name}'
            message = f'You have spent RON {spent:.2f} against a limit of RON {limit_amount:.2f} for {name} this budget period.'
            dedupe_key = f'budget_overrun:{budget_id}:{category_id}'
            if Notification.create_if_not_exists(mysql, user_id, 'budget_overrun', title, message, dedupe_key):
                created += 1
    except Exception:
        pass

    try:
        window_end = today + timedelta(days=BILL_REMINDER_DAYS_AHEAD)
        for rt in RecurringTransaction.get_upcoming(mysql, today, window_end):
            desc = rt.description or f'{rt.frequency} payment'
            title = 'Upcoming bill reminder'
            message = f'{desc} (RON {float(rt.amount):.2f}) is due on {rt.next_run_date}.'
            dedupe_key = f'bill_reminder:{rt.id}:{rt.next_run_date}'
            if Notification.create_if_not_exists(mysql, rt.user_id, 'bill_reminder', title, message, dedupe_key):
                created += 1
    except Exception:
        pass

    return created


def run_ai_insight_job(mysql):
    """
    Sprint 25. For every active user with at least one real finding,
    narrate it via Solis once and deliver through the existing notification
    system. Users with no findings get skipped entirely.
    """
    from flask import current_app
    from utils.ai_insights import build_findings, narrate_findings

    api_key = current_app.config.get('GROQ_API_KEY')
    model = current_app.config.get('GROQ_MODEL')
    today = date.today()
    created = 0

    for user_id in User.get_all_ids(mysql):
        try:
            findings, has_findings = build_findings(mysql, user_id)
            if not has_findings:
                continue
            message = narrate_findings(api_key, model, findings)
            if not message:
                continue
            dedupe_key = f'ai_insight:{user_id}:{today.isoformat()}'
            if Notification.create_if_not_exists(mysql, user_id, 'ai_insight', 'Insight from Solis', message, dedupe_key):
                created += 1
        except Exception:
            continue

    return created


def run_interest_job(mysql):
    """
    Sprint 57 (ENH-11). Mirrors secure-version's run_interest_job() — see
    that version's docstring for the full reasoning (daily job, per-account
    due-ness check, simple even-split interest formula, category lookup by
    name with a graceful uncategorized fallback). No per-user isolation
    here either, consistent with every other job in this file.

    Sprint 57 (ENH-17): also mirrors secure-version's gross-income +
    separate-tax-expense withholding (INTEREST_TAX_RATE_PCT), including the
    same best-effort-per-step handling — the tax transaction's own failure
    doesn't roll back or skip marking the account accrued.
    """
    from models.account import Account
    from models.category import Category

    today = date.today()
    credited = 0

    interest_category = Category.get_default_by_name(mysql, 'Saving Interest')
    category_id = interest_category.id if interest_category else None
    tax_category = Category.get_default_by_name(mysql, 'Saving Interest Tax')
    tax_category_id = tax_category.id if tax_category else None

    try:
        accounts = Account.get_accounts_for_interest(mysql)
    except Exception:
        return 0

    for acct in accounts:
        try:
            last = acct.last_interest_accrued_date
            if acct.interest_accrual_frequency == 'daily':
                due = last is None or last < today
                divisor = 365
            elif acct.interest_accrual_frequency == 'monthly':
                due = last is None or (last.year, last.month) != (today.year, today.month)
                divisor = 12
            else:
                continue

            if not due:
                continue

            balance = float(acct.current_balance or 0)
            if balance <= 0:
                continue

            amount = round(balance * (float(acct.interest_rate_annual) / 100) / divisor, 2)
            if amount <= 0:
                continue

            success, _, _ = Transaction.create(
                mysql,
                user_id=acct.user_id,
                category_id=category_id,
                type='income',
                amount=amount,
                description=f'Interest earned ({acct.interest_accrual_frequency})',
                transaction_date=str(today),
                account_id=acct.id,
            )
            if success:
                Account.mark_interest_accrued(mysql, acct.id, today)
                credited += 1

                tax_amount = round(amount * INTEREST_TAX_RATE_PCT / 100, 2)
                if tax_amount > 0:
                    Transaction.create(
                        mysql,
                        user_id=acct.user_id,
                        category_id=tax_category_id,
                        type='expense',
                        amount=tax_amount,
                        description=f'Tax withheld on interest ({INTEREST_TAX_RATE_PCT}%)',
                        transaction_date=str(today),
                        account_id=acct.id,
                    )
        except Exception:
            continue

    return credited


def run_ai_conversation_cleanup_job(mysql):
    """Sprint 23 follow-up: retention cleanup, independent of the per-login
    display boundary (session['ai_chat_since'])."""
    try:
        return AIConversation.delete_older_than(mysql, days=AI_CONVERSATION_RETENTION_DAYS)
    except Exception:
        return 0


def init_scheduler(app):
    """
    Initialize and start the APScheduler background scheduler.
    Runs the recurring job every hour.

    VULNERABILITY: Debug mode causes werkzeug reloader to fork the process,
    which would start two schedulers. Guard with WERKZEUG_RUN_MAIN check.
    """
    import os

    scheduler = BackgroundScheduler()

    def job():
        with app.app_context():
            mysql = app.extensions['mysql']
            count = run_recurring_job(mysql)
            if count > 0:
                # VULNERABILITY: Internal processing details printed to stdout
                print(f'[Scheduler] Generated {count} recurring transactions for {date.today()}')

    scheduler.add_job(
        func=job,
        trigger='interval',
        hours=1,
        id='recurring_transaction_job',
        replace_existing=True
    )

    def notification_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            count = run_notification_job(mysql)
            if count > 0:
                print(f'[Scheduler] Generated {count} notifications for {date.today()}')

    scheduler.add_job(
        func=notification_job,
        trigger='interval',
        hours=1,
        id='notification_generation_job',
        replace_existing=True
    )

    def interest_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            count = run_interest_job(mysql)
            if count > 0:
                print(f'[Scheduler] Credited interest to {count} accounts for {date.today()}')

    scheduler.add_job(
        func=interest_job,
        trigger='interval',
        hours=24,
        id='interest_accrual_job',
        replace_existing=True
    )

    def ai_cleanup_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            count = run_ai_conversation_cleanup_job(mysql)
            if count > 0:
                print(f'[Scheduler] Deleted {count} AI conversation messages older than {AI_CONVERSATION_RETENTION_DAYS} days')

    scheduler.add_job(
        func=ai_cleanup_job,
        trigger='interval',
        hours=24,
        id='ai_conversation_cleanup_job',
        replace_existing=True
    )

    def ai_insight_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            count = run_ai_insight_job(mysql)
            if count > 0:
                print(f'[Scheduler] Generated {count} AI insight notifications for {date.today()}')

    scheduler.add_job(
        func=ai_insight_job,
        trigger='interval',
        hours=24,
        id='ai_insight_job',
        replace_existing=True
    )

    # Guard against double-start from werkzeug reloader in debug mode
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()
        print('[Scheduler] Recurring transaction scheduler started (runs every hour)')
        print('[Scheduler] Notification generation job registered (runs every hour)')
        print('[Scheduler] Interest accrual job registered (runs every 24 hours)')
        print('[Scheduler] AI conversation cleanup job registered (runs every 24 hours)')
        print('[Scheduler] AI insight job registered (runs every 24 hours)')

    return scheduler
