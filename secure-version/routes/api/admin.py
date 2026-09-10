"""
Aura Financial Tracker - Secure Version
Admin API Routes
Sprint 57 (ENH-02): user management actions for the admin panel — promote/
demote admin, lock/unlock (activate/deactivate), delete, and force-expire
sessions. Every route here is gated by api_admin_required (routes/main.py),
not just api_login_required — these act on *other* users' accounts, so a
plain "logged in" check would make this a straightforward vertical
privilege-escalation hole for any regular user who found the endpoints.

Self-action guards: every route also blocks an admin from targeting their
own account (demoting/deactivating/deleting/session-expiring themselves) —
a common real-world admin-panel safeguard against an accidental,
hard-to-recover self-lockout (the only way back in at that point would be
a direct DB edit).
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, session, current_app
from models.user import User
from models.category import Category
from models.ai_conversation import AIConversation
from models.impersonation_log import ImpersonationLog
from routes.main import api_admin_required, api_login_required

api_admin_bp = Blueprint('api_admin', __name__)

# Sprint 57 (ENH-02, group 5): every job scheduler.py currently registers —
# kept here explicitly so a job that has genuinely never run yet (fresh
# migration, or the scheduler hasn't ticked since restart) still shows up
# as "Never run" rather than being silently omitted.
KNOWN_SCHEDULER_JOBS = [
    ('recurring_transaction_job', 'Recurring Transactions', 'Every hour'),
    ('notification_generation_job', 'Notification Generation', 'Every hour'),
    ('interest_accrual_job', 'Savings Interest Accrual', 'Every 24 hours'),
    ('ai_conversation_cleanup_job', 'AI Conversation Cleanup', 'Every 24 hours'),
    ('ai_insight_job', 'AI Insight Generation', 'Every 24 hours'),
]


def get_mysql():
    return current_app.extensions['mysql']


def _is_self(user_id):
    return int(user_id) == int(session['user_id'])


@api_admin_bp.route('/stats', methods=['GET'])
@api_admin_required
def get_stats():
    """
    Sprint 57 (ENH-02): system-wide counts for the admin panel's stats
    row. Plain counts, no per-user scoping (unlike every other query in
    this app) — deliberate, since this is the one page meant to see across
    all users at once. Direct queries here rather than new model methods,
    since these don't fit naturally on User (spans transactions too) or
    Transaction (would be the only system-wide, unscoped method on a model
    whose every other method takes a user_id).
    """
    mysql = get_mysql()
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= (NOW() - INTERVAL 30 DAY)")
        recent_signups = cursor.fetchone()[0]
        cursor.close()
        return jsonify({
            'success': True,
            'total_users': total_users,
            'total_transactions': total_transactions,
            'recent_signups': recent_signups,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_admin_bp.route('/users/<int:user_id>/set-admin', methods=['POST'])
@api_admin_required
def set_admin(user_id):
    if _is_self(user_id):
        return jsonify({'success': False, 'message': "You can't change your own admin status."}), 400

    mysql = get_mysql()
    users = {u[0]: u for u in User.get_all_users(mysql)}
    target = users.get(user_id)
    if not target:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    new_status = not bool(target[4])  # target[4] = is_admin, per get_all_users' column order
    success = User.set_admin_status(mysql, user_id, new_status)
    if not success:
        return jsonify({'success': False, 'message': 'Could not update admin status'}), 400
    return jsonify({'success': True, 'is_admin': new_status}), 200


@api_admin_bp.route('/users/<int:user_id>/set-active', methods=['POST'])
@api_admin_required
def set_active(user_id):
    if _is_self(user_id):
        return jsonify({'success': False, 'message': "You can't lock your own account."}), 400

    mysql = get_mysql()
    users = {u[0]: u for u in User.get_all_users(mysql)}
    target = users.get(user_id)
    if not target:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    new_status = not bool(target[5])  # target[5] = is_active, per get_all_users' column order
    success = User.set_active_status(mysql, user_id, new_status)
    if not success:
        return jsonify({'success': False, 'message': 'Could not update account status'}), 400
    return jsonify({'success': True, 'is_active': new_status}), 200


@api_admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@api_admin_required
def delete_user_route(user_id):
    if _is_self(user_id):
        return jsonify({'success': False, 'message': "You can't delete your own account."}), 400

    mysql = get_mysql()
    success = User.delete_user(mysql, user_id)
    if not success:
        return jsonify({'success': False, 'message': 'Could not delete user'}), 400
    return jsonify({'success': True}), 200


@api_admin_bp.route('/users/<int:user_id>/invalidate-sessions', methods=['POST'])
@api_admin_required
def invalidate_sessions(user_id):
    if _is_self(user_id):
        return jsonify({'success': False, 'message': "You can't force-expire your own session — just log out."}), 400

    mysql = get_mysql()
    success = User.invalidate_all_sessions(mysql, user_id)
    if not success:
        return jsonify({'success': False, 'message': 'Could not invalidate sessions'}), 400
    return jsonify({'success': True}), 200


# ── Shared/default category management (ENH-02 group 3) ─────────────────
# The one path in the app that can touch a default category (user_id IS
# NULL) at all — every other Category method scopes to `user_id = %s`,
# structurally excluding defaults by design (see models/category.py's own
# docstring). This is why ENH-08 (merging the "Salary"/"Salar" duplicate)
# had to be a raw one-off DB operation instead of a UI action; these
# endpoints close that gap for any future case like it.

@api_admin_bp.route('/categories', methods=['GET'])
@api_admin_required
def list_default_categories():
    mysql = get_mysql()
    categories = Category.get_all_defaults(mysql)

    # Usage count per category, across every user — not just a nice-to-have:
    # it's what lets the frontend warn accurately before a delete ("used by
    # N transactions across every user") instead of a generic "are you sure".
    cursor = mysql.connection.cursor()
    usage = {}
    for c in categories:
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category_id = %s", (c.id,))
        usage[c.id] = cursor.fetchone()[0]
    cursor.close()

    return jsonify({
        'success': True,
        'categories': [
            {'id': c.id, 'name': c.name, 'type': c.type, 'color': c.color, 'usage_count': usage[c.id]}
            for c in categories
        ],
    }), 200


@api_admin_bp.route('/categories/create', methods=['POST'])
@api_admin_required
def create_default_category():
    data = request.get_json() if request.is_json else request.form
    name = (data.get('name') or '').strip()
    type_ = data.get('type')
    color = data.get('color') or '#6c757d'

    if not name or type_ not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'A name and a valid type (income/expense) are required'}), 400

    mysql = get_mysql()
    success, message, category_id = Category.create_default(mysql, name, type_, color)
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    return jsonify({'success': True, 'message': message, 'category_id': category_id}), 201


@api_admin_bp.route('/categories/<int:category_id>/update', methods=['POST'])
@api_admin_required
def update_default_category(category_id):
    data = request.get_json() if request.is_json else request.form
    name = (data.get('name') or '').strip()
    type_ = data.get('type')
    color = data.get('color') or '#6c757d'

    if not name or type_ not in ('income', 'expense'):
        return jsonify({'success': False, 'message': 'A name and a valid type (income/expense) are required'}), 400

    mysql = get_mysql()
    success, message = Category.update_default(mysql, category_id, name, type_, color)
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    return jsonify({'success': True, 'message': message}), 200


@api_admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@api_admin_required
def delete_default_category(category_id):
    mysql = get_mysql()
    success, message = Category.delete_default(mysql, category_id)
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    return jsonify({'success': True, 'message': message}), 200


# ── AI advisor usage visibility (ENH-02 group 4) ─────────────────────────
# Message counts, not token counts — see models/ai_conversation.py's
# get_usage_stats() docstring for why: real token usage was never captured
# anywhere in this app, so there's no historical data to report, and this
# was an explicit user decision to ship now rather than add tracking that
# could only ever cover future messages.

@api_admin_bp.route('/scheduler-health', methods=['GET'])
@api_admin_required
def get_scheduler_health():
    """Sprint 57 (ENH-02, group 5): latest run per known job. Direct query
    here rather than a new model, matching this file's own /stats route —
    this is admin-panel-only, cross-cutting infrastructure visibility, not
    a concern any single model owns."""
    mysql = get_mysql()
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT job_id, run_at, status, result_count, error_message FROM scheduler_job_runs "
            "WHERE id IN (SELECT MAX(id) FROM scheduler_job_runs GROUP BY job_id)"
        )
        latest_by_job = {row[0]: row for row in cursor.fetchall()}
        cursor.close()
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

    jobs = []
    for job_id, label, schedule in KNOWN_SCHEDULER_JOBS:
        row = latest_by_job.get(job_id)
        if row:
            jobs.append({
                'job_id': job_id, 'label': label, 'schedule': schedule,
                'last_run': str(row[1]), 'status': row[2],
                'result_count': row[3], 'error_message': row[4],
            })
        else:
            jobs.append({
                'job_id': job_id, 'label': label, 'schedule': schedule,
                'last_run': None, 'status': None, 'result_count': None, 'error_message': None,
            })
    return jsonify({'success': True, 'jobs': jobs}), 200


@api_admin_bp.route('/ai-usage', methods=['GET'])
@api_admin_required
def get_ai_usage():
    mysql = get_mysql()
    rows = AIConversation.get_usage_stats(mysql)
    return jsonify({
        'success': True,
        'usage': [
            {
                'user_id': r[0], 'username': r[1], 'prompts_sent': r[2],
                'total_messages': r[3], 'last_activity': str(r[4]) if r[4] else None,
            }
            for r in rows
        ],
    }), 200


# ── "View As" / impersonate a user (ENH-02 group 6) ──────────────────────
# Full-access impersonation (explicit user decision, 2026-09-02): creates a
# real session for the target user via the same User.create_session() a
# normal login uses, so every existing login_required/api_login_required
# check keeps working transparently — the admin genuinely becomes that
# user for the duration, not a read-only view bolted on top. The original
# admin identity is stashed in session['impersonator_*'] keys so
# stop_impersonating() can restore it. Guardrails: can't impersonate
# yourself or another admin account, and can't impersonate a locked
# account. Every impersonation is logged (models/impersonation_log.py) —
# who, whom, when started, when ended.

@api_admin_bp.route('/users/<int:user_id>/impersonate', methods=['POST'])
@api_admin_required
def impersonate_user(user_id):
    if _is_self(user_id):
        return jsonify({'success': False, 'message': "You're already yourself."}), 400
    if 'impersonator_id' in session:
        return jsonify({'success': False, 'message': "You're already impersonating someone — return to admin first."}), 400

    mysql = get_mysql()
    users = {u[0]: u for u in User.get_all_users(mysql)}
    target = users.get(user_id)
    if not target:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    if bool(target[4]):  # target[4] = is_admin
        return jsonify({'success': False, 'message': "You can't impersonate another admin account."}), 400
    if not bool(target[5]):  # target[5] = is_active
        return jsonify({'success': False, 'message': "You can't impersonate a locked account."}), 400

    success, new_session_token = User.create_session(mysql, user_id, request.remote_addr, request.headers.get('User-Agent', ''))
    if not success:
        return jsonify({'success': False, 'message': 'Could not start impersonation session'}), 400

    log_id = ImpersonationLog.create(mysql, admin_id=session['user_id'], target_user_id=user_id)

    # Stash the real admin's identity, then swap the active session to the target.
    session['impersonator_id'] = session['user_id']
    session['impersonator_username'] = session['username']
    session['impersonator_session_token'] = session['session_token']
    session['impersonation_log_id'] = log_id

    session['user_id'] = user_id
    session['username'] = target[1]
    session['session_token'] = new_session_token
    session['is_admin'] = False  # never elevated in the impersonated view, even though the guard above already excludes admin targets
    session['ai_chat_since'] = datetime.utcnow().isoformat()

    return jsonify({'success': True}), 200


@api_admin_bp.route('/stop-impersonating', methods=['POST'])
@api_login_required
def stop_impersonating():
    # Not @api_admin_required — session['is_admin'] is False for the
    # duration of an impersonation by design, so that check would block
    # this route from ever being reachable. Presence of
    # session['impersonator_id'] is itself the authorization gate: it can
    # only ever be set by impersonate_user() above, which is already
    # admin-gated.
    if 'impersonator_id' not in session:
        return jsonify({'success': False, 'message': 'Not currently impersonating anyone'}), 400

    mysql = get_mysql()
    User.invalidate_session(mysql, session['session_token'])
    ImpersonationLog.mark_ended(mysql, session.get('impersonation_log_id'))

    session['user_id'] = session.pop('impersonator_id')
    session['username'] = session.pop('impersonator_username')
    session['session_token'] = session.pop('impersonator_session_token')
    session.pop('impersonation_log_id', None)
    session['is_admin'] = True
    session['ai_chat_since'] = datetime.utcnow().isoformat()

    return jsonify({'success': True}), 200


@api_admin_bp.route('/impersonation-log', methods=['GET'])
@api_admin_required
def get_impersonation_log():
    mysql = get_mysql()
    rows = ImpersonationLog.get_recent(mysql)
    return jsonify({
        'success': True,
        'events': [
            {
                'id': r[0], 'admin_username': r[1], 'target_username': r[2],
                'started_at': str(r[3]), 'ended_at': str(r[4]) if r[4] else None,
            }
            for r in rows
        ],
    }), 200
