#!/usr/bin/env python3
"""
Aura CTF Victim Seeder — Sprint 45 (Release 9, "Shattered Veil")
Standalone script — populates aura_vulnerable with synthetic "victim"
accounts for hackers to target via the app's cataloged vulnerabilities.

Every persona, account, transaction, budget, goal, and loan below is
entirely fabricated for this CTF. None of it is derived from, sampled
from, or related in any way to any real person's actual finances.

Prerequisites:
    pip install mysql-connector-python
    Docker containers running: docker compose up -d

Usage:
    python3 seed_ctf_victims.py           # insert (warns if victims exist)
    python3 seed_ctf_victims.py --reset   # wipe the seeded CTF victims and re-seed
"""

import sys
import random
import calendar
from datetime import date
import mysql.connector

# ── DB connection ────────────────────────────────────────────────────────────
DB = dict(
    host='127.0.0.1',
    port=3307,
    user='aura_user',
    password='VulnUserPass123!',
    database='aura_vulnerable',
)

VICTIM_USERNAMES = ['emma', 'james', 'olivia', 'daniel', 'sophie']

TODAY = date.today()


def month_back(n):
    """First day of the month n months before today's month."""
    y, m = TODAY.year, TODAY.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return date(y, m, 1)


def month_forward(n):
    """First day of the month n months after today's month."""
    y, m = TODAY.year, TODAY.month
    for _ in range(n):
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return date(y, m, 1)


# Oldest -> current, so seeded data always looks recent regardless of when
# this script is actually run.
MONTHS = [month_back(2), month_back(1), month_back(0)]
CURRENT_MONTH = MONTHS[-1]


# ── Victim personas (entirely fabricated) ────────────────────────────────────
# Each account entry: key -> (display name, type, include_in_budget)
# income/expenses entries: (category name, monthly amount, day-of-month, jitter)
# transfers: (from_key, to_key, monthly amount, day-of-month)
# budget: category limits deliberately below actual spend for victim2, to
#         exercise the existing budget-overrun notification/business-logic path
# savings_goal: victim5's is already at its target on purpose, to exercise the
#         pre-existing "status not auto-updated at 100%" bug (BUG-008)
# loan: bare loans row (no loan_events) — enough to make VULN-080's IDOR/SQLi
#         reachable without needing to replicate the full amortization engine

VICTIMS = [
    {
        'username': 'emma',
        'email': 'emma@ctf.local',
        'password': 'sunshine1',
        'accounts': {
            'chk': ('Main Checking', 'checking', True),
            'sav': ('Car Fund Savings', 'savings', True),
        },
        'primary': 'chk',
        'income': [
            ('Salary', 4200, 1, 50),
        ],
        'expenses': [
            ('Housing', 1200, 3, 0),
            ('Food & Dining', 650, 10, 80),
            ('Transport', 180, 12, 30),
            ('Utilities', 220, 5, 20),
            ('Entertainment', 150, 18, 40),
            ('Shopping', 300, 20, 90),
        ],
        'transfers': [
            ('chk', 'sav', 800, 27),
        ],
        'budget': {
            'name': f'{CURRENT_MONTH.strftime("%B %Y")} Essentials',
            'total_limit': 3000,
            'category_limits': {'Food & Dining': 700, 'Transport': 200, 'Entertainment': 200},
        },
        'savings_goal': {
            'account': 'sav', 'name': 'New Car Fund',
            'target_amount': 40000, 'current_amount': 8400,
            'target_date': date(TODAY.year + 2, 6, 30), 'monthly_target': 800,
            'status': 'active',
        },
        'loan': None,
    },
    {
        'username': 'james',
        'email': 'james@ctf.local',
        'password': 'letmein22',
        'accounts': {
            'chk': ('Everyday Checking', 'checking', True),
            'cc': ('Star Credit Card', 'credit_card', False),
        },
        'primary': 'chk',
        'income': [
            ('Salary', 3800, 1, 0),
        ],
        'expenses': [
            ('Housing', 950, 2, 0),
            ('Food & Dining', 700, 8, 100),
            ('Transport', 220, 14, 40),
            ('Entertainment', 380, 16, 60),
            ('Shopping', 550, 22, 120),
        ],
        'transfers': [
            ('chk', 'cc', 400, 26),
        ],
        'budget': {
            # Deliberately tight limits — actual Shopping/Entertainment spend
            # above exceeds these most months, exercising the budget-overrun
            # notification path (VULN-034's business-logic finding).
            'name': f'{CURRENT_MONTH.strftime("%B %Y")} Budget',
            'total_limit': 2200,
            'category_limits': {'Shopping': 300, 'Entertainment': 200, 'Food & Dining': 550},
        },
        'savings_goal': None,
        'loan': None,
    },
    {
        'username': 'olivia',
        'email': 'olivia@ctf.local',
        'password': 'homeowner3',
        'accounts': {
            'chk': ('Household Checking', 'checking', True),
            'sav': ('Emergency Fund', 'savings', True),
        },
        'primary': 'chk',
        'income': [
            ('Salary', 5200, 1, 0),
            ('Freelance', 500, 15, 300),
        ],
        'expenses': [
            ('Utilities', 380, 4, 40),
            ('Food & Dining', 800, 9, 90),
            ('Transport', 260, 13, 50),
            ('Healthcare', 150, 19, 100),
            ('Shopping', 250, 24, 70),
        ],
        'transfers': [
            ('chk', 'sav', 400, 27),
        ],
        'budget': None,
        'savings_goal': {
            'account': 'sav', 'name': 'Emergency Fund',
            'target_amount': 20000, 'current_amount': 6400,
            'target_date': date(TODAY.year + 1, 12, 31), 'monthly_target': 400,
            'status': 'active',
        },
        'loan': {
            'name': 'Home Mortgage',
            'principal': 250000.00,
            'margin_pct': 2.000,
            'initial_base_index_pct': 6.500,
            'start_date': date(TODAY.year - 3, 3, 1),
            'original_term_months': 300,
            'currency': 'RON',
        },
    },
    {
        'username': 'daniel',
        'email': 'daniel@ctf.local',
        'password': 'freelancer44',
        'accounts': {
            'chk': ('Freelance Checking', 'checking', True),
            'inv': ('Investment Portfolio', 'investment', True),
        },
        'primary': 'chk',
        'income': [
            ('Freelance', 3200, 5, 1800),
            ('Investment', 150, 20, 200),
        ],
        'expenses': [
            ('Housing', 900, 2, 0),
            ('Food & Dining', 500, 11, 70),
            ('Transport', 140, 15, 30),
            ('Entertainment', 200, 21, 50),
        ],
        'transfers': [
            ('chk', 'inv', 500, 28),
        ],
        'budget': None,
        'savings_goal': {
            'account': 'inv', 'name': 'Business Equipment',
            'target_amount': 15000, 'current_amount': 4100,
            'target_date': date(TODAY.year + 1, 6, 30), 'monthly_target': 500,
            'status': 'active',
        },
        'loan': None,
    },
    {
        'username': 'sophie',
        'email': 'sophie@ctf.local',
        'password': 'student55',
        'accounts': {
            'chk': ('Student Checking', 'checking', True),
        },
        'primary': 'chk',
        'income': [
            ('Salary', 1200, 1, 0),
            ('Gift', 200, 17, 150),
        ],
        'expenses': [
            ('Food & Dining', 350, 9, 50),
            ('Transport', 90, 13, 20),
            ('Education', 200, 6, 0),
            ('Entertainment', 60, 19, 30),
        ],
        'transfers': [],
        'budget': None,
        'savings_goal': {
            # Deliberately already at (in fact past) its target — exercises
            # the pre-existing "status not auto-updated at 100%" bug (BUG-008):
            # this goal should show as 'achieved' but the app never flips it.
            'account': 'chk', 'name': 'Laptop Fund',
            'target_amount': 3000, 'current_amount': 3000,
            'target_date': month_forward(1), 'monthly_target': 100,
            'status': 'active',
        },
        'loan': None,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_or_create_user(cur, username, email, password):
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
        (username, email, password),
    )
    return cur.lastrowid


def get_category_id(cur, name, cat_type):
    cur.execute(
        "SELECT id FROM categories WHERE user_id IS NULL AND name = %s AND type = %s",
        (name, cat_type),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Global default category not found: {name} ({cat_type})")
    return row[0]


def get_or_create_account(cur, user_id, name, acc_type, include_in_budget):
    cur.execute(
        "SELECT id FROM accounts WHERE user_id = %s AND name = %s",
        (user_id, name),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """INSERT INTO accounts
               (user_id, name, type, initial_balance, current_balance,
                include_in_budget, description)
           VALUES (%s, %s, %s, 0, 0, %s, %s)""",
        (user_id, name, acc_type, 1 if include_in_budget else 0,
         f'Synthetic CTF victim account ({acc_type})'),
    )
    return cur.lastrowid


def insert_tx(cur, user_id, account_id, category_id, tx_type, amount, description, tx_date,
              is_transfer=False):
    if not amount or amount <= 0:
        return None
    cur.execute(
        """INSERT INTO transactions
               (user_id, account_id, category_id, type, amount, description,
                transaction_date, is_transfer)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, account_id, category_id, tx_type,
         round(float(amount), 2), description, tx_date, is_transfer),
    )
    return cur.lastrowid


def insert_transfer(cur, user_id, from_acc, to_acc, amount, description, tx_date):
    if not amount or amount <= 0:
        return
    amt = round(float(amount), 2)
    from_tx = insert_tx(cur, user_id, from_acc, None, 'expense', amt, description, tx_date, True)
    to_tx = insert_tx(cur, user_id, to_acc, None, 'income', amt, description, tx_date, True)
    cur.execute(
        """INSERT INTO transfers
               (user_id, from_account_id, to_account_id,
                from_transaction_id, to_transaction_id,
                amount, description, transfer_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, from_acc, to_acc, from_tx, to_tx, amt, description, tx_date),
    )


def insert_budget(cur, user_id, budget_cfg):
    start = CURRENT_MONTH
    last_day = calendar.monthrange(start.year, start.month)[1]
    end = date(start.year, start.month, last_day)
    cur.execute(
        """INSERT INTO budgets (user_id, name, period_type, start_date, end_date, total_limit, is_active)
           VALUES (%s, %s, 'monthly', %s, %s, %s, TRUE)""",
        (user_id, budget_cfg['name'], start, end, budget_cfg['total_limit']),
    )
    budget_id = cur.lastrowid
    for cat_name, limit in budget_cfg['category_limits'].items():
        cat_id = get_category_id(cur, cat_name, 'expense')
        cur.execute(
            "INSERT INTO budget_categories (budget_id, category_id, limit_amount) VALUES (%s, %s, %s)",
            (budget_id, cat_id, limit),
        )


def insert_savings_goal(cur, user_id, account_id, goal_cfg):
    cur.execute(
        """INSERT INTO savings_goals
               (user_id, account_id, name, target_amount, current_amount,
                target_date, monthly_target, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, account_id, goal_cfg['name'], goal_cfg['target_amount'],
         goal_cfg['current_amount'], goal_cfg['target_date'],
         goal_cfg['monthly_target'], goal_cfg['status']),
    )


def insert_loan(cur, user_id, loan_cfg):
    cur.execute(
        """INSERT INTO loans
               (user_id, name, principal, margin_pct, initial_base_index_pct,
                start_date, original_term_months, currency, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')""",
        (user_id, loan_cfg['name'], loan_cfg['principal'], loan_cfg['margin_pct'],
         loan_cfg['initial_base_index_pct'], loan_cfg['start_date'],
         loan_cfg['original_term_months'], loan_cfg['currency']),
    )


def recalc_balances(cur, account_ids):
    for aid in account_ids:
        cur.execute(
            """SELECT a.initial_balance + COALESCE(
                   SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE -t.amount END), 0
               )
               FROM accounts a
               LEFT JOIN transactions t ON t.account_id = a.id
               WHERE a.id = %s""",
            (aid,),
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            cur.execute(
                "UPDATE accounts SET current_balance = %s WHERE id = %s",
                (float(row[0]), aid),
            )


def reset_victims(cur, conn):
    placeholders = ','.join(['%s'] * len(VICTIM_USERNAMES))
    cur.execute(f"SELECT id FROM users WHERE username IN ({placeholders})", VICTIM_USERNAMES)
    ids = [r[0] for r in cur.fetchall()]
    if not ids:
        return
    id_ph = ','.join(['%s'] * len(ids))

    # Row counts before deleting, printed explicitly — the reseeded data is
    # deterministic (fixed RNG seed per username, dates derived from today),
    # so a reset-then-reseed on the same day looks identical to the data it
    # replaced. Printing real counts here makes the delete step verifiable
    # instead of just trusted.
    cur.execute(f"SELECT COUNT(*) FROM transactions WHERE user_id IN ({id_ph})", ids)
    tx_count = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM accounts WHERE user_id IN ({id_ph})", ids)
    acc_count = cur.fetchone()[0]
    print(f"  Resetting — deleting {len(ids)} victim(s), {acc_count} account(s), {tx_count} transaction(s) …")

    # No FK on user_id for these tables — explicit deletes needed, same
    # reasoning as Sprint 45's reset-script scope decision 3.
    cur.execute(f"DELETE FROM transfers WHERE user_id IN ({id_ph})", ids)
    cur.execute(f"SELECT id FROM budgets WHERE user_id IN ({id_ph})", ids)
    budget_ids = [r[0] for r in cur.fetchall()]
    if budget_ids:
        bp = ','.join(['%s'] * len(budget_ids))
        cur.execute(f"DELETE FROM budget_categories WHERE budget_id IN ({bp})", budget_ids)
    cur.execute(f"DELETE FROM budgets WHERE user_id IN ({id_ph})", ids)
    cur.execute(f"DELETE FROM savings_goals WHERE user_id IN ({id_ph})", ids)
    cur.execute(f"DELETE FROM transactions WHERE user_id IN ({id_ph})", ids)
    cur.execute(f"DELETE FROM accounts WHERE user_id IN ({id_ph})", ids)
    # loans/loan_events do have real FK cascades from users, but deleted
    # explicitly here too for clarity.
    cur.execute(f"DELETE FROM loans WHERE user_id IN ({id_ph})", ids)
    cur.execute(f"DELETE FROM users WHERE id IN ({id_ph})", ids)
    conn.commit()

    cur.execute(f"SELECT COUNT(*) FROM users WHERE username IN ({placeholders})", VICTIM_USERNAMES)
    remaining = cur.fetchone()[0]
    print(f"  Confirmed: {remaining} victim account(s) remain after delete (should be 0).")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    reset = '--reset' in sys.argv

    conn = mysql.connector.connect(**DB)
    cur = conn.cursor()

    placeholders = ','.join(['%s'] * len(VICTIM_USERNAMES))
    cur.execute(f"SELECT COUNT(*) FROM users WHERE username IN ({placeholders})", VICTIM_USERNAMES)
    existing = cur.fetchone()[0]

    if existing > 0:
        if reset:
            reset_victims(cur, conn)
        else:
            print(f"  Warning: {existing} victim account(s) already exist.")
            print("  Run with --reset to wipe and re-seed. Aborting.")
            cur.close()
            conn.close()
            sys.exit(0)

    total_accounts = 0
    for victim in VICTIMS:
        rng = random.Random(victim['username'])  # deterministic per victim
        print(f"Seeding {victim['username']} …")

        user_id = get_or_create_user(cur, victim['username'], victim['email'], victim['password'])
        conn.commit()

        acc_ids = {}
        for key, (name, acc_type, include_in_budget) in victim['accounts'].items():
            acc_ids[key] = get_or_create_account(cur, user_id, name, acc_type, include_in_budget)
        conn.commit()
        total_accounts += len(acc_ids)

        primary_acc = acc_ids[victim['primary']]

        for month in MONTHS:
            last_day = calendar.monthrange(month.year, month.month)[1]
            label = month.strftime('%B %Y')

            for cat_name, base_amt, day, jitter in victim['income']:
                cid = get_category_id(cur, cat_name, 'income')
                amt = base_amt + (rng.uniform(-jitter, jitter) if jitter else 0)
                d = date(month.year, month.month, min(day, last_day))
                insert_tx(cur, user_id, primary_acc, cid, 'income', amt, f'{cat_name} — {label}', d)

            for cat_name, base_amt, day, jitter in victim['expenses']:
                cid = get_category_id(cur, cat_name, 'expense')
                amt = base_amt + (rng.uniform(-jitter, jitter) if jitter else 0)
                d = date(month.year, month.month, min(day, last_day))
                insert_tx(cur, user_id, primary_acc, cid, 'expense', amt, f'{cat_name} — {label}', d)

            for from_key, to_key, amt, day in victim['transfers']:
                d = date(month.year, month.month, min(day, last_day))
                insert_transfer(cur, user_id, acc_ids[from_key], acc_ids[to_key], amt,
                                 f'Transfer — {label}', d)

        conn.commit()

        if victim['budget']:
            insert_budget(cur, user_id, victim['budget'])
            conn.commit()

        if victim['savings_goal']:
            g = victim['savings_goal']
            insert_savings_goal(cur, user_id, acc_ids[g['account']], g)
            conn.commit()

        if victim['loan']:
            insert_loan(cur, user_id, victim['loan'])
            conn.commit()

        recalc_balances(cur, list(acc_ids.values()))
        conn.commit()

    print(f"\nDone. {len(VICTIMS)} victims seeded, {total_accounts} accounts total.")
    print("Refresh http://localhost:5001")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
