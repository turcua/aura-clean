#!/usr/bin/env python3
"""
Aura CTF Reset Script — Sprint 45 (Release 9, "Shattered Veil")
Standalone script — returns vulnerable-version to a fresh-deploy state
between CTF sessions: deletes every user except `testuser` and `admin`
(the two baseline seeded accounts, see database/init-vulnerable.sql) and
all their data, then cleans up any rows left orphaned by mass-assignment/
IDOR writes under a user_id that was never a real user in the first place.

This removes seeded CTF victims (see seed_ctf_victims.py) AND anything a
hacker created live during a session (decoy registrations, IDOR-written
rows) in one pass. testuser/admin and their data are never touched, and
global default categories (user_id IS NULL) are never touched either.

Prerequisites:
    pip install mysql-connector-python
    Docker containers running: docker compose up -d

Usage:
    python3 reset_ctf.py
"""

import mysql.connector

DB = dict(
    host='127.0.0.1',
    port=3307,
    user='aura_user',
    password='VulnUserPass123!',
    database='aura_vulnerable',
)

PRESERVE_USERNAMES = ['testuser', 'admin']

# Tables with a user_id column but NO real FOREIGN KEY to users(id) — the
# vulnerable schema's intentional design (see database/init-vulnerable*.sql
# comments, e.g. "VULN: No FOREIGN KEY on user_id"). A user delete never
# cascades into these; they need explicit handling both for the "known
# users being removed" pass and the "orphaned under a fake user_id" pass.
NO_FK_TABLES = ['transactions', 'accounts', 'recurring_transactions',
                 'transfers', 'savings_goals', 'user_sessions']

# Tables WITH a real FOREIGN KEY ... ON DELETE CASCADE to users(id) — a user
# delete cleans these up automatically: loans (+ loan_events via loan_id
# cascade), ai_conversations, notifications, dashboards (+ dashboard_widgets
# via dashboard_id cascade), scoreboard_progress. They also can't be
# orphaned under a fake user_id in the first place, since the FK rejects
# the insert outright — no cleanup pass needed for any of them.


def delete_for_users(cur, user_ids):
    """Deletes every row owned by the given (real, about-to-be-removed)
    user ids, across every no-FK table, then the user rows themselves."""
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

    # Never touch global default categories (user_id IS NULL).
    cur.execute(f"DELETE FROM categories WHERE user_id IS NOT NULL AND user_id IN ({ph})", user_ids)

    cur.execute(f"DELETE FROM users WHERE id IN ({ph})", user_ids)


def delete_orphans(cur):
    """Second pass: rows under a user_id that was never a real user at all
    (e.g. a mass-assignment write with a fabricated id) — these can't be
    caught by delete_for_users() since there was never a matching users
    row to select in the first place. Known edge case, documented in
    docs/sprints/sprint-45-plan.md scope decision 3."""
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


def main():
    conn = mysql.connector.connect(**DB)
    cur = conn.cursor()

    ph = ','.join(['%s'] * len(PRESERVE_USERNAMES))
    cur.execute(f"SELECT id FROM users WHERE username NOT IN ({ph})", PRESERVE_USERNAMES)
    to_remove = [r[0] for r in cur.fetchall()]

    print(f"Removing {len(to_remove)} user(s) (everything except {', '.join(PRESERVE_USERNAMES)}) …")
    delete_for_users(cur, to_remove)
    conn.commit()

    print("Cleaning up orphaned rows under nonexistent user_ids …")
    orphan_counts = delete_orphans(cur)
    conn.commit()
    any_orphans = False
    for table, n in orphan_counts.items():
        if n:
            any_orphans = True
            print(f"  {table}: removed {n} orphaned row(s)")
    if not any_orphans:
        print("  none found")

    cur.execute("SELECT username FROM users ORDER BY username")
    remaining = [r[0] for r in cur.fetchall()]
    print(f"\nDone. Remaining users: {', '.join(remaining)}")

    cur.execute("SELECT COUNT(*) FROM categories WHERE user_id IS NULL")
    print(f"Global default categories intact: {cur.fetchone()[0]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
