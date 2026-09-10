"""
Aura Financial Tracker - Vulnerable Version
CTF Organizer Control Panel (Sprint 46)

Intentionally unlinked - no nav entry, same "findable via a known URL, not
breadcrumb-leaked" precedent as routes/scoreboard.py. Deliberately kept
separate from VULN-002's /admin: that page is itself the vulnerability a
hacker is supposed to find, and mixing real operator controls (reset, mode
toggle) into it would let a player disrupt or reset a live session.
"""

from flask import Blueprint, render_template

ctf_admin_bp = Blueprint('ctf_admin', __name__)


@ctf_admin_bp.route('/ctf-admin')
def ctf_admin():
    return render_template('ctf_admin.html')
