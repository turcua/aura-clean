"""
Aura Financial Tracker - Vulnerable Version
CTF Organizer Control Panel API (Sprint 46)

Like utils/flag_engine.py, this is CTF scoring/operator infrastructure, not
one of the app's intentional vulnerabilities — genuinely correct,
parameterized queries throughout. Unauthenticated by design, same
convention already established for /api/scoreboard/mode (Sprint 43):
"organizer-controlled ... same as this app's other admin-style surfaces
(VULN-002)" — the page's hidden URL is the real protection, matching
/scoreboard's own precedent.
"""

from flask import Blueprint, jsonify, request, current_app

from utils import flag_engine, ctf_ops
from utils.challenge_catalog import CHALLENGES

api_ctf_admin_bp = Blueprint('api_ctf_admin', __name__)

_CATALOG_BY_ID = {c['vuln_id']: c for c in CHALLENGES}


def get_mysql():
    return current_app.extensions['mysql']


@api_ctf_admin_bp.route('/seed', methods=['POST'])
def seed():
    try:
        success, message, details = ctf_ops.seed_victims(get_mysql())
        return jsonify({'success': success, 'message': message, 'details': details}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_ctf_admin_bp.route('/reset', methods=['POST'])
def reset():
    try:
        success, message, details = ctf_ops.reset_ctf(get_mysql())
        return jsonify({'success': success, 'message': message, 'details': details}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_ctf_admin_bp.route('/mode', methods=['GET'])
def get_mode():
    return jsonify({'success': True, 'mode': flag_engine.get_mode(get_mysql())}), 200


@api_ctf_admin_bp.route('/mode', methods=['POST'])
def set_mode():
    data = request.get_json(silent=True) or {}
    mode = data.get('mode')
    mysql = get_mysql()
    success = flag_engine.set_mode(mysql, mode)
    return jsonify({'success': success, 'mode': mode if success else None}), (200 if success else 400)


@api_ctf_admin_bp.route('/flag-prefix', methods=['GET'])
def get_flag_prefix():
    return jsonify({'success': True, 'prefix': flag_engine.get_flag_prefix(get_mysql())}), 200


@api_ctf_admin_bp.route('/flag-prefix', methods=['POST'])
def set_flag_prefix():
    data = request.get_json(silent=True) or {}
    prefix = data.get('prefix')
    mysql = get_mysql()
    success = flag_engine.set_flag_prefix(mysql, prefix)
    return jsonify({
        'success': success,
        'prefix': flag_engine.get_flag_prefix(mysql) if success else None,
        'message': None if success else 'Prefix must be 1-20 alphanumeric characters',
    }), (200 if success else 400)


@api_ctf_admin_bp.route('/flags-audit', methods=['GET'])
def flags_audit():
    """Every flag ever issued — organizer reference/scoring. Safe,
    parameterized — distinct from VULN-082's own exploitable /progress."""
    mysql = get_mysql()
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT u.username, sp.vuln_id, sp.flag_value, sp.found_at "
            "FROM scoreboard_progress sp "
            "JOIN users u ON u.id = sp.user_id "
            "WHERE sp.source = 'flag' AND sp.flag_value IS NOT NULL "
            "ORDER BY sp.found_at DESC"
        )
        rows = cursor.fetchall()
        cursor.close()
        flags = []
        for username, vuln_id, flag_value, found_at in rows:
            catalog_entry = _CATALOG_BY_ID.get(vuln_id)
            flags.append({
                'username': username,
                'vuln_id': vuln_id,
                'name': catalog_entry['name'] if catalog_entry else None,
                'flag_value': flag_value,
                'found_at': str(found_at) if found_at else None,
            })
        return jsonify({'success': True, 'flags': flags}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
