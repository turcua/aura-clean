"""
Aura Financial Tracker - Vulnerable Version
Flag Engine
Sprint 43: Sound Breathing - Rapid Fire Slice

This module is the CTF's own scoring infrastructure, not one of the app's
intentional vulnerabilities — unlike models/scoreboard_progress.py (VULN-082,
deliberately IDOR+SQLi vulnerable), everything here uses parameterized
queries and is meant to be genuinely correct. flag_value is only ever
written from here, server-side, triggered by a vulnerability's own leak
actually firing — never accepted directly from a request body.

Flags are random, not derived: Aura{<24 random alphanumeric chars>},
generated the first time a given (user_id, vuln_id) pair is genuinely
triggered, then reused for that pair from then on.
"""

import random
import string

DEFAULT_FLAG_PREFIX = 'Aura'
MAX_PREFIX_LEN = 20  # keeps flag_value comfortably within scoreboard_progress's VARCHAR(64)


def get_flag_prefix(mysql):
    """Sprint 46: organizer-customizable via /ctf-admin, stored as a key in
    the same ctf_settings table Sprint 43's mode toggle already uses — no
    schema change needed."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT setting_value FROM ctf_settings WHERE setting_key = 'flag_prefix'")
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else DEFAULT_FLAG_PREFIX
    except Exception:
        return DEFAULT_FLAG_PREFIX


def set_flag_prefix(mysql, prefix):
    """Only affects flags generated after this call — already-issued flags
    keep their original value (they're generated once, then stored and
    reused, per Sprint 43's design)."""
    prefix = (prefix or '').strip()
    if not prefix or len(prefix) > MAX_PREFIX_LEN or not prefix.isalnum():
        return False
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO ctf_settings (setting_key, setting_value) VALUES ('flag_prefix', %s) "
            "ON DUPLICATE KEY UPDATE setting_value = %s",
            (prefix, prefix)
        )
        mysql.connection.commit()
        cursor.close()
        return True
    except Exception:
        return False


def _random_flag(prefix=DEFAULT_FLAG_PREFIX):
    body = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    return f"{prefix}{{{body}}}"


def get_or_create_flag(mysql, user_id, vuln_id):
    """Lazily generates and stores a flag the first time (user_id, vuln_id)
    is triggered; returns the same value on every subsequent call for that
    pair. Also marks the pair solved (source='flag') as a side effect —
    that's the whole point: the caller only calls this when it already
    knows a real leak just fired."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT flag_value FROM scoreboard_progress WHERE user_id = %s AND vuln_id = %s",
            (user_id, vuln_id)
        )
        row = cursor.fetchone()
        if row and row[0]:
            cursor.close()
            return row[0]

        flag = _random_flag(get_flag_prefix(mysql))
        cursor.execute(
            "INSERT INTO scoreboard_progress (user_id, vuln_id, source, flag_value) "
            "VALUES (%s, %s, 'flag', %s) "
            "ON DUPLICATE KEY UPDATE flag_value = VALUES(flag_value), source = 'flag'",
            (user_id, vuln_id, flag)
        )
        mysql.connection.commit()
        cursor.close()
        return flag
    except Exception:
        return None


def plant_secret(mysql):
    """A fresh flag value that ISN'T persisted or credited yet — for cases
    where the flag has to be embedded in something first (e.g. an AI
    system prompt) and only counts once it's actually observed leaking
    back out. Pair with credit_exact_flag() once that's confirmed."""
    return _random_flag(get_flag_prefix(mysql))


def credit_exact_flag(mysql, user_id, vuln_id, flag_value):
    """Like mark_solved_with_flag, but credits a specific already-known
    value instead of generating a new one — used where the flag must match
    something planted earlier in the same request (plant_secret above)."""
    if not user_id or not flag_value:
        return None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO scoreboard_progress (user_id, vuln_id, source, flag_value) "
            "VALUES (%s, %s, 'flag', %s) "
            "ON DUPLICATE KEY UPDATE flag_value = VALUES(flag_value), source = 'flag'",
            (user_id, vuln_id, flag_value)
        )
        mysql.connection.commit()
        cursor.close()
        return flag_value
    except Exception:
        mysql.connection.rollback()
        return None


def mark_solved_with_flag(mysql, user_id, vuln_id):
    """Call this from wherever a vulnerability's leak actually fires, with
    the id of whoever is being credited. Safe to call even with no user_id
    (anonymous exploitation, e.g. missing-auth findings hit pre-login) —
    returns None rather than crediting a session that doesn't exist."""
    if not user_id:
        return None
    return get_or_create_flag(mysql, user_id, vuln_id)


def get_mode(mysql):
    """'casual' (default, safe) or 'ctf'."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT setting_value FROM ctf_settings WHERE setting_key = 'mode'")
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else 'casual'
    except Exception:
        return 'casual'


def set_mode(mysql, mode):
    if mode not in ('casual', 'ctf'):
        return False
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO ctf_settings (setting_key, setting_value) VALUES ('mode', %s) "
            "ON DUPLICATE KEY UPDATE setting_value = %s",
            (mode, mode)
        )
        mysql.connection.commit()
        cursor.close()
        return True
    except Exception:
        return False


def reveal_if_ctf_mode(mysql, flag_value):
    """Gates flag *display* on the mode toggle — marking already happened
    unconditionally in mark_solved_with_flag(). Returns None in casual mode
    so callers can render a generic 'found!' instead of the flag text."""
    if flag_value and get_mode(mysql) == 'ctf':
        return flag_value
    return None
