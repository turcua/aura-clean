"""
Aura Financial Tracker - Vulnerable Version
CTF Operations — Seed / Reset (Sprint 46: CTF Organizer Control Panel)

Ported from the standalone seed_ctf_victims.py / reset_ctf.py scripts
(Sprint 45) into the app itself, so the organizer's /ctf-admin page can
trigger them directly against the app's own live DB connection instead of
shelling out to a CLI script. The two root-level scripts are left
untouched and still work independently for pre-session CLI use (Sprint 46
scope decision 3) — this module is a separate, parallel implementation,
not a shared import, to avoid any risk of touching what Sprint 45 already
tested successfully.

Same content as those scripts: victim data is entirely fabricated (no
connection to any real person's finances), and the reset logic uses the
exact same table-by-table FK/orphan handling already verified correct in
Sprint 45 (docs/sprints/sprint-45-plan.md).

Like utils/flag_engine.py, this module is meant to be genuinely correct —
parameterized queries throughout, not one of the app's intentional
vulnerabilities.
"""

import calendar
import random
from datetime import date

VICTIM_USERNAMES = ['emma', 'james', 'olivia', 'daniel', 'sophie']
PRESERVE_USERNAMES = ['testuser', 'admin']

# Tables with a user_id column but NO real FOREIGN KEY to users(id) — see
# reset_ctf.py's own comment for the full reasoning; verified table-by-table
# against database/init-vulnerable*.sql in Sprint 45.
NO_FK_TABLES = ['transactions', 'accounts', 'recurring_transactions',
                 'transfers', 'savings_goals', 'user_sessions']


def _month_back(today, n):
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return date(y, m, 1)


def _month_forward(today, n):
    y, m = today.year, today.month
    for _ in range(n):
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return date(y, m, 1)


def _build_victims(today):
    """Victim data built fresh against `today` on every call (not at import
    time), so seeded dates stay relative to whenever the organizer actually
    clicks Seed, even in a long-running app process."""
    months = [_month_back(today, 2), _month_back(today, 1), _month_back(today, 0)]
    current_month = months[-1]

    victims = [
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
                'name': f'{current_month.strftime("%B %Y")} Essentials',
                'total_limit': 3000,
                'category_limits': {'Food & Dining': 700, 'Transport': 200, 'Entertainment': 200},
            },
            'savings_goal': {
                'account': 'sav', 'name': 'New Car Fund',
                'target_amount': 40000, 'current_amount': 8400,
                'target_date': date(today.year + 2, 6, 30), 'monthly_target': 800,
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
                'name': f'{current_month.strftime("%B %Y")} Budget',
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
                'target_date': date(today.year + 1, 12, 31), 'monthly_target': 400,
                'status': 'active',
            },
            'loan': {
                'name': 'Home Mortgage',
                'principal': 250000.00,
                'margin_pct': 2.000,
                'initial_base_index_pct': 6.500,
                'start_date': date(today.year - 3, 3, 1),
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
                'target_date': date(today.year + 1, 6, 30), 'monthly_target': 500,
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
                'account': 'chk', 'name': 'Laptop Fund',
                'target_amount': 3000, 'current_amount': 3000,
                'target_date': _month_forward(today, 1), 'monthly_target': 100,
                'status': 'active',
            },
            'loan': None,
        },
    ]
    return months, current_month, victims


# ── Shared insert helpers ────────────────────────────────────────────────────

def _get_or_create_user(cur, username, email, password):
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
        (username, email, password),
    )
    return cur.lastrowid


def _get_category_id(cur, name, cat_type):
    cur.execute(
        "SELECT id FROM categories WHERE user_id IS NULL AND name = %s AND type = %s",
        (name, cat_type),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Global default category not found: {name} ({cat_type})")
    return row[0]


def _get_or_create_account(cur, user_id, name, acc_type, include_in_budget):
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


def _insert_tx(cur, user_id, account_id, category_id, tx_type, amount, description, tx_date,
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


def _insert_transfer(cur, user_id, from_acc, to_acc, amount, description, tx_date):
    if not amount or amount <= 0:
        return
    amt = round(float(amount), 2)
    from_tx = _insert_tx(cur, user_id, from_acc, None, 'expense', amt, description, tx_date, True)
    to_tx = _insert_tx(cur, user_id, to_acc, None, 'income', amt, description, tx_date, True)
    cur.execute(
        """INSERT INTO transfers
               (user_id, from_account_id, to_account_id,
                from_transaction_id, to_transaction_id,
                amount, description, transfer_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, from_acc, to_acc, from_tx, to_tx, amt, description, tx_date),
    )


def _insert_budget(cur, user_id, budget_cfg, current_month):
    last_day = calendar.monthrange(current_month.year, current_month.month)[1]
    end = date(current_month.year, current_month.month, last_day)
    cur.execute(
        """INSERT INTO budgets (user_id, name, period_type, start_date, end_date, total_limit, is_active)
           VALUES (%s, %s, 'monthly', %s, %s, %s, TRUE)""",
        (user_id, budget_cfg['name'], current_month, end, budget_cfg['total_limit']),
    )
    budget_id = cur.lastrowid
    for cat_name, limit in budget_cfg['category_limits'].items():
        cat_id = _get_category_id(cur, cat_name, 'expense')
        cur.execute(
            "INSERT INTO budget_categories (budget_id, category_id, limit_amount) VALUES (%s, %s, %s)",
            (budget_id, cat_id, limit),
        )


def _insert_savings_goal(cur, user_id, account_id, goal_cfg):
    cur.execute(
        """INSERT INTO savings_goals
               (user_id, account_id, name, target_amount, current_amount,
                target_date, monthly_target, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, account_id, goal_cfg['name'], goal_cfg['target_amount'],
         goal_cfg['current_amount'], goal_cfg['target_date'],
         goal_cfg['monthly_target'], goal_cfg['status']),
    )


def _insert_loan(cur, user_id, loan_cfg):
    cur.execute(
        """INSERT INTO loans
               (user_id, name, principal, margin_pct, initial_base_index_pct,
                start_date, original_term_months, currency, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')""",
        (user_id, loan_cfg['name'], loan_cfg['principal'], loan_cfg['margin_pct'],
         loan_cfg['initial_base_index_pct'], loan_cfg['start_date'],
         loan_cfg['original_term_months'], loan_cfg['currency']),
    )


def _recalc_balances(cur, account_ids):
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


def _delete_users_by_ids(cur, user_ids):
    """Deletes every row owned by the given (real) user ids, across every
    no-FK table, then the user rows themselves. Never touches global
    default categories (user_id IS NULL)."""
    if not user_ids:
        return
    ph = ','.join(['%s'] * len(user_ids))

    cur.execute(f"SELECT id FROM budgets WHERE user_id IN ({ph})", user_ids)
    budget_ids = [r[0] for r in cur.fetchall()]
    if budget_ids:
        bp = ','.join(['%s'] * len(budget_ids))
        cur.execute(f"DELETE FROM budget_categories WHERE budget_id IN ({bp})", budget_ids)

    for table in NO_FK_TABLES + ['budgets']:
        cur.execute(f"DELETE FROM {table} WHERE user_id IN ({ph})", user_ids)

    cur.execute(f"DELETE FROM categories WHERE user_id IS NOT NULL AND user_id IN ({ph})", user_ids)
    cur.execute(f"DELETE FROM users WHERE id IN ({ph})", user_ids)


def _delete_orphans(cur):
    """Rows under a user_id that was never a real user at all (e.g. a
    mass-assignment write with a fabricated id)."""
    counts = {}
    for table in NO_FK_TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id NOT IN (SELECT id FROM users)")
        counts[table] = cur.fetchone()[0]
        cur.execute(f"DELETE FROM {table} WHERE user_id NOT IN (SELECT id FROM users)")

    cur.execute(
        "SELECT COUNT(*) FROM categories WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)"
    )
    counts['categories'] = cur.fetchone()[0]
    cur.execute(
        "DELETE FROM categories WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)"
    )

    cur.execute("SELECT COUNT(*) FROM budgets WHERE user_id NOT IN (SELECT id FROM users)")
    counts['budgets'] = cur.fetchone()[0]
    cur.execute("DELETE FROM budgets WHERE user_id NOT IN (SELECT id FROM users)")

    cur.execute(
        "SELECT COUNT(*) FROM budget_categories WHERE budget_id NOT IN (SELECT id FROM budgets)"
    )
    counts['budget_categories'] = cur.fetchone()[0]
    cur.execute(
        "DELETE FROM budget_categories WHERE budget_id NOT IN (SELECT id FROM budgets)"
    )

    return counts


# ── Public entry points ──────────────────────────────────────────────────────

def seed_victims(mysql):
    """Always wipes any existing copies of the 5 named victims first, then
    reseeds fresh — a single button click should just produce a clean set,
    unlike the CLI script's --reset flag which needed an explicit choice."""
    cur = mysql.connection.cursor()
    today = date.today()
    months, current_month, victims = _build_victims(today)

    placeholders = ','.join(['%s'] * len(VICTIM_USERNAMES))
    cur.execute(f"SELECT id FROM users WHERE username IN ({placeholders})", VICTIM_USERNAMES)
    existing_ids = [r[0] for r in cur.fetchall()]
    if existing_ids:
        _delete_users_by_ids(cur, existing_ids)
        mysql.connection.commit()

    total_accounts = 0
    for victim in victims:
        rng = random.Random(victim['username'])  # deterministic per victim

        user_id = _get_or_create_user(cur, victim['username'], victim['email'], victim['password'])
        mysql.connection.commit()

        acc_ids = {}
        for key, (name, acc_type, include_in_budget) in victim['accounts'].items():
            acc_ids[key] = _get_or_create_account(cur, user_id, name, acc_type, include_in_budget)
        mysql.connection.commit()
        total_accounts += len(acc_ids)

        primary_acc = acc_ids[victim['primary']]

        for month in months:
            last_day = calendar.monthrange(month.year, month.month)[1]
            label = month.strftime('%B %Y')

            for cat_name, base_amt, day, jitter in victim['income']:
                cid = _get_category_id(cur, cat_name, 'income')
                amt = base_amt + (rng.uniform(-jitter, jitter) if jitter else 0)
                d = date(month.year, month.month, min(day, last_day))
                _insert_tx(cur, user_id, primary_acc, cid, 'income', amt, f'{cat_name} — {label}', d)

            for cat_name, base_amt, day, jitter in victim['expenses']:
                cid = _get_category_id(cur, cat_name, 'expense')
                amt = base_amt + (rng.uniform(-jitter, jitter) if jitter else 0)
                d = date(month.year, month.month, min(day, last_day))
                _insert_tx(cur, user_id, primary_acc, cid, 'expense', amt, f'{cat_name} — {label}', d)

            for from_key, to_key, amt, day in victim['transfers']:
                d = date(month.year, month.month, min(day, last_day))
                _insert_transfer(cur, user_id, acc_ids[from_key], acc_ids[to_key], amt,
                                  f'Transfer — {label}', d)

        mysql.connection.commit()

        if victim['budget']:
            _insert_budget(cur, user_id, victim['budget'], current_month)
            mysql.connection.commit()

        if victim['savings_goal']:
            g = victim['savings_goal']
            _insert_savings_goal(cur, user_id, acc_ids[g['account']], g)
            mysql.connection.commit()

        if victim['loan']:
            _insert_loan(cur, user_id, victim['loan'])
            mysql.connection.commit()

        _recalc_balances(cur, list(acc_ids.values()))
        mysql.connection.commit()

    cur.close()
    return True, f"Seeded {len(victims)} victims, {total_accounts} accounts total.", {
        'victims': len(victims),
        'accounts': total_accounts,
        'usernames': VICTIM_USERNAMES,
    }


def reset_ctf(mysql):
    """Removes every user except testuser/admin, plus a second pass for
    rows orphaned under a user_id that was never real at all."""
    cur = mysql.connection.cursor()

    ph = ','.join(['%s'] * len(PRESERVE_USERNAMES))
    cur.execute(f"SELECT id FROM users WHERE username NOT IN ({ph})", PRESERVE_USERNAMES)
    to_remove = [r[0] for r in cur.fetchall()]

    _delete_users_by_ids(cur, to_remove)
    mysql.connection.commit()

    orphan_counts = _delete_orphans(cur)
    mysql.connection.commit()

    cur.execute("SELECT username FROM users ORDER BY username")
    remaining = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM categories WHERE user_id IS NULL")
    default_cats = cur.fetchone()[0]

    cur.close()
    return True, f"Removed {len(to_remove)} user(s). Remaining: {', '.join(remaining)}.", {
        'removed_users': len(to_remove),
        'remaining_users': remaining,
        'orphans_removed': {k: v for k, v in orphan_counts.items() if v},
        'default_categories_intact': default_cats,
    }
