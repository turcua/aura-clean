"""
Aura Financial Tracker - Secure Version
APScheduler - Recurring Transaction Generator
Sprint 12: Accounts + Recurring Transactions

Runs hourly. Processes all users' due recurring transactions in one background
job — this is an internal system job, not a user-facing endpoint, so it does
not go through session/ownership checks; get_due() and mark_executed() are
scheduler-internal methods on RecurringTransaction, never called from a route.
"""

import os
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from models.recurring_transaction import RecurringTransaction
from models.transaction import Transaction
from models.budget import Budget
from models.notification import Notification
from models.ai_conversation import AIConversation
from models.user import User
# Sprint 51 (ENH-12): scheduler needs loan-computed installment lookups.
# routes.api.loans is not itself a "model", but compute_loan_status() is
# already an established cross-module import from a non-route caller —
# utils/ai_context.py does the same thing, for the same reason (no
# duplicating the projection logic).
from routes.api.loans import compute_loan_status

BILL_REMINDER_DAYS_AHEAD = 3
AI_CONVERSATION_RETENTION_DAYS = 90
# Sprint 57 (ENH-17): fixed statutory withholding rate on savings interest,
# not a per-account field — see run_interest_job()'s docstring.
INTEREST_TAX_RATE_PCT = 10


def run_recurring_job(mysql):
    """Find all due recurring transactions and generate them. Returns count generated."""
    today = date.today()
    generated = 0

    try:
        due = RecurringTransaction.get_due(mysql, today)
    except Exception:
        return 0

    for rt in due:
        try:
            # Sprint 51 (ENH-12): a loan-linked recurring transaction uses
            # the loan's current computed installment instead of the static
            # rt.amount, so it stays in sync with rate changes automatically.
            # Falls back to rt.amount if the loan lookup fails for any
            # reason (loan deleted mid-flight, no periods yet, etc.) — this
            # job must never skip generating the transaction just because
            # the amount lookup had a problem.
            amount = rt.amount
            if rt.loan_id:
                try:
                    status = compute_loan_status(mysql, rt.loan_id, rt.user_id)
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
                recurring_transaction_id=rt.id,
                # Sprint 51 (ENH-13): tagging the generated transaction with
                # the same loan_id makes it ledger-visible; payment_type
                # 'scheduled' is what keeps get_extra_payments() from
                # double-counting it — see that method's own docstring.
                loan_id=rt.loan_id,
                payment_type='scheduled' if rt.loan_id else None,
            )
            if success:
                generated += 1

            next_run = RecurringTransaction.calculate_next_run(today, rt.frequency)

            if rt.end_date and next_run > rt.end_date:
                RecurringTransaction.set_active(mysql, rt.id, rt.user_id, False)
            else:
                RecurringTransaction.mark_executed(mysql, rt.id, today, next_run)

        except Exception:
            continue

    return generated


def run_notification_job(mysql):
    """
    Sprint 21. Generates budget-overrun and upcoming-bill notifications for
    every user. Returns the count of new notifications actually created —
    duplicates caught by create_if_not_exists (same underlying event,
    already-notified) don't count.
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
    Sprint 25. For every active user with at least one real finding
    (spending anomaly, off-pace savings goal, or recurring-cost creep),
    narrate it via Solis once and deliver through the existing notification
    system. Users with no findings get skipped entirely — no Groq call, no
    notification — the main cost control for this job (Scope Decision 5).
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
    Sprint 57 (ENH-11). Runs daily; internally decides per-account whether
    today is actually due, since accrual frequency is selectable per
    account (daily or monthly) — a 'monthly' account only gets credited
    once per calendar month even though this job itself ticks every day.

    Interest amount: balance * (annual_rate / 100) / 365 for daily,
    / 12 for monthly — a simple even split, not real day-count-in-month
    precision (a bank's own compounding convention varies, and this is a
    personal tracker, not the bank itself). Skipped entirely for a
    zero/negative balance or an amount that rounds to 0.00, so no
    zero-value transactions ever get created.

    Category lookup is by name ("Saving Interest", the shared default
    category the user created for this feature) rather than a hardcoded
    id, since that could differ across environments (see
    Category.get_default_by_name()'s docstring) — falls back to
    category_id=None (uncategorized) rather than skipping interest
    entirely if that category doesn't exist for some reason.

    Sprint 57 (ENH-17): the full gross amount is posted as income, then a
    separate expense transaction withholds INTEREST_TAX_RATE_PCT of it —
    two ledger lines rather than crediting a pre-taxed net amount, mirroring
    how a real bank statement shows gross interest and tax withheld
    separately. A fixed statutory rate (matches ENH-11's own "no tiered
    rates" simplicity precedent), not a per-account field. The tax
    transaction is attempted only after the gross income transaction
    succeeds, and its own failure doesn't roll back or skip marking the
    account accrued — same best-effort-per-step convention as the rest of
    this job.
    """
    from models.account import Account
    from models.category import Category
    from models.transaction import Transaction

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
                continue  # shouldn't happen — get_accounts_for_interest() only returns rate>0 accounts, but frequency is a separate nullable column

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
    display boundary (session['ai_chat_since']) — this deletes rows outright
    after AI_CONVERSATION_RETENTION_DAYS regardless of session history."""
    try:
        return AIConversation.delete_older_than(mysql, days=AI_CONVERSATION_RETENTION_DAYS)
    except Exception:
        return 0


def _log_job_run(mysql, job_id, status, result_count=None, error_message=None):
    """
    Sprint 57 (ENH-02, group 5): one row per job execution, for the admin
    panel's scheduler health view. Every run gets logged — success, no-op,
    or error — not just the "did something" ones each job already prints
    to console for; a job silently crashing every hour previously left no
    record at all. Failure to log itself is swallowed (never let job-health
    bookkeeping break the actual job it's tracking).
    """
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO scheduler_job_runs (job_id, status, result_count, error_message) VALUES (%s, %s, %s, %s)",
            (job_id, status, result_count, error_message)
        )
        mysql.connection.commit()
        cursor.close()
    except Exception:
        try:
            mysql.connection.rollback()
        except Exception:
            pass


def init_scheduler(app):
    """
    Initialize and start the APScheduler background scheduler. Runs hourly.
    Guarded against the Werkzeug reloader double-starting it in debug mode.
    """
    scheduler = BackgroundScheduler()

    def job():
        with app.app_context():
            mysql = app.extensions['mysql']
            try:
                count = run_recurring_job(mysql)
                _log_job_run(mysql, 'recurring_transaction_job', 'success', result_count=count)
                if count > 0:
                    print(f'[Scheduler] Generated {count} recurring transactions for {date.today()}')
            except Exception as e:
                _log_job_run(mysql, 'recurring_transaction_job', 'error', error_message=str(e))
                print(f'[Scheduler] ERROR in recurring_transaction_job: {e}')

    scheduler.add_job(
        func=job,
        trigger='interval',
        hours=1,
        id='recurring_transaction_job',
        replace_existing=True,
    )

    def notification_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            try:
                count = run_notification_job(mysql)
                _log_job_run(mysql, 'notification_generation_job', 'success', result_count=count)
                if count > 0:
                    print(f'[Scheduler] Generated {count} notifications for {date.today()}')
            except Exception as e:
                _log_job_run(mysql, 'notification_generation_job', 'error', error_message=str(e))
                print(f'[Scheduler] ERROR in notification_generation_job: {e}')

    scheduler.add_job(
        func=notification_job,
        trigger='interval',
        hours=1,
        id='notification_generation_job',
        replace_existing=True,
    )

    def interest_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            try:
                count = run_interest_job(mysql)
                _log_job_run(mysql, 'interest_accrual_job', 'success', result_count=count)
                if count > 0:
                    print(f'[Scheduler] Credited interest to {count} accounts for {date.today()}')
            except Exception as e:
                _log_job_run(mysql, 'interest_accrual_job', 'error', error_message=str(e))
                print(f'[Scheduler] ERROR in interest_accrual_job: {e}')

    scheduler.add_job(
        func=interest_job,
        trigger='interval',
        hours=24,
        id='interest_accrual_job',
        replace_existing=True,
    )

    def ai_cleanup_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            try:
                count = run_ai_conversation_cleanup_job(mysql)
                _log_job_run(mysql, 'ai_conversation_cleanup_job', 'success', result_count=count)
                if count > 0:
                    print(f'[Scheduler] Deleted {count} AI conversation messages older than {AI_CONVERSATION_RETENTION_DAYS} days')
            except Exception as e:
                _log_job_run(mysql, 'ai_conversation_cleanup_job', 'error', error_message=str(e))
                print(f'[Scheduler] ERROR in ai_conversation_cleanup_job: {e}')

    scheduler.add_job(
        func=ai_cleanup_job,
        trigger='interval',
        hours=24,
        id='ai_conversation_cleanup_job',
        replace_existing=True,
    )

    def ai_insight_job():
        with app.app_context():
            mysql = app.extensions['mysql']
            try:
                count = run_ai_insight_job(mysql)
                _log_job_run(mysql, 'ai_insight_job', 'success', result_count=count)
                if count > 0:
                    print(f'[Scheduler] Generated {count} AI insight notifications for {date.today()}')
            except Exception as e:
                _log_job_run(mysql, 'ai_insight_job', 'error', error_message=str(e))
                print(f'[Scheduler] ERROR in ai_insight_job: {e}')

    scheduler.add_job(
        func=ai_insight_job,
        trigger='interval',
        hours=24,
        id='ai_insight_job',
        replace_existing=True,
    )

    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()
        print('[Scheduler] Recurring transaction scheduler started (runs every hour)')
        print('[Scheduler] Notification generation job registered (runs every hour)')
        print('[Scheduler] Interest accrual job registered (runs every 24 hours)')
        print('[Scheduler] AI conversation cleanup job registered (runs every 24 hours)')
        print('[Scheduler] AI insight job registered (runs every 24 hours)')

    return scheduler
