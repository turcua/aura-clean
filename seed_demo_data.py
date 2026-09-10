#!/usr/bin/env python3
"""
Aura Demo Data Seeder — synthetic, both versions
Sprint 20: generates 24 months of randomized transaction data for testuser,
across aura_secure and/or aura_vulnerable, so the Spending Trend/Anomalies
and Year-over-Year Comparison widgets have enough month-over-month and
year-over-year variance to be visually meaningful.

Unlike seed_financial_data.py (real personal data, vulnerable-only,
gitignored), this is fully synthetic/randomized and safe to keep in the
repo — no privacy concern.

The most recent month deliberately spikes a couple of categories (see
ANOMALY_SPIKE_CATEGORIES) so the anomaly detector has something to flag on
first look, and each category has its own year-over-year growth factor
(YOY_GROWTH) so the comparison widget shows a mix of categories up and
down rather than a flat line.

Prerequisites:
    pip install mysql-connector-python bcrypt
    Docker containers running: docker compose up -d

Usage:
    python3 seed_demo_data.py                          # seed testuser on both versions
    python3 seed_demo_data.py --user alice              # seed 'alice', creating it if it doesn't exist
    python3 seed_demo_data.py --target secure            # secure only
    python3 seed_demo_data.py --target vulnerable         # vulnerable only
    python3 seed_demo_data.py --reset                     # wipe this user's transactions first

If --user doesn't exist yet in a target database, it's created — secure
gets a real bcrypt hash (same scheme as User.hash_password), vulnerable
gets the plaintext password stored directly in its `password` column,
matching how each app actually stores credentials (VULN-001 for
vulnerable). Default password is DemoPass123! unless --password is given.
"""

import argparse
import calendar
import random
from datetime import date

import bcrypt
import mysql.connector

DB_CONFIGS = {
    'secure': dict(host='127.0.0.1', port=3306, user='aura_user',
                   password='SecureUserPass123!', database='aura_secure'),
    'vulnerable': dict(host='127.0.0.1', port=3307, user='aura_user',
                        password='VulnUserPass123!', database='aura_vulnerable'),
}

MONTHS_BACK = 24

# (name, type, color, base_monthly_amount, volatility 0-1)
CATEGORIES = [
    ('Salary',        'income',  '#28a745', 6500,  0.05),
    ('Freelance',     'income',  '#20c997', 800,   0.60),
    ('Groceries',     'expense', '#e74c3c', 900,   0.15),
    ('Dining Out',    'expense', '#e67e22', 350,   0.35),
    ('Transport',     'expense', '#3498db', 300,   0.25),
    ('Utilities',     'expense', '#9b59b6', 450,   0.10),
    ('Entertainment', 'expense', '#1abc9c', 200,   0.40),
    ('Shopping',      'expense', '#2980b9', 400,   0.50),
    ('Healthcare',    'expense', '#2ecc71', 150,   0.70),
    ('Subscriptions', 'expense', '#95a5a6', 120,   0.10),
    ('Rent',          'expense', '#c0392b', 1800,  0.02),
    ('Travel',        'expense', '#f39c12', 250,   0.90),
]

# Deliberately spiked in the most recent month, to guarantee the Spending
# Trend widget's anomaly detector (>=30% above 3-month average) has
# something to show on first look.
ANOMALY_SPIKE_CATEGORIES = ['Shopping', 'Dining Out']
ANOMALY_SPIKE_MULTIPLIER = 1.8

# Per-category growth ramped in linearly across the 24-month window, so
# "this year" vs "last year" (YoY Comparison widget) shows a mix of
# categories that grew and shrank, not a uniform trend.
YOY_GROWTH = {
    'Groceries': 1.15, 'Dining Out': 1.30, 'Transport': 0.90, 'Utilities': 1.05,
    'Entertainment': 0.80, 'Shopping': 1.45, 'Healthcare': 1.10,
    'Subscriptions': 1.20, 'Rent': 1.08, 'Travel': 0.60,
    'Salary': 1.12, 'Freelance': 0.85,
}


def month_amount(base, volatility, month_index, total_months, category_name):
    """month_index: 0 = oldest month, total_months-1 = most recent month."""
    growth = YOY_GROWTH.get(category_name, 1.0)
    progress = month_index / max(total_months - 1, 1)
    factor = 1.0 + (growth - 1.0) * progress
    amount = base * factor * random.uniform(1 - volatility, 1 + volatility)
    return max(round(amount, 2), 0)


def get_or_create_user(cur, target, username, email, password):
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        return row[0], False

    if target == 'secure':
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_active, failed_login_attempts) "
            "VALUES (%s, %s, %s, TRUE, 0)",
            (username, email, password_hash)
        )
    else:
        # VULN-001: vulnerable-version stores passwords in plaintext — matched
        # here deliberately so a seeded user behaves identically to one
        # created through the app's own (also-plaintext) registration flow.
        cur.execute(
            "INSERT INTO users (username, email, password, is_active) VALUES (%s, %s, %s, TRUE)",
            (username, email, password)
        )
    return cur.lastrowid, True


def get_or_create_category(cur, user_id, name, cat_type, color):
    cur.execute("SELECT id FROM categories WHERE user_id = %s AND name = %s AND type = %s",
                (user_id, name, cat_type))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM categories WHERE user_id IS NULL AND name = %s AND type = %s",
                (name, cat_type))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO categories (user_id, name, type, color) VALUES (%s, %s, %s, %s)",
                (user_id, name, cat_type, color))
    return cur.lastrowid


def get_or_create_account(cur, user_id, name, acc_type, description):
    cur.execute("SELECT id FROM accounts WHERE user_id = %s AND name = %s", (user_id, name))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO accounts (user_id, name, type, initial_balance, current_balance, include_in_budget, description) "
        "VALUES (%s, %s, %s, 0, 0, 1, %s)",
        (user_id, name, acc_type, description)
    )
    return cur.lastrowid


def insert_tx(cur, user_id, account_id, category_id, tx_type, amount, description, tx_date):
    if not amount or amount <= 0:
        return None
    cur.execute(
        "INSERT INTO transactions (user_id, account_id, category_id, type, amount, description, transaction_date, is_transfer) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)",
        (user_id, account_id, category_id, tx_type, round(float(amount), 2), description, tx_date)
    )
    return cur.lastrowid


def recalc_balance(cur, account_id):
    cur.execute(
        "SELECT a.initial_balance + COALESCE(SUM(CASE WHEN t.type='income' THEN t.amount ELSE -t.amount END), 0) "
        "FROM accounts a LEFT JOIN transactions t ON t.account_id = a.id WHERE a.id = %s",
        (account_id,)
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        cur.execute("UPDATE accounts SET current_balance = %s WHERE id = %s", (float(row[0]), account_id))


def seed(target, reset, username, email, password):
    print(f"\n=== Seeding {target} ===")
    conn = mysql.connector.connect(**DB_CONFIGS[target])
    cur = conn.cursor()

    user_id, created = get_or_create_user(cur, target, username, email, password)
    conn.commit()
    if created:
        print(f"  User '{username}' didn't exist — created (id={user_id}).")

    cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id = %s", (user_id,))
    existing = cur.fetchone()[0]
    if existing > 0:
        if reset:
            print(f"  Resetting — deleting {existing} existing transactions for '{username}' …")
            cur.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
            conn.commit()
        else:
            print(f"  {existing} transactions already exist for '{username}'. "
                  f"Run with --reset to wipe and re-seed. Skipping.")
            cur.close()
            conn.close()
            return

    cat = {}
    for name, cat_type, color, _, _ in CATEGORIES:
        cat[(name, cat_type)] = get_or_create_category(cur, user_id, name, cat_type, color)
    conn.commit()

    acc_id = get_or_create_account(cur, user_id, 'Demo Checking', 'checking',
                                    'Synthetic demo data (Sprint 20 testing)')
    conn.commit()

    today = date.today()
    total = 0
    for i in range(MONTHS_BACK):
        months_ago = MONTHS_BACK - 1 - i
        year, month = today.year, today.month - months_ago
        while month <= 0:
            month += 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        is_current_month = (months_ago == 0)

        for name, cat_type, color, base, vol in CATEGORIES:
            amount = month_amount(base, vol, i, MONTHS_BACK, name)
            if is_current_month and name in ANOMALY_SPIKE_CATEGORIES and cat_type == 'expense':
                amount = round(amount * ANOMALY_SPIKE_MULTIPLIER, 2)
            tx_date = date(year, month, random.randint(1, last_day))
            tx_id = insert_tx(cur, user_id, acc_id, cat[(name, cat_type)], cat_type, amount,
                               f"{name} — {year}-{month:02d}", tx_date)
            if tx_id:
                total += 1
        conn.commit()

    recalc_balance(cur, acc_id)
    conn.commit()

    print(f"  {total} transactions inserted across {MONTHS_BACK} months for '{username}' (id={user_id}).")
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=['secure', 'vulnerable', 'both'], default='both')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--user', default='testuser', help="Username to seed (created if it doesn't exist)")
    parser.add_argument('--email', default=None, help="Email for a newly-created user (default: <user>@example.com)")
    parser.add_argument('--password', default='DemoPass123!', help="Password for a newly-created user")
    args = parser.parse_args()

    email = args.email or f"{args.user}@example.com"

    for t in (['secure', 'vulnerable'] if args.target == 'both' else [args.target]):
        seed(t, args.reset, args.user, email, args.password)

    print("\nDone. Refresh http://localhost:5000 (secure) / http://localhost:5001 (vulnerable)")


if __name__ == '__main__':
    main()
