"""
Aura Financial Tracker - Vulnerable Version
Loan API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 28: Loan Intelligence Foundation
VULNERABILITY (VULN-080): No auth, IDOR — user_id/loan_id from request,
f-string SQL throughout (in the model layer).
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request, current_app, session

from models.loan import Loan, LoanEvent
from utils.loan_engine import project, _add_month
from utils.chart_parser import extract_text, guess_chart_fields
from utils import flag_engine

api_loans_bp = Blueprint('api_loans', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_loans_bp.route('/create', methods=['POST'])
def create_loan():
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get('user_id')
        required = ['user_id', 'name', 'principal', 'margin_pct', 'initial_base_index_pct', 'start_date', 'original_term_months']
        if not all(data.get(f) not in (None, '') for f in required):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        mysql = get_mysql()
        success, message, loan_id = Loan.create(
            mysql, user_id, data['name'], data['principal'], data['margin_pct'],
            data['initial_base_index_pct'], data['start_date'], data['original_term_months'],
            data.get('currency', 'RON'),
        )
        return jsonify({'success': success, 'message': message, 'loan_id': loan_id}), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/list', methods=['GET'])
def list_loans():
    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required'}), 400
        mysql = get_mysql()
        loans = Loan.get_all_by_user(mysql, user_id)
        return jsonify({'success': True, 'loans': [_loan_to_dict(l) for l in loans]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>', methods=['GET'])
def get_loan(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all."""
    try:
        mysql = get_mysql()
        loan = Loan.get_by_id(mysql, loan_id)
        if not loan:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404

        # Sprint 44 (VULN-080 flag): genuinely reading someone else's loan
        # via the IDOR is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(loan.user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-080')

        return jsonify({'success': True, 'loan': _loan_to_dict(loan)}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/update', methods=['POST'])
def update_loan(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all. Sprint 51 (ENH-01)."""
    try:
        data = request.get_json() if request.is_json else request.form
        required = ['name', 'currency', 'margin_pct']
        if not all(data.get(f) not in (None, '') for f in required):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        mysql = get_mysql()
        success, message = Loan.update(mysql, loan_id, data['name'], data['currency'], data['margin_pct'])
        return jsonify({'success': success, 'message': message}), (200 if success else 404)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/delete', methods=['POST'])
def delete_loan(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all. Sprint 51 (ENH-01)."""
    try:
        mysql = get_mysql()
        success, message = Loan.delete(mysql, loan_id)
        return jsonify({'success': success, 'message': message}), (200 if success else 404)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/events', methods=['POST'])
def create_event(loan_id):
    """VULNERABILITY: No auth, IDOR — any loan_id accepts a new event, no ownership check."""
    try:
        data = request.get_json() if request.is_json else request.form
        event_type = data.get('event_type')
        effective_date = data.get('effective_date')
        payload = data.get('payload') or {}
        if event_type not in ('rate_change', 'bank_snapshot', 'refinance', 'closure') or not effective_date:
            return jsonify({'success': False, 'message': 'Invalid event_type or missing effective_date'}), 400

        mysql = get_mysql()
        success, message, event_id = LoanEvent.create(mysql, loan_id, event_type, effective_date, payload)
        return jsonify({'success': success, 'message': message, 'event_id': event_id}), (200 if success else 400)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/events', methods=['GET'])
def list_events(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all."""
    try:
        mysql = get_mysql()
        events = LoanEvent.get_by_loan(mysql, loan_id)
        return jsonify({'success': True, 'events': [_event_to_dict(e) for e in events]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/events/<int:event_id>', methods=['DELETE'])
def delete_event(loan_id, event_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on event_id at all,
    matching every other loan-event endpoint in this file. loan_id isn't
    even used to scope the delete (LoanEvent.delete() matches on event_id
    alone), so it's accepted here purely for URL-shape parity with the
    other /events routes."""
    try:
        mysql = get_mysql()
        success, message = LoanEvent.delete(mysql, event_id)
        return jsonify({'success': success, 'message': message}), (200 if success else 404)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/events/deleted', methods=['GET'])
def list_deleted_events(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all,
    matching list_events(). Sprint 49."""
    try:
        mysql = get_mysql()
        events = LoanEvent.get_deleted(mysql, loan_id)
        return jsonify({'success': True, 'events': [_event_to_dict(e) for e in events]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/events/<int:event_id>/restore', methods=['POST'])
def restore_event(loan_id, event_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on event_id at all,
    matching delete_event(). Sprint 49."""
    try:
        mysql = get_mysql()
        success, message = LoanEvent.restore(mysql, event_id)
        return jsonify({'success': success, 'message': message}), (200 if success else 404)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def compute_actual_baseline(mysql, loan_id):
    """
    VULNERABILITY: No ownership check — shared by every loan-analytics
    endpoint in this file, and — as of Sprint 32 — by utils/ai_context.py's
    compute_loan_status() too (promoted from a private helper since it's no
    longer only used within this module). Returns a dict with the raw
    inputs plus actual/baseline (so callers that need to re-run project()
    with modified inputs — leave-one-out, what-if — don't have to re-fetch
    from the DB), or None if loan_id doesn't exist at all.
    """
    loan = Loan.get_by_id(mysql, loan_id)
    if not loan:
        return None

    events = LoanEvent.get_by_loan(mysql, loan_id)
    rate_changes = [
        {
            'effective_date': e.effective_date, 'new_base_index_pct': e.payload.get('new_base_index_pct'),
            'id': e.id, 'created_at': e.created_at,
        }
        for e in events if e.event_type == 'rate_change'
    ]
    snapshots = [
        {
            'effective_date': e.effective_date,
            'remaining_principal': e.payload.get('remaining_principal'),
            'remaining_term_months': e.payload.get('remaining_term_months'),
            'current_rate_pct': e.payload.get('current_rate_pct'),
            'remaining_interest_total': e.payload.get('remaining_interest_total'),
            'reported_installment': e.payload.get('reported_installment'),
            'id': e.id, 'created_at': e.created_at,
        }
        for e in events if e.event_type == 'bank_snapshot'
    ]
    extra_payments = Loan.get_extra_payments(mysql, loan_id)

    loan_dict = {
        'principal': loan.principal, 'margin_pct': loan.margin_pct,
        'initial_base_index_pct': loan.initial_base_index_pct,
        'start_date': loan.start_date, 'original_term_months': loan.original_term_months,
    }

    # Baseline (Sprint 29, redefined 2026-09-02): same replay, no extra
    # payments, no snapshot pin at all — a pure, zero-extra-payment
    # schedule from loan origin. See secure-version's identical function
    # for the full writeup: originally anchored to the first real snapshot
    # instead, which meant Baseline silently inherited whatever real
    # extra-payment term-shortening had already happened by that
    # snapshot's date, rather than representing "if you'd never paid
    # extra, ever". Also note: the exact payoff date for an N-period
    # schedule is start_date + (N-1) months, not +N — period 1 is dated
    # the start date itself.
    #
    # snapshots_sorted is still needed for `actual` below — kept sorted
    # with the same (effective_date, created_at, id) tiebreaker as
    # project() (2026-08-24, BUG-20) for consistency, even though
    # baseline_snapshots itself no longer depends on it.
    snapshots_sorted = sorted(snapshots, key=lambda s: (s['effective_date'], s.get('created_at'), s.get('id')))
    baseline_snapshots = []

    actual = project(loan_dict, rate_changes, extra_payments, snapshots_sorted, include_extra_payments=True)
    baseline = project(loan_dict, rate_changes, extra_payments, baseline_snapshots, include_extra_payments=False)
    return {
        'loan': loan,
        'loan_dict': loan_dict,
        'rate_changes': rate_changes,
        'extra_payments': extra_payments,
        'snapshots': snapshots_sorted,
        'actual': actual,
        'baseline': baseline,
    }


def _current_period(periods):
    """Most recent period at-or-before today; None if the loan hasn't started yet (Sprint 30).

    Bug fixed 2026-08-08 (found via real usage on secure-version, ported
    here for parity): a period's `date` is just its monthly anchor label
    (e.g. the 11th) — extra payments and snapshots are bucketed into it by
    calendar month, not exact day (see project()'s extra_by_period), so
    they already take effect within that period's own balance_end
    regardless of which day-of-month they happened on. But this function
    used to require `period.date <= today`, so anything entered earlier in
    the current month (before the anchor day arrives) computed correctly
    internally yet stayed invisible in "current balance" for up to ~10
    days — silently reporting last month's stale figure instead. Fixed by
    preferring the period whose (year, month) matches today's, using it
    immediately rather than waiting for its anchor date."""
    today = date.today()
    for p in periods:
        if p['date'].year == today.year and p['date'].month == today.month:
            return p
    candidates = [p for p in periods if p['date'] <= today]
    return candidates[-1] if candidates else None


@api_loans_bp.route('/<int:loan_id>/project', methods=['GET'])
def get_projection(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all."""
    try:
        mysql = get_mysql()
        result = compute_actual_baseline(mysql, loan_id)
        if not result:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404
        actual, baseline = result['actual'], result['baseline']

        return jsonify({
            'success': True,
            'actual': _track_to_dict(actual),
            'baseline': _track_to_dict(baseline),
            'reconciliation': _reconciliation_to_dict(actual['reconciliation']),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _balance_as_of_today(period, today):
    """A period's balance_end already includes that period's own scheduled
    monthly payment — but if today is still before the period's anchor
    date, that payment hasn't actually happened yet. Bug found 2026-08-08
    (secure-version, ported here for parity), same session as the
    _current_period fix above: that fix correctly started selecting the
    right period early, but this still reported balance_end
    unconditionally, prematurely showing the not-yet-due monthly principal
    as already paid. Only extra payments/snapshot pins already recorded
    this month (baked into balance_start/extra_paid) are real before the
    anchor date; the scheduled portion isn't yet."""
    if period['date'] <= today:
        return period['balance_end']
    return round(period['balance_start'] - period['extra_paid'], 2)


def compute_loan_status(mysql, loan_id):
    """
    VULNERABILITY: No ownership check — same pattern as compute_actual_baseline().
    Current-status summary (Sprint 30, factored out of the /status route in
    Sprint 32 so utils/ai_context.py can reuse it without duplicating the
    logic) — today's balance/installment/rate from the Actual track, plus a
    simple years/interest-saved headline (Actual vs. Baseline diff). Returns
    None if loan_id doesn't exist at all.
    """
    result = compute_actual_baseline(mysql, loan_id)
    if not result:
        return None
    loan, actual, baseline = result['loan'], result['actual'], result['baseline']

    today = date.today()
    current = _current_period(actual['periods'])
    baseline_current = _current_period(baseline['periods'])
    current_balance = _balance_as_of_today(current, today) if current else None
    interest_saved = round(baseline['total_interest'] - actual['total_interest'], 2)
    years_saved = None
    months_saved = None
    if actual['payoff_date'] and baseline['payoff_date']:
        # Sprint 57 (ENH-16) fix: months_saved is an exact period-count
        # difference, not days/30.44 — same exact-installment-count-vs-
        # day-average distinction already established for term_impact_months.
        # years_saved is then derived straight from that exact count
        # (months/12) rather than an independent days/365.25 calculation,
        # so the two never drift apart by a rounding hair. Mirrors
        # secure-version.
        months_saved = len(baseline['periods']) - len(actual['periods'])
        years_saved = round(months_saved / 12, 2)

    # Sprint 33 follow-up: "debt amount saved" — distinct from interest_saved
    # (a lifetime total) in that this is a live, present-tense figure: how
    # much lower your actual balance is today than Baseline's projection for
    # today, purely from the extra payments logged so far.
    total_extra_paid = round(sum(p['amount'] for p in result['extra_payments']), 2)
    baseline_balance_today = _balance_as_of_today(baseline_current, today) if baseline_current else None
    debt_reduction_vs_baseline = (
        round(baseline_balance_today - current_balance, 2)
        if baseline_balance_today is not None and current_balance is not None
        else None
    )

    # "Dobanda" (interest) tracking, bank-confirmed rather than modeled.
    # current_total_dobanda is the latest bank snapshot's own reported total
    # remaining interest — null if no snapshot has ever recorded this
    # optional field (e.g. logged before this feature existed).
    # dobanda_saved_estimate anchors that real figure against Baseline's own
    # projected remaining interest at the same date, so the comparison uses
    # your bank's confirmed number as "Actual" instead of relying purely on
    # the model's own projection for both sides.
    dobanda_entries = [r for r in actual['reconciliation'] if r.get('reported_remaining_interest') is not None]
    current_total_dobanda = None
    dobanda_saved_estimate = None
    dobanda_snapshot_date = None
    if dobanda_entries:
        latest_dobanda_entry = dobanda_entries[-1]
        current_total_dobanda = latest_dobanda_entry['reported_remaining_interest']
        snapshot_date = latest_dobanda_entry['date']
        dobanda_snapshot_date = str(snapshot_date)
        # Interest "already spent" by Baseline is everything strictly before
        # the snapshot date, mirroring how the snapshot hard-pin itself is
        # applied before that period's own interest is computed (see the
        # snapshot-processing loop in loan_engine.py).
        baseline_interest_accrued = sum(
            p['interest'] for p in baseline['periods'] if p['date'] < snapshot_date
        )
        baseline_remaining_interest = baseline['total_interest'] - baseline_interest_accrued
        dobanda_saved_estimate = round(baseline_remaining_interest - current_total_dobanda, 2)

    # Sprint 32 fix: computed explicitly so callers (the AI context builder,
    # in particular) never have to infer "time until payoff" from the date
    # alone — Solis was observed conflating years_saved (a comparison
    # figure: how much sooner than Baseline) with years remaining (an
    # absolute figure: how much time is actually left) when only the date
    # and years_saved were given side by side.
    years_remaining = None
    months_remaining = None
    if actual['payoff_date']:
        # Same period-count-exactness reasoning as months_saved/years_saved
        # above, mirrors secure-version.
        if current:
            months_remaining = len(actual['periods']) - actual['periods'].index(current)
            if current['date'] <= today:
                months_remaining -= 1
        else:
            months_remaining = len(actual['periods'])
        months_remaining = max(months_remaining, 0)
        years_remaining = round(months_remaining / 12, 2)

    return {
        'loan_name': loan.name,
        'current_balance': current_balance,
        'current_installment': current['installment'] if current else None,
        'current_rate_pct': current['rate_pct'] if current else None,
        'payoff_date': str(actual['payoff_date']) if actual['payoff_date'] else None,
        'years_remaining': years_remaining,
        'months_remaining': months_remaining,
        'baseline_payoff_date': str(baseline['payoff_date']) if baseline['payoff_date'] else None,
        'interest_saved': interest_saved,
        'years_saved': years_saved,
        'months_saved': months_saved,
        'total_extra_paid': total_extra_paid,
        'baseline_balance_today': baseline_balance_today,
        'debt_reduction_vs_baseline': debt_reduction_vs_baseline,
        'current_total_dobanda': current_total_dobanda,
        'dobanda_saved_estimate': dobanda_saved_estimate,
        'dobanda_snapshot_date': dobanda_snapshot_date,
    }


@api_loans_bp.route('/<int:loan_id>/status', methods=['GET'])
def get_status(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all."""
    try:
        mysql = get_mysql()
        status = compute_loan_status(mysql, loan_id)
        if not status:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404
        return jsonify({'success': True, **status}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _baseline_remaining_interest_from(baseline_periods, payment_date):
    """
    Sum of the Baseline track's interest from the period matching
    payment_date's (year, month) onward — the "theoretical ceiling" a
    payment's efficiency is measured against (Sprint 31, Epic 3). Using the
    stable Baseline trajectory (no extra payments, ever) as the denominator
    for every payment gives each one the same kind of comparable ceiling
    regardless of when in the loan's life it happened, avoiding the
    mechanical near-payoff decline an absolute RON-per-RON figure would
    show. Returns None if payment_date falls outside Baseline's own period
    range (shouldn't happen in practice — Baseline always runs at least as
    long as Actual — but guarded rather than assumed).
    """
    total = 0.0
    started = False
    found = False
    for p in baseline_periods:
        if not started and (p['date'].year, p['date'].month) == (payment_date.year, payment_date.month):
            started = True
            found = True
        if started:
            total += p['interest']
    return total if found else None


def _real_snapshot_term_impact(payment, period_i, snapshots, extra_payments, rate_changes):
    """
    Sprint 54 (BUG-20), fourth redesign. See secure-version's identical
    function for the full writeup — reads the bank's own reported
    remaining_term_months directly from a real snapshot shortly before and
    shortly after the payment, when one cleanly brackets it alone, instead
    of approximating via a day-count or trusting our own simulated math to
    match the bank's exactly. Returns None when the real data doesn't
    cleanly bracket this payment (caller falls back to a simulated
    method).
    """
    period_end = _add_month(period_i['date'])
    candidates_before = [s for s in snapshots
                          if period_i['date'] <= s['effective_date'] < payment['date']]
    candidates_after = [s for s in snapshots
                         if payment['date'] <= s['effective_date'] < period_end]
    if not candidates_before or not candidates_after:
        return None
    snap_before = max(candidates_before, key=lambda s: s['effective_date'])
    snap_after = min(candidates_after, key=lambda s: s['effective_date'])
    if snap_before.get('remaining_term_months') is None or snap_after.get('remaining_term_months') is None:
        return None

    # Strict inequality on both sides — a payment dated exactly on either
    # boundary snapshot's own date is already baked into that snapshot's
    # figure, not an interloper; see secure-version's comment.
    other_payments_between = [p for p in extra_payments
                               if p is not payment
                               and snap_before['effective_date'] < p['date'] < snap_after['effective_date']]
    if other_payments_between:
        return None
    rate_changes_between = [rc for rc in rate_changes
                             if snap_before['effective_date'] < rc['effective_date'] < snap_after['effective_date']]
    if rate_changes_between:
        return None

    return int(snap_before['remaining_term_months']) - int(snap_after['remaining_term_months'])


@api_loans_bp.route('/<int:loan_id>/payment-ledger', methods=['GET'])
def get_payment_ledger(loan_id):
    """VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all.
    Sprint 51 (ENH-13) — display/audit only, see Loan.get_payment_ledger()."""
    try:
        mysql = get_mysql()
        ledger = Loan.get_payment_ledger(mysql, loan_id)
        return jsonify({'success': True, 'ledger': ledger}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/payment-impact', methods=['GET'])
def get_payment_impact(loan_id):
    """
    VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all.
    Isolated per-payment comparison, matching an official bank repayment
    chart's own before/after (Sprint 31, redesigned three times on
    2026-08-24 — BUG-20). For each real extra payment, measures that
    payment's own effect the same way the bank's own chart would if you
    asked "what does just this payment save": replay the loan using only
    real events strictly *before* this payment's date to get an
    uncontaminated anchor state, then compare two short projections from
    that anchor, one with the payment applied and one without, holding the
    rate constant and with no other extra payments in either run.
    interest_impact/term_impact are how much that one payment saved *on
    its own, as if nothing else about the loan changed afterward* — per
    the release-level scope decision, these do NOT sum to the total
    years/interest actually saved, because in reality extra payments and
    real rate changes compound together.

    efficiency_pct = interest_impact ÷ (Baseline's remaining interest from
    that payment's period onward) × 100 — see
    _baseline_remaining_interest_from() for why this specific denominator
    was chosen. efficiency_trend is the same data in chronological order
    with a 3-payment moving average.

    History: see secure-version/routes/api/loans.py's get_payment_impact()
    docstring for the full writeup — original full-lifetime-replay design
    let years of asymmetric snapshot correction dominate the measured
    impact for old payments. First redesign (start_override, symmetric
    both sides) fixed that but still folded in every real rate change and
    every other real payment made afterward. Second redesign anchored
    from Actual's own period for the payment's month — sound whenever
    that period has one real snapshot, but this loan has two the same
    month as the December payment (one just before it, one just after);
    the after one silently overwrote the before one, so the anchor was
    already post-payment and the payment got double-subtracted.
    Anchoring from a strictly-before replay instead can't be contaminated
    by same-period snapshots however many exist — but exposed a THIRD bug:
    finding the payment's own period by calendar (year, month) equality is
    wrong when periods are dated by the loan's anchor day (e.g. the 11th),
    not the 1st — a payment dated the 9th/10th of a month actually belongs
    to the PRIOR period, not the one sharing its own calendar month. Fixed
    by finding the latest period whose date is <= the payment's date.

    Fourth issue (2026-08-28): term_impact_months was computed as a
    payoff-date day-difference divided by a fixed 30.44 average, an
    approximation of a quantity the engine already tracks exactly (periods
    are discretely monthly). See secure-version's identical docstring for
    the full writeup. Fixed by preferring the bank's own reported
    remaining_term_months, read from a real snapshot cleanly bracketing
    the payment (_real_snapshot_term_impact), falling back to this run's
    own simulated period count otherwise.

    Known remaining limitation, not a code bug: this loan's imported
    history has no rate-change events between origin and its first real
    bank snapshot years later, so payments in that window are computed
    against an incomplete rate history — no code fix can correct that
    without the real historical data.
    """
    try:
        mysql = get_mysql()
        result = compute_actual_baseline(mysql, loan_id)
        if not result:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404

        loan_dict = result['loan_dict']
        rate_changes = result['rate_changes']
        extra_payments = result['extra_payments']
        snapshots = result['snapshots']
        actual = result['actual']
        baseline_periods = result['baseline']['periods']

        payments = []
        for payment in extra_payments:
            rate_changes_before = [rc for rc in rate_changes if rc['effective_date'] < payment['date']]
            snapshots_before = [s for s in snapshots if s['effective_date'] < payment['date']]
            extra_payments_before = [p for p in extra_payments if p['date'] < payment['date']]
            pre_payment = project(loan_dict, rate_changes_before, extra_payments_before, snapshots_before,
                                   include_extra_payments=True)

            # The period the payment actually falls into — the LATEST
            # period whose own date is <= the payment's date, not a
            # calendar-month equality match. See secure-version's
            # get_payment_impact() docstring/comment for the full writeup —
            # periods are dated by the loan's anchor day, so a naive
            # (year, month) match silently placed most of this loan's
            # payments (dated the 9th/10th, before the 11th anchor day)
            # one whole period too far along.
            period_i = None
            for p in pre_payment['periods']:
                if p['date'] <= payment['date']:
                    period_i = p
                else:
                    break
            if period_i is None:
                payments.append({
                    'date': str(payment['date']), 'amount': round(float(payment['amount']), 2),
                    'interest_impact': None, 'term_impact_days': None, 'term_impact_months': None,
                    'efficiency_pct': None, 'ron_per_month_saved': None,
                })
                continue

            anchor = {
                'date': period_i['date'],
                'balance': period_i['balance_start'],
                'rate_pct': period_i['rate_pct'],
                'installment': period_i['installment'],
            }
            # No rate_changes, no other real payments in either run — see
            # docstring's History section.
            local_actual = project(loan_dict, [], [payment], [],
                                    include_extra_payments=True, start_override=anchor)
            local_variant = project(loan_dict, [], [], [],
                                     include_extra_payments=True, start_override=anchor)

            interest_impact = round(local_variant['total_interest'] - local_actual['total_interest'], 2)
            term_impact_days = None
            term_impact_months = None
            if local_variant['payoff_date'] and local_actual['payoff_date']:
                term_impact_days = (local_variant['payoff_date'] - local_actual['payoff_date']).days
                # Prefer the bank's own reported remaining_term_months when
                # real snapshots cleanly bracket this payment; otherwise
                # fall back to this run's own simulated period count. See
                # docstring's History section.
                term_impact_months = _real_snapshot_term_impact(payment, period_i, snapshots, extra_payments, rate_changes)
                if term_impact_months is None:
                    term_impact_months = len(local_variant['periods']) - len(local_actual['periods'])

            ceiling = _baseline_remaining_interest_from(baseline_periods, payment['date'])
            efficiency_pct = round((interest_impact / ceiling) * 100, 2) if ceiling else None
            # How much this payment cost per whole month of term reduction —
            # a practical, if "lumpy", complement to efficiency_pct (added
            # after user feedback that term_impact_months' month-quantization
            # made cross-payment comparison hard to read directly).
            ron_per_month_saved = round(float(payment['amount']) / term_impact_months, 2) if term_impact_months else None

            payments.append({
                'date': str(payment['date']),
                'amount': round(float(payment['amount']), 2),
                'interest_impact': interest_impact,
                'term_impact_days': term_impact_days,
                'term_impact_months': term_impact_months,
                'efficiency_pct': efficiency_pct,
                'ron_per_month_saved': ron_per_month_saved,
            })

        # Still chronological here (matches extra_payments' own ORDER BY
        # transaction_date ASC) — build the trend before re-sorting for rank.
        efficiency_trend = []
        window = []
        for p in payments:
            if p['efficiency_pct'] is None:
                continue
            window.append(p['efficiency_pct'])
            if len(window) > 3:
                window.pop(0)
            efficiency_trend.append({
                'date': p['date'],
                'efficiency_pct': p['efficiency_pct'],
                'moving_avg_pct': round(sum(window) / len(window), 2),
            })

        payments.sort(key=lambda p: p['interest_impact'] if p['interest_impact'] is not None else float('-inf'), reverse=True)

        return jsonify({
            'success': True,
            'actual_payoff_date': str(actual['payoff_date']) if actual['payoff_date'] else None,
            'payments': payments,
            'efficiency_trend': efficiency_trend,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


def _add_months(d, n):
    """Returns the 1st of the month n months after d (Sprint 31)."""
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


@api_loans_bp.route('/<int:loan_id>/interest-per-ron', methods=['GET'])
def get_interest_per_ron(loan_id):
    """
    VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all.
    Interest-per-RON curve (Sprint 31) — tests a hypothetical extra payment
    amount added on top of real Actual history at each month across a
    chosen horizon, showing how much interest it would eliminate depending
    on when it's made. Tested on top of your real history (not in isolation
    against a clean Baseline) — a release-level scope decision.

    `months` (query param): a number of months, or the literal "full" to
    use the actual remaining term (derived from the Actual track's own
    period count, capped at 300 as a safety net) — added after user
    feedback that a fixed 12-month window couldn't show the full timing
    story on a loan with ~15 years still remaining.

    Same fix as /payment-impact applies here: for each sampled date, any
    real snapshot dated *after* that date is excluded from that variant's
    replay, since a real snapshot reports what actually happened without
    this hypothetical payment.
    """
    try:
        mysql = get_mysql()
        result = compute_actual_baseline(mysql, loan_id)
        if not result:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404

        try:
            amount = float(request.args.get('amount', 1000))
        except (TypeError, ValueError):
            amount = 1000.0
        if amount <= 0:
            return jsonify({'success': False, 'message': 'amount must be positive'}), 400

        loan_dict = result['loan_dict']
        rate_changes = result['rate_changes']
        extra_payments = result['extra_payments']
        snapshots = result['snapshots']
        actual = result['actual']

        today = date.today()
        months_param = request.args.get('months', '12')
        if months_param == 'full':
            num_months = len([p for p in actual['periods'] if p['date'] >= today])
        else:
            try:
                num_months = int(months_param)
            except (TypeError, ValueError):
                num_months = 12
        num_months = max(1, min(num_months, 300))

        curve = []
        for i in range(num_months):
            sample_date = _add_months(today, i + 1)
            hypothetical = extra_payments + [{'date': sample_date, 'amount': amount}]
            # Same-day excluded outright (2026-08-24, BUG-20) — sample_date
            # is a synthetic future payment, so there's no real created_at
            # to compare a same-day snapshot against like /payment-impact does.
            snapshots_before = [s for s in snapshots if s['effective_date'] < sample_date]
            variant = project(loan_dict, rate_changes, hypothetical, snapshots_before, include_extra_payments=True)
            interest_saved = round(actual['total_interest'] - variant['total_interest'], 2)
            curve.append({
                'date': str(sample_date),
                'interest_saved': interest_saved,
                'new_payoff_date': str(variant['payoff_date']) if variant['payoff_date'] else None,
            })

        return jsonify({'success': True, 'amount': amount, 'curve': curve}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/what-if', methods=['GET'])
def get_what_if(loan_id):
    """
    VULNERABILITY: No auth, IDOR — no ownership check on loan_id at all.
    What-if simulator (Sprint 31) — takes a hypothetical *recurring* monthly
    extra payment (not a one-time lump sum, unlike /interest-per-ron) and
    replays real history plus that synthetic recurring future payment,
    compared against real Actual. Directly answers "if I paid this much
    more every month starting now, when would I actually finish?" — added
    after user feedback surfaced this exact distinction.

    Same snapshot-filtering principle as /payment-impact and
    /interest-per-ron: any real snapshot dated after the simulation's start
    date is excluded from the replay.
    """
    try:
        mysql = get_mysql()
        result = compute_actual_baseline(mysql, loan_id)
        if not result:
            return jsonify({'success': False, 'message': 'Loan not found'}), 404

        try:
            monthly_amount = float(request.args.get('monthly_amount', 0))
        except (TypeError, ValueError):
            monthly_amount = 0.0
        if monthly_amount <= 0:
            return jsonify({'success': False, 'message': 'monthly_amount must be positive'}), 400

        today = date.today()
        start_date_param = request.args.get('start_date')
        if start_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            except ValueError:
                start_date = _add_months(today, 1)
        else:
            start_date = _add_months(today, 1)

        loan_dict = result['loan_dict']
        rate_changes = result['rate_changes']
        extra_payments = result['extra_payments']
        snapshots = result['snapshots']
        actual = result['actual']

        synthetic_payments = [{'date': _add_months(start_date, i), 'amount': monthly_amount} for i in range(300)]
        hypothetical = extra_payments + synthetic_payments
        # Same-day excluded outright (2026-08-24, BUG-20), same reasoning
        # as /interest-per-ron — start_date hasn't actually happened yet.
        snapshots_before_start = [s for s in snapshots if s['effective_date'] < start_date]

        variant = project(loan_dict, rate_changes, hypothetical, snapshots_before_start, include_extra_payments=True)

        interest_saved = round(actual['total_interest'] - variant['total_interest'], 2)
        term_saved_months = None
        if actual['payoff_date'] and variant['payoff_date']:
            term_saved_days = (actual['payoff_date'] - variant['payoff_date']).days
            term_saved_months = round(term_saved_days / 30.44, 1)

        return jsonify({
            'success': True,
            'monthly_amount': monthly_amount,
            'start_date': str(start_date),
            'actual_payoff_date': str(actual['payoff_date']) if actual['payoff_date'] else None,
            'actual_total_interest': actual['total_interest'],
            'new_payoff_date': str(variant['payoff_date']) if variant['payoff_date'] else None,
            'new_total_interest': variant['total_interest'],
            'interest_saved': interest_saved,
            'term_saved_months': term_saved_months,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@api_loans_bp.route('/<int:loan_id>/parse-chart', methods=['POST'])
def parse_chart(loan_id):
    """
    Extracts text from an uploaded bank chart PDF and returns best-effort
    field guesses (Sprint 30 extension). Purely an assist — nothing is
    persisted here; the caller reviews/corrects the guessed values and
    still submits them via POST /<id>/events itself.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        text = extract_text(file)
        return jsonify({'success': True, 'raw_text': text, 'guessed': guess_chart_fields(text)}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Could not read this PDF: {str(e)}'}), 500


def _loan_to_dict(l):
    return {
        'id': l.id, 'user_id': l.user_id,  # VULN: exposing user_id
        'name': l.name, 'principal': l.principal, 'margin_pct': l.margin_pct,
        'initial_base_index_pct': l.initial_base_index_pct, 'start_date': str(l.start_date),
        'original_term_months': l.original_term_months, 'currency': l.currency,
        'status': l.status, 'created_at': str(l.created_at) if l.created_at else None,
    }


def _event_to_dict(e):
    return {
        'id': e.id, 'event_type': e.event_type, 'effective_date': str(e.effective_date),
        'payload': e.payload, 'created_at': str(e.created_at) if e.created_at else None,
    }


def _period_to_dict(p):
    return {**p, 'date': str(p['date'])}


def _track_to_dict(result):
    return {
        'payoff_date': str(result['payoff_date']) if result['payoff_date'] else None,
        'total_interest': result['total_interest'],
        'periods': [_period_to_dict(p) for p in result['periods']],
    }


def _reconciliation_to_dict(items):
    return [{**r, 'date': str(r['date'])} for r in items]
