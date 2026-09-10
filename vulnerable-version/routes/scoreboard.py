"""
Aura Financial Tracker - Vulnerable Version
Hidden Challenge Scoreboard (Sprint 41: Sound Breathing - String Performance)

Intentionally unlinked - no nav entry, no robots.txt reference. Findable only
via content-discovery/wordlist recon against /scoreboard, matching this
release's scope decision (docs/releases/release-09-plan.md).
"""

from flask import Blueprint, render_template
from itertools import groupby
from utils.challenge_catalog import CHALLENGES

scoreboard_bp = Blueprint('scoreboard', __name__)


@scoreboard_bp.route('/scoreboard')
def scoreboard():
    """
    Unauthenticated by design - a hunter finds this before any account
    exists. Self-report ("mark as found") is client-side only this sprint
    (localStorage); Sprint 42 replaces it with real per-user persistence.
    """
    ordered = sorted(CHALLENGES, key=lambda c: c['category'])
    grouped = [
        {'category': category, 'challenges': list(items)}
        for category, items in groupby(ordered, key=lambda c: c['category'])
    ]
    active_count = sum(1 for c in CHALLENGES if c['status'] == 'active')

    return render_template(
        'scoreboard.html',
        grouped_challenges=grouped,
        total_active=active_count,
    )
