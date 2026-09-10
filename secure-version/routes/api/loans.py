"""
Aura Financial Tracker - Secure Version
Loan API Routes
Sprint 28: Loan Intelligence Foundation

Security properties (contrast with vulnerable-version/routes/api/loans.py):
- Every route requires @api_login_required; user_id always comes from session
- loan_id ownership enforced at the model layer on every read/write
- /project is read-only — it calls the deterministic engine on data already
  scoped to the caller, never accepts loan terms/events directly from the request
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request, session, current_app

from models.loan import Loan, LoanEvent
from routes.main import api_login_required
from utils.loan_engine import project, _add_month
from utils.chart_parser import extract_text, guess_chart_fields

MAX_CHART_UPLOAD_BYTES = 10 * 1024 * 1024

api_loans_bp = Blueprint('api_loans', __name__)


def get_mysql():
    return current_app.extensions['mysql']


@api_loans_bp.route('/create', methods=['POST'])
@api_login_required
def create_loan():
    mysql = get_mysql()
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}

    required = ['name', 'principal', 'margin_pct', 'initial_base_index_pct', 'start_date', 'original_term_months']
    if not all(data.get(f) not in (None, '') for f in required):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    success, message, loan_id = Loan.create(
        mysql, user_id, data['name'], data['principal'], data['margin_pct'],
        data['initial_base_index_pct'], data['start_date'], data['original_term_months'],
        data.get('currency', 'RON'),
    )
    status = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'loan_id': loan_id}), status


@api_loans_bp.route('/list', methods=['GET'])
@api_login_required
def list_loans():
    mysql = get_mysql()
    user_id = session['user_id']
    loans = Loan.get_all_by_user(mysql, user_id)
    return jsonify({'success': True, 'loans': [_loan_to_dict(l) for l in loans]}), 200


@api_loans_bp.route('/<int:loan_id>', methods=['GET'])
@api_login_required
def get_loan(loan_id):
    mysql = get_mysql()
    user_id = session['user_id']
    loan = Loan.get_by_id(mysql, loan_id, user_id)
    if not loan:
        return jsonify({'success': False, 'message': 'Loan not found'}), 404
    return jsonify({'success': True, 'loan': _loan_to_dict(loan)}), 200


@api_loans_bp.route('/<int:loan_id>/update', methods=['POST'])
@api_login_required
def update_loan(loan_id):
    """Sprint 51 (ENH-01) — only name/currency/margin_pct, matching Loan.update()'s signature."""
    mysql = get_mysql()
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}

    required = ['name', 'currency', 'margin_pct']
    if not all(data.get(f) not in (None, '') for f in required):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    success, message = Loan.update(mysql, loan_id, user_id, data['name'], data['currency'], data['margin_pct'])
    return jsonify({'success': success, 'message': message}), (200 if success else 404)


@api_loans_bp.route('/<int:loan_id>/delete', methods=['POST'])
@api_login_required
def delete_loan(loan_id):
    """Sprint 51 (ENH-01)."""
    mysql = get_mysql()
    user_id = session['user_id']
    success, message = Loan.delete(mysql, loan_id, user_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 404)


@api_loans_bp.route('/<int:loan_id>/events', methods=['POST'])
@api_login_required
def create_event(loan_id):
    mysql = get_mysql()
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}

    event_type = data.get('event_type')
    effective_date = data.get('effective_date')
    payload = data.get('payload') or {}
    if event_type not in ('rate_change', 'bank_snapshot', 'refinance', 'closure') or not effective_date:
        return jsonify({'success': False, 'message': 'Invalid event_type or missing effective_date'}), 400

    success, message, event_id = LoanEvent.create(mysql, loan_id, user_id, event_type, effective_date, payload)
    status = 200 if success else 404
    return jsonify({'success': success, 'message': message, 'event_id': event_id}), status


@api_loans_bp.route('/<int:loan_id>/events', methods=['GET'])
@api_login_required
def list_events(loan_id):
    mysql = get_mysql()
    user_id = session['user_id']
    events = LoanEvent.get_by_loan(mysql, loan_id, user_id)
    return jsonify({'success': True, 'events': [_event_to_dict(e) for e in events]}), 200


@api_loans_bp.route('/<int:loan_id>/events/<int:event_id>', methods=['DELETE'])
@api_login_required
def delete_event(loan_id, event_id):
    mysql = get_mysql()
    user_id = session['user_id']
    success, message = LoanEvent.delete(mysql, event_id, loan_id, user_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 404)


@api_loans_bp.route('/<int:loan_id>/events/deleted', methods=['GET'])
@api_login_required
def list_deleted_events(loan_id):
    """Sprint 49 — soft-deleted events still recoverable via restore_event()."""
    mysql = get_mysql()
    user_id = session['user_id']
    events = LoanEvent.get_deleted(mysql, loan_id, user_id)
    return jsonify({'success': True, 'events': [_event_to_dict(e) for e in events]}), 200


@api_loans_bp.route('/<int:loan_id>/events/<int:event_id>/restore', methods=['POST'])
@api_login_required
def restore_event(loan_id, event_id):
    """Sprint 49."""
    mysql = get_mysql()
    user_id = session['user_id']
    success, message = LoanEvent.restore(mysql, event_id, loan_id, user_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 404)


def compute_actual_baseline(mysql, loan_id, user_id):
    """
    Shared by every loan-analytics endpoint in this file, and — as of
    Sprint 32 — by utils/ai_context.py's compute_loan_status() too (promoted
    from a private helper since it's no longer only used within this
    module). Loads the loan and its events/tagged transactions (all scoped
    to user_id), computes Actual and Baseline, and returns the raw inputs
    alongside them so callers that need to re-run project() with modified
    inputs (leave-one-out, what-if) don't have to re-fetch from the DB.
    Returns None if the loan isn't found/owned.
    """
    loan = Loan.get_by_id(mysql, loan_id, user_id)
    if not loan:
        return None

    events = LoanEvent.get_by_loan(mysql, loan_id, user_id)
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
    extra_payments = Loan.get_extra_payments(mysql, loan_id, user_id)

    loan_dict = {
        'principal': loan.principal, 'margin_pct': loan.margin_pct,
        'initial_base_index_pct': loan.initial_base_index_pct,
        'start_date': loan.start_date, 'original_term_months': loan.original_term_months,
    }

    # Baseline (Sprint 29, redefined 2026-09-02): same replay, no extra
    # payments, no snapshot pin at all — a pure, zero-extra-payment
    # schedule from loan origin. Originally anchored to the first real
    # snapshot instead (kept here for history: that snapshot's own
    # reported balance already reflects whatever real extra payments had
    # been made by that date, which meant Baseline silently inherited some
    # real term-shortening rather than representing "if you'd never paid
    # extra, ever" — confirmed against the user's real loan, where this
    # made Baseline read 2045-11-11 instead of the true zero-extra-payment
    # schedule end date. Note the exact payoff date for an N-period
    # schedule is start_date + (N-1) months, not +N — period 1 is dated
    # the start date itself, so a 300-period schedule from 2021-06-11 ends
    # 2046-05-11, not 2046-06-11 as it's easy to assume. Explicit user
    # decision to redefine Baseline as the pure schedule instead — no
    # extra payments credited at any point, not even ones made before the
    # first bank check-in.
    #
    # snapshots_sorted is still needed for `actual` below (real events,
    # real order) — kept sorted with the same (effective_date, created_at,
    # id) tiebreaker as project() (2026-08-24, BUG-20) for consistency,
    # even though baseline_snapshots itself no longer depends on it.
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

    Bug fixed 2026-08-08 (found via real usage): a period's `date` is just
    its monthly anchor label (e.g. the 11th) — extra payments and snapshots
    are bucketed into it by calendar month, not exact day (see project()'s
    extra_by_period), so they already take effect within that period's own
    balance_end regardless of which day-of-month they happened on. But this
    function used to require `period.date <= today`, so anything entered
    earlier in the current month (before the anchor day arrives) computed
    correctly internally yet stayed invisible in "current balance" for up
    to ~10 days — silently reporting last month's stale figure instead.
    Fixed by preferring the period whose (year, month) matches today's,
    using it immediately rather than waiting for its anchor date."""
    today = date.today()
    for p in periods:
        if p['date'].year == today.year and p['date'].month == today.month:
            return p
    candidates = [p for p in periods if p['date'] <= today]
    return candidates[-1] if candidates else None


def _balance_as_of_today(period, today):
    """A period's balance_end already includes that period's own scheduled
    monthly payment — but if today is still before the period's anchor
    date, that payment hasn't actually happened yet. Bug found 2026-08-08,
    same session as the _current_period fix above: that fix correctly
    started selecting the right period early, but then this still reported
    balance_end unconditionally, prematurely showing the not-yet-due
    monthly principal as already paid. Only extra payments/snapshot pins
    already recorded this month (baked into balance_start/extra_paid) are
    real before the anchor date; the scheduled portion isn't yet."""
    if period['date'] <= today:
        return period['balance_end']
    return round(period['balance_start'] - period['extra_paid'], 2)


def compute_loan_status(mysql, loan_id, user_id):
    """
    Current-status summary (Sprint 30, factored out of the /status route in
    Sprint 32 so utils/ai_context.py can reuse it without duplicating the
    logic) — today's balance/installment/rate from the Actual track, plus a
    simple years/interest-saved headline (Actual vs. Baseline diff). Deeper
    behavioral analytics (leave-one-out ranking, interest-per-RON curve,
    normalized efficiency) are Sprint 31's endpoints, deliberately not
    included here. Returns None if the loan isn't found/owned.
    """
    result = compute_actual_baseline(mysql, loan_id, user_id)
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
        # difference, not days/30.44 — the same exact-installment-count-vs-
        # day-average distinction already established for term_impact_months
        # (see get_payment_impact's docstring below) applies here. Both
        # tracks start from the same loan start_date, so len(periods) is
        # already an exact month count. years_saved is then derived
        # straight from that exact count (months/12) rather than an
        # independent days/365.25 calculation, so the two never drift apart
        # by a rounding hair (e.g. "14.51 years (174 months)" when 174/12
        # is exactly 14.5).
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
        # above: count periods from the current one through the last, minus
        # one if this period's own payment has already happened this month
        # (mirrors _balance_as_of_today's identical date<=today
        # distinction), then derive years_remaining straight from that
        # exact count rather than an independent days/365.25 calculation.
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


@api_loans_bp.route('/<int:loan_id>/project', methods=['GET'])
@api_login_required
def get_projection(loan_id):
    """
    Read-only — calls the deterministic engine using only data already
    scoped to the caller (the loan's own terms, its own events, its own
    tagged transactions). No loan terms or events are ever accepted from
    the request itself.
    """
    mysql = get_mysql()
    user_id = session['user_id']
    result = compute_actual_baseline(mysql, loan_id, user_id)
    if not result:
        return jsonify({'success': False, 'message': 'Loan not found'}), 404
    actual, baseline = result['actual'], result['baseline']

    return jsonify({
        'success': True,
        'actual': _track_to_dict(actual),
        'baseline': _track_to_dict(baseline),
        'reconciliation': _reconciliation_to_dict(actual['reconciliation']),
    }), 200


@api_loans_bp.route('/<int:loan_id>/status', methods=['GET'])
@api_login_required
def get_status(loan_id):
    """Thin wrapper around compute_loan_status() (Sprint 32 refactor)."""
    mysql = get_mysql()
    user_id = session['user_id']
    status = compute_loan_status(mysql, loan_id, user_id)
    if not status:
        return jsonify({'success': False, 'message': 'Loan not found'}), 404
    return jsonify({'success': True, **status}), 200


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
    Sprint 54 (BUG-20), fourth redesign. Prefers the bank's own reported
    remaining_term_months, read directly from a real snapshot shortly
    before AND shortly after the payment (both within the payment's own
    period, nothing else -- another payment, a rate change -- between
    them), over any simulated projection. This is literally the bank's own
    figure, not our model's approximation of it, and is why it resolves
    cases the simulated method can't: term_impact_months as (payoff-date
    difference / 30.44) is measuring the wrong unit (a fixed day-average
    standing in for what the engine already knows is a whole installment
    count), and even switching to a straight period-count difference still
    depends on our own math matching the bank's exactly. Reading the two
    real numbers and subtracting them sidesteps both.

    Returns None when the real data doesn't cleanly bracket this payment
    alone -- caller should fall back to a simulated method in that case.
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

    # Strict inequality on both sides: a payment dated exactly ON
    # snap_before's or snap_after's own date is a legitimate boundary
    # case, not an interloper -- its effect is already baked into that
    # snapshot's reported figure (e.g. May's own payment is what made
    # May's "after" snapshot the right "before" anchor for June's
    # payment). Only a payment strictly *between* the two dates would
    # actually confound the measurement.
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
@api_login_required
def get_payment_ledger(loan_id):
    """Sprint 51 (ENH-13) — display/audit only, see Loan.get_payment_ledger()'s docstring."""
    mysql = get_mysql()
    user_id = session['user_id']
    ledger = Loan.get_payment_ledger(mysql, loan_id, user_id)
    return jsonify({'success': True, 'ledger': ledger}), 200


@api_loans_bp.route('/<int:loan_id>/payment-impact', methods=['GET'])
@api_login_required
def get_payment_impact(loan_id):
    """
    Isolated per-payment comparison, matching an official bank repayment
    chart's own before/after (Sprint 31, redesigned three times on
    2026-08-24 — BUG-20). For each real extra payment, measures that
    payment's own effect the same way the bank's own chart would if you
    asked "what does just this payment save": replay the loan using only
    real events strictly *before* this payment's date (its own real
    rate-change and snapshot history up to that point, no later events at
    all) to get an uncontaminated anchor state, then compare two short
    projections from that anchor, one with the payment applied and one
    without, holding the rate constant and with no other extra payments in
    either run. interest_impact/term_impact are how much that one payment
    saved *on its own, as if nothing else about the loan changed
    afterward* — per the release-level scope decision, these do NOT sum to
    the total years/interest actually saved, because in reality extra
    payments and real rate changes compound together. The frontend must
    say so, not present this as if it should add up.

    efficiency_pct = interest_impact ÷ (Baseline's remaining interest from
    that payment's period onward) × 100 — see
    _baseline_remaining_interest_from() for why this specific denominator
    was chosen. efficiency_trend is the same data in chronological order
    with a 3-payment moving average, for a trend view that doesn't
    mechanically decline near payoff the way an unnormalized figure would.

    History: original design diffed two full-lifetime replays, letting
    years of asymmetric snapshot correction dominate the measured impact
    for old payments. First redesign made both sides symmetric via
    start_override, but still folded in every real rate change and every
    other real payment made afterward, so a payment's measured impact
    quietly depended on what happened later — confirmed wrong against a
    real bank chart pair (Grafic rambursare 18/19.pdf) showing a clean
    13-month reduction with nothing else changing. Second redesign
    anchored from `actual`'s own already-pinned period for the payment's
    month — mathematically sound whenever that period has at most one
    real snapshot, but a REAL, second bug: this loan actually has two
    snapshots the same month as the December payment (one dated just
    before it, one just after) — the after one silently overwrote the
    before one as that period's recorded state, so the anchor was already
    post-payment, and the payment then got double-subtracted in
    local_actual while local_variant inherited the same contamination.
    Anchoring from a strictly-before replay fixed that, but exposed a
    THIRD, separate bug in how the payment's own period was then found
    within that replay: matched by calendar (year, month) equality against
    the payment's transaction_date, when periods are actually dated by the
    loan's own anchor day (the 11th, for this real loan) — a period
    labeled June covers June 11 through July 10. Most of this loan's real
    payments are dated the 9th/10th (before the anchor day), so the naive
    match was silently landing on the FOLLOWING period — one whole
    month's scheduled principal further along than the payment's real
    date — producing plausible-but-wrong figures on exactly those
    payments (confirmed against the user's own expected pattern: several
    payments the user expected at a clean 3.0 months were showing 3.9/4.0).
    Fixed by finding the latest period whose own date is <= the payment's
    date (a proper interval lookup), not an equality match.

    Fourth issue (2026-08-28, not a regression of the above -- exposed
    only once the anchor itself was correct): term_impact_months was
    computed as (payoff-date difference in days) / 30.44, rounded to 1
    decimal. But this loan's periods are already discretely monthly by
    construction -- dividing a day-count by a fixed average month length
    is an approximation of a quantity the engine already knows exactly,
    and several real payments landed on the wrong side of a whole-month
    boundary because of it (2.9, 3.9, 4.0 instead of a clean 3.0;
    December's 7,300 RON payment showed 12.9 instead of the bank chart's
    13). Fixed in two layers: primarily, read the bank's own reported
    remaining_term_months directly from a real snapshot shortly before and
    shortly after the payment when one cleanly exists (literally the
    bank's own number, see _real_snapshot_term_impact); otherwise fall
    back to this run's own simulated period count (len(periods) diff),
    which is still an exact installment count, just our model's own
    rather than the bank's. Verified against the user's full real payment
    history: every previously-flagged payment now lands on its expected
    whole-month figure. One payment (2025-04-10) still doesn't -- see the
    known limitation below, which is the actual cause: no real snapshot
    data exists anywhere near it to read from, and the simulated fallback
    inherits the same missing-rate-history gap.

    Known remaining limitation, not a code bug: this loan's imported
    history has no real rate-change events between loan origin
    (2021-06-11) and its first real bank snapshot (2025-04-15) — the
    engine assumes the origination rate held constant across that ~4-year
    gap, which is almost certainly wrong for a variable-rate mortgage.
    Every payment dated in that window (2023, and early 2025 before the
    first snapshot) is computed against that incomplete rate history, and
    no code fix can correct it without the real historical rate-change
    data.
    """
    mysql = get_mysql()
    user_id = session['user_id']
    result = compute_actual_baseline(mysql, loan_id, user_id)
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

        # The period the payment actually falls into — the LATEST period
        # whose own date is <= the payment's date, not a calendar-month
        # equality match. Periods are dated by the loan's own anchor day
        # (e.g. the 11th), so a period labeled June covers June 11 through
        # July 10 — a payment dated July 10 belongs to the June period, not
        # a "July" one, even though its own transaction_date says July.
        # Found and fixed 2026-08-24 (BUG-20): most of this loan's payments
        # are dated the 9th/10th (before the anchor day), which a naive
        # (year, month) match was silently placing in the following
        # period — one whole month's scheduled principal too far along —
        # producing a plausible-looking but real ~1-month error on
        # payments that should have landed on a clean, expected figure.
        period_i = None
        for p in pre_payment['periods']:
            if p['date'] <= payment['date']:
                period_i = p
            else:
                break
        if period_i is None:
            # Defensive only — every real payment should have at least one
            # period at or before it (even the very first one, at loan
            # origin); skip gracefully rather than crash if a data anomaly
            # ever puts one outside the projected range.
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
        # No rate_changes, no other real payments in either run — matches
        # what the bank's own chart would show for this payment alone, not
        # a projection that depends on every other real thing that
        # happened afterward. See docstring's History section.
        local_actual = project(loan_dict, [], [payment], [],
                                include_extra_payments=True, start_override=anchor)
        local_variant = project(loan_dict, [], [], [],
                                 include_extra_payments=True, start_override=anchor)

        interest_impact = round(local_variant['total_interest'] - local_actual['total_interest'], 2)
        term_impact_days = None
        term_impact_months = None
        if local_variant['payoff_date'] and local_actual['payoff_date']:
            term_impact_days = (local_variant['payoff_date'] - local_actual['payoff_date']).days
            # Prefer the bank's own reported remaining_term_months (see
            # _real_snapshot_term_impact) when real snapshots cleanly
            # bracket this payment; otherwise fall back to this run's own
            # simulated period count. Both are exact installment counts,
            # not a day-count divided by a fixed month-length average (the
            # original method) -- see docstring's History section.
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


def _add_months(d, n):
    """Returns the 1st of the month n months after d (Sprint 31)."""
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


@api_loans_bp.route('/<int:loan_id>/interest-per-ron', methods=['GET'])
@api_login_required
def get_interest_per_ron(loan_id):
    """
    Interest-per-RON curve (Sprint 31) — tests a hypothetical extra payment
    amount added on top of real Actual history at each month across a
    chosen horizon, showing how much interest it would eliminate depending
    on when it's made. Tested on top of your real history (not in isolation
    against a clean Baseline) — a release-level scope decision, since "is
    this month or a later month better?" is the practically useful question.

    `months` (query param): a number of months, or the literal "full" to
    use the actual remaining term (derived from the Actual track's own
    period count, capped at 300 as a safety net) — added after user
    feedback that a fixed 12-month window couldn't show the full timing
    story on a loan with ~15 years still remaining.

    Same fix as /payment-impact applies here: for each sampled date, any
    real snapshot dated *after or on* that date is excluded from that
    variant's replay, since a real snapshot reports what actually happened
    without this hypothetical payment — hard-pinning to it would silently
    erase the very difference this endpoint exists to measure. Same-day is
    excluded outright here (2026-08-24, BUG-20) rather than compared via
    created_at like /payment-impact does: the sampled payment is synthetic
    and hasn't actually happened, so there's no real created_at to compare
    a same-day snapshot against.
    """
    mysql = get_mysql()
    user_id = session['user_id']
    result = compute_actual_baseline(mysql, loan_id, user_id)
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
        snapshots_before = [s for s in snapshots if s['effective_date'] < sample_date]
        variant = project(loan_dict, rate_changes, hypothetical, snapshots_before, include_extra_payments=True)
        interest_saved = round(actual['total_interest'] - variant['total_interest'], 2)
        curve.append({
            'date': str(sample_date),
            'interest_saved': interest_saved,
            'new_payoff_date': str(variant['payoff_date']) if variant['payoff_date'] else None,
        })

    return jsonify({'success': True, 'amount': amount, 'curve': curve}), 200


@api_loans_bp.route('/<int:loan_id>/what-if', methods=['GET'])
@api_login_required
def get_what_if(loan_id):
    """
    What-if simulator (Sprint 31) — takes a hypothetical *recurring* monthly
    extra payment (not a one-time lump sum, unlike /interest-per-ron) and
    replays real history plus that synthetic recurring future payment,
    compared against real Actual. Directly answers "if I paid this much
    more every month starting now, when would I actually finish?" — the
    question /interest-per-ron's one-time-payment curve can't answer (added
    after user feedback surfaced this exact distinction).

    Same snapshot-filtering principle as /payment-impact and
    /interest-per-ron: any real snapshot dated on or after the
    simulation's start date is excluded from the replay, since it reports
    what actually happened without this hypothetical recurring payment.
    Same-day excluded outright (2026-08-24, BUG-20), same reasoning as
    /interest-per-ron — the start date is synthetic/hasn't happened yet,
    so there's no real created_at to compare a same-day snapshot against.
    """
    mysql = get_mysql()
    user_id = session['user_id']
    result = compute_actual_baseline(mysql, loan_id, user_id)
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

    # 300 months (safety-cap length, matching /interest-per-ron) is more
    # than enough to cover any realistic remaining term — project() simply
    # stops once the balance reaches zero, so entries beyond natural payoff
    # are never visited.
    synthetic_payments = [{'date': _add_months(start_date, i), 'amount': monthly_amount} for i in range(300)]
    hypothetical = extra_payments + synthetic_payments
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


@api_loans_bp.route('/<int:loan_id>/parse-chart', methods=['POST'])
@api_login_required
def parse_chart(loan_id):
    """
    Extracts text from an uploaded bank chart PDF and returns best-effort
    field guesses (Sprint 30 extension). Purely an assist — nothing is
    persisted here; the caller reviews/corrects the guessed values and
    still submits them via POST /<id>/events itself.
    """
    mysql = get_mysql()
    user_id = session['user_id']
    loan = Loan.get_by_id(mysql, loan_id, user_id)
    if not loan:
        return jsonify({'success': False, 'message': 'Loan not found'}), 404

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Only PDF files are supported'}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_CHART_UPLOAD_BYTES:
        return jsonify({'success': False, 'message': 'File too large (max 10MB)'}), 400

    try:
        text = extract_text(file)
    except Exception:
        return jsonify({'success': False, 'message': 'Could not read this PDF'}), 400

    return jsonify({'success': True, 'raw_text': text, 'guessed': guess_chart_fields(text)}), 200


def _loan_to_dict(l):
    return {
        'id': l.id, 'name': l.name, 'principal': l.principal, 'margin_pct': l.margin_pct,
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
