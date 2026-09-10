"""
Aura Financial Tracker - Vulnerable Version
Scoreboard API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 42: Sound Breathing - Constant Resounding Slashes
VULNERABILITY (VULN-082): No ownership check — user_id comes from the
request body/query string on every endpoint, never the session, matching
every other IDOR-style finding in this app. /mark and /unmark also carry
SQL Injection in the model layer (see models/scoreboard_progress.py).
Deliberate: the scoreboard's own tracking mechanism is exploitable in
character, the same as everything it catalogs (Sprint 42 scope decision 5).
"""

from flask import Blueprint, jsonify, request, current_app, session

from models.scoreboard_progress import ScoreboardProgress
from utils import flag_engine
from utils.challenge_catalog import CHALLENGES

_CATALOG_BY_ID = {c['vuln_id']: c for c in CHALLENGES}

api_scoreboard_bp = Blueprint('api_scoreboard', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_scoreboard_bp.route('/mark', methods=['POST'])
def mark_found():
    """VULN-082: user_id taken from the request body — anyone can mark a
    finding as found for any user, including one that isn't theirs."""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    vuln_id = data.get('vuln_id')
    if not user_id or not vuln_id:
        return jsonify({'success': False, 'message': 'user_id and vuln_id are required'}), 400

    success, message = ScoreboardProgress.mark(get_mysql(), user_id, vuln_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 400)


@api_scoreboard_bp.route('/unmark', methods=['POST'])
def unmark_found():
    """VULN-082: same missing ownership check as /mark."""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    vuln_id = data.get('vuln_id')
    if not user_id or not vuln_id:
        return jsonify({'success': False, 'message': 'user_id and vuln_id are required'}), 400

    success, message = ScoreboardProgress.unmark(get_mysql(), user_id, vuln_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 400)


@api_scoreboard_bp.route('/progress', methods=['GET'])
def get_progress():
    """VULN-082: user_id from the query string — any user's real progress
    is readable by anyone who guesses/enumerates their id."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400

    progress = ScoreboardProgress.get_by_user(get_mysql(), user_id)
    return jsonify({'success': True, 'progress': progress}), 200


@api_scoreboard_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Public by design (Sprint 42 scope decision 4) — no auth required."""
    leaderboard = ScoreboardProgress.get_leaderboard(get_mysql())
    return jsonify({'success': True, 'leaderboard': leaderboard}), 200


# ── Sprint 43: real flag mechanism. These four endpoints, unlike the four
# above, are deliberately NOT part of VULN-082's exploitable surface — they
# use the real session (never a request-supplied user_id) and parameterized
# queries throughout, because the CTF's own scoring has to be trustworthy
# even though everything else in this app isn't. ───────────────────────────

@api_scoreboard_bp.route('/flags', methods=['GET'])
def get_my_flags():
    """What the logged-in visitor has actually earned, flag values included
    (gated on CTF mode). Requires real login — this is the safe counterpart
    to /progress, which is intentionally open to anyone (VULN-082)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    mysql = get_mysql()
    ctf_mode = flag_engine.get_mode(mysql) == 'ctf'
    flags = ScoreboardProgress.get_my_flags(mysql, user_id)
    for f in flags:
        if not ctf_mode:
            f['flag_value'] = None
        catalog_entry = _CATALOG_BY_ID.get(f['vuln_id'])
        f['name'] = catalog_entry['name'] if catalog_entry else None
    return jsonify({'success': True, 'ctf_mode': ctf_mode, 'flags': flags}), 200


@api_scoreboard_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Solved findings the popup hasn't announced to this account yet —
    server-side truth, so it behaves the same regardless of browser/
    incognito/device (bug found via real testing, 2026-08-08: the original
    popup tracked 'already shown' in localStorage, which reset on every
    fresh browser context and re-announced everything already earned)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    mysql = get_mysql()
    ctf_mode = flag_engine.get_mode(mysql) == 'ctf'
    pending = ScoreboardProgress.get_unnotified(mysql, user_id)
    for f in pending:
        if not ctf_mode:
            f['flag_value'] = None
        catalog_entry = _CATALOG_BY_ID.get(f['vuln_id'])
        f['name'] = catalog_entry['name'] if catalog_entry else None
    return jsonify({'success': True, 'ctf_mode': ctf_mode, 'notifications': pending}), 200


@api_scoreboard_bp.route('/notifications/ack', methods=['POST'])
def ack_notification():
    """Marks one finding as announced — called right after the popup
    actually shows it, so it never re-appears on this or any other
    browser/device for the same account."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    data = request.get_json(silent=True) or {}
    vuln_id = data.get('vuln_id')
    if not vuln_id:
        return jsonify({'success': False, 'message': 'vuln_id is required'}), 400

    success = ScoreboardProgress.mark_notified(get_mysql(), user_id, vuln_id)
    return jsonify({'success': success}), (200 if success else 400)


@api_scoreboard_bp.route('/submit', methods=['POST'])
def submit_flag():
    """Manual fallback for exploitation done outside a live browser session
    (curl/Burp/scripts) — a flag can't auto-credit anyone if there was no
    session to credit at the moment it was generated. Validates the pasted
    value against any flag this app has ever actually issued, then credits
    the *submitter's own* session — never a request-supplied user_id."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    data = request.get_json(silent=True) or {}
    flag_value = (data.get('flag') or '').strip()
    if not flag_value:
        return jsonify({'success': False, 'message': 'flag is required'}), 400

    mysql = get_mysql()
    vuln_id = ScoreboardProgress.find_by_flag_value(mysql, flag_value)
    if not vuln_id:
        return jsonify({'success': False, 'message': 'Unrecognized flag'}), 400

    ScoreboardProgress.credit_flag(mysql, user_id, vuln_id, flag_value)
    return jsonify({'success': True, 'message': f'Flag accepted for {vuln_id}', 'vuln_id': vuln_id}), 200


@api_scoreboard_bp.route('/mode', methods=['GET'])
def get_mode():
    """Public — a hacker should be able to tell whether they're in an
    organized CTF session before deciding whether to expect real flags."""
    return jsonify({'success': True, 'mode': flag_engine.get_mode(get_mysql())}), 200


@api_scoreboard_bp.route('/mode', methods=['POST'])
def set_mode():
    """Organizer-controlled global toggle. Unauthenticated/unchecked here,
    same as this app's other admin-style surfaces (VULN-002) — not a new
    VULN-ID, just consistent with the app's existing convention."""
    data = request.get_json(silent=True) or {}
    mode = data.get('mode')
    success = flag_engine.set_mode(get_mysql(), mode)
    return jsonify({'success': success, 'mode': mode if success else None}), (200 if success else 400)


@api_scoreboard_bp.route('/xss-capture', methods=['POST'])
def xss_capture():
    """Proof-of-execution endpoint for stored/reflected XSS findings
    (VULN-009, VULN-025 in the Sprint 43 proving set). A payload that
    actually executes as JS can read window.__auraCanary (base.html) and
    POST it here; a passive HTML injection without real script execution
    never could. vuln_id is self-declared by the payload — a hacker who
    proves execution on one XSS finding could technically claim credit on
    another sharing this same mechanism without separately proving it.
    Documented limitation, not fixed this sprint."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    data = request.get_json(silent=True) or {}
    vuln_id = data.get('vuln_id')
    canary = data.get('canary')
    if not vuln_id or not canary:
        return jsonify({'success': False, 'message': 'vuln_id and canary are required'}), 400

    if canary != session.get('xss_canary'):
        return jsonify({'success': False, 'message': 'Canary mismatch'}), 400

    flag = flag_engine.mark_solved_with_flag(get_mysql(), user_id, vuln_id)
    revealed = flag_engine.reveal_if_ctf_mode(get_mysql(), flag)
    return jsonify({'success': True, 'message': 'Execution proven', 'flag': revealed}), 200
