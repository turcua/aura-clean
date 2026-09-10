"""
Aura Financial Tracker - Vulnerable Version
Loan Amortization Engine
Sprint 28: Loan Intelligence Foundation

Pure, deterministic math — identical to secure-version/utils/loan_engine.py
on purpose. This file is not a vulnerable/secure contrast point: the
vulnerabilities in this release live in the route/model layer (IDOR, SQL
injection — VULN-080), not in the amortization math itself, so there is no
"intentionally broken" version of this engine. Both apps must compute the
same correct numbers regardless of which version's endpoints get attacked.

Confirmed rules (validated against the user's real bank chart data during
the Release 8 design conversation, interest formula reproduced to the
cent):
- Extra payment: pure principal reduction. Installment unchanged, remaining
  term shortens implicitly.
- Rate change: installment recalculated via the standard amortization
  formula, holding remaining term fixed — remaining term is *derived* from
  (balance, installment, old rate) at the moment of the change, never
  tracked as separate state that could drift out of sync with what extra
  payments have already done to the timeline.
- Bank snapshot: a hard pin (balance/rate/derived-term jump straight to the
  snapshot's reported values), not an additive event.

Bug fixed 2026-08-07 (found via real usage, not a test): a snapshot pinned
in the same calendar month as an extra payment used to double-count that
payment — once implicitly, via the bank's own reported balance (which
already reflects any payment it had processed before the chart was
generated), and once explicitly, via this engine's own extra-payment
subtraction, keyed only by month with no awareness a pin had just absorbed
it. Fixed by tracking each extra payment's exact date and only counting,
in a period where a snapshot pins, payments dated *after* that snapshot's
effective_date.

Bug fixed 2026-08-12 (found via real usage): a bank chart generated any
time after a period's own anchor day (e.g. the loan's payment day is the
11th, and a chart is generated the 12th) could never pin *that* period —
the snapshot-pinning loop compared effective_date against current_date
with a strict day-level `<=`, so a snapshot one day "too late" was silently
deferred a full month, even though it's the freshest, most authoritative
data available right now. Inconsistent with how extra payments already
work (bucketed by calendar month since the 2026-08-07 fix referenced
above) and with _current_period()'s own 2026-08-08 fix in routes/api/
loans.py, which bucket-selects the current period by (year, month) for
exactly this reason. Fixed by comparing snapshots against current_date by
(year, month) too, so any chart generated within the same calendar month
as a period's anchor correctly pins that period, not the next one.

Bug fixed 2026-08-24 (BUG-20, found via real usage on the Payment Impact
card): rate_changes/snapshots were sorted by effective_date alone, so two
events sharing the same effective_date had no defined relative order —
which one "won" when both pinned the same period depended on database
return order for the tie, not the real order they were actually logged
in. Confirmed against the user's real history (two same-day bank
snapshots, 2025-12-09). Fixed by sorting on (effective_date, created_at,
id) instead — created_at/id already existed on every event row, just
weren't threaded through into these dicts until this fix (see
routes/api/loans.py's compute_actual_baseline()).

Bug fixed 2026-08-24 (BUG-20, deeper root cause than the fix above): see
secure-version/utils/loan_engine.py's module docstring for the full
writeup — get_payment_impact() diffed two full-lifetime replays instead
of two symmetric local ones, letting years of asymmetric snapshot
correction dominate the measured impact for old payments, occasionally
flipping it negative. Fixed via start_override (below).
"""

import math
from datetime import date

MAX_PERIODS = 600  # 50 years — safety cap against a degenerate input never converging


def monthly_rate(annual_rate_pct):
    return (annual_rate_pct / 100.0) / 12.0


def derive_remaining_periods(balance, installment, monthly_r):
    """
    How many periods it would take to pay off `balance` at `installment`
    per period and `monthly_r` monthly rate — i.e. "remaining term",
    recovered from state already being tracked rather than a second,
    independently-drifting counter. Standard amortization formula solved
    for n. Returns None if the installment doesn't even cover the interest
    (would never pay off at this rate/payment combination).
    """
    if installment <= 0:
        return None
    if monthly_r == 0:
        return balance / installment
    if installment <= balance * monthly_r:
        return None
    return -math.log(1 - (balance * monthly_r) / installment) / math.log(1 + monthly_r)


def calculate_installment(balance, monthly_r, n_periods):
    """Standard fixed-payment amortization formula, solving for the payment
    that fully amortizes `balance` over `n_periods` at `monthly_r`."""
    if n_periods <= 0:
        return balance
    if monthly_r == 0:
        return balance / n_periods
    factor = (1 + monthly_r) ** n_periods
    return balance * (monthly_r * factor) / (factor - 1)


def project(loan, rate_changes, extra_payments, snapshots, include_extra_payments=True, start_override=None):
    """
    loan: dict with principal, margin_pct, initial_base_index_pct, start_date
          (date), original_term_months
    rate_changes: list of dicts {effective_date, new_base_index_pct}, any order
    extra_payments: list of dicts {date, amount}, any order — ignored
                    entirely if include_extra_payments is False (this is how
                    the Baseline track, added in Sprint 29, reuses this exact
                    function with no changes needed here)
    snapshots: list of dicts {effective_date, remaining_principal,
               remaining_term_months, current_rate_pct}, any order
    start_override: optional dict {date, balance, rate_pct, installment} —
                    when given, the projection begins at this exact known
                    state instead of replaying from loan['start_date']/
                    loan['principal']. rate_changes/extra_payments/snapshots
                    dated before this state's (year, month) are dropped
                    entirely — the override already reflects them. See
                    module docstring (BUG-20, 2026-08-24) and
                    get_payment_impact()'s docstring.

    Returns {
        'periods': [{date, balance_start, rate_pct, installment, interest,
                     scheduled_principal, extra_paid, balance_end}, ...],
        'payoff_date': date or None (None if MAX_PERIODS reached without payoff),
        'total_interest': float,
        'reconciliation': [{date, predicted_balance, reported_balance, delta,
                             delta_pct}, ...] — one entry per snapshot actually
                            replayed, capturing what this track had already
                            computed for that date immediately before the
                            snapshot overwrote it. Sprint 29.
    }
    """
    if start_override:
        anchor_key = (start_override['date'].year, start_override['date'].month)
        rate_changes = [rc for rc in rate_changes
                         if (rc['effective_date'].year, rc['effective_date'].month) > anchor_key]
        snapshots = [s for s in snapshots
                     if (s['effective_date'].year, s['effective_date'].month) > anchor_key]
        extra_payments = [p for p in extra_payments
                           if (p['date'].year, p['date'].month) >= anchor_key]

    # Sorted by effective_date first, then created_at/id as a deterministic
    # tiebreaker for same-day events (2026-08-24, BUG-20) — see module
    # docstring.
    rate_changes = sorted(rate_changes, key=lambda e: (e['effective_date'], e.get('created_at'), e.get('id')))
    snapshots = sorted(snapshots, key=lambda e: (e['effective_date'], e.get('created_at'), e.get('id')))
    # Keyed by (year, month), each value a list of {date, amount} rather than
    # a pre-summed total — a snapshot pinned in the same period as one of
    # these needs each payment's exact date to tell whether the bank's
    # reported balance already reflects it (see the pinned_this_period_at
    # handling below; this fixes a real double-count bug found 2026-08-07).
    extra_by_period = {}
    if include_extra_payments:
        for p in extra_payments:
            key = (p['date'].year, p['date'].month)
            extra_by_period.setdefault(key, []).append(p)

    if start_override:
        balance = float(start_override['balance'])
        rate_pct = float(start_override['rate_pct'])
        current_date = start_override['date']
        installment = float(start_override['installment'])
    else:
        balance = float(loan['principal'])
        rate_pct = float(loan['margin_pct']) + float(loan['initial_base_index_pct'])
        current_date = loan['start_date']
        installment = calculate_installment(balance, monthly_rate(rate_pct), loan['original_term_months'])

    rate_idx = 0
    snap_idx = 0
    periods = []
    reconciliation = []
    total_interest = 0.0
    payoff_date = None

    for _ in range(MAX_PERIODS):
        # Snapshot: hard pin, applied before anything else this period if due
        pinned_this_period_at = None
        pinned_after_anchor = False
        while (snap_idx < len(snapshots) and
               (snapshots[snap_idx]['effective_date'].year, snapshots[snap_idx]['effective_date'].month)
               <= (current_date.year, current_date.month)):
            s = snapshots[snap_idx]
            predicted_balance = balance
            reported_balance = float(s['remaining_principal'])
            delta = reported_balance - predicted_balance
            # Total remaining interest ("Dobanda") from the chart — reporting
            # only, same as reported_balance; never used to hard-pin the
            # amortization math itself (unlike remaining_principal/
            # current_rate_pct/remaining_term_months above), and optional
            # since older snapshots logged before this field existed won't
            # have it.
            reported_remaining_interest = (
                float(s['remaining_interest_total'])
                if s.get('remaining_interest_total') is not None else None
            )
            reconciliation.append({
                'date': s['effective_date'],
                'predicted_balance': round(predicted_balance, 2),
                'reported_balance': round(reported_balance, 2),
                'delta': round(delta, 2),
                'delta_pct': round((delta / predicted_balance) * 100, 2) if predicted_balance else None,
                'reported_remaining_interest': round(reported_remaining_interest, 2) if reported_remaining_interest is not None else None,
            })
            balance = reported_balance
            rate_pct = float(s['current_rate_pct'])
            # Prefer the bank's own stated installment when the chart
            # provided one — remaining_term_months is an integer
            # approximation of the bank's more precise internal figure, so
            # re-deriving via the formula drifts slightly from what's
            # actually charged whenever the rate hasn't genuinely changed
            # (added 2026-08-12, alongside chart_parser.py's new
            # reported_installment field). Falls back to the formula for
            # snapshots that don't have this field (older ones, or entered
            # without a parsed chart).
            reported_installment = s.get('reported_installment')
            if reported_installment is not None:
                installment = float(reported_installment)
            else:
                installment = calculate_installment(balance, monthly_rate(rate_pct), float(s['remaining_term_months']))
            pinned_this_period_at = s['effective_date']
            # Bug fixed 2026-08-12 (same session as the calendar-month
            # bucketing fix above, found immediately after deploying it):
            # a snapshot dated AFTER this period's own anchor day (e.g.
            # anchor the 11th, chart generated the 12th) was generated by
            # the bank *after* this period's scheduled payment already
            # happened — its reported balance already reflects that
            # payment. The bucketing fix alone still went on to subtract
            # this period's scheduled_principal a second time on top,
            # double-counting the same payment this exact function already
            # guards against for extra payments (2026-08-07 fix, below).
            # Tracked here so balance_end skips that second subtraction
            # when it applies.
            pinned_after_anchor = s['effective_date'] > current_date
            snap_idx += 1

        # Rate change: recalculate installment, remaining term derived, not tracked
        while rate_idx < len(rate_changes) and rate_changes[rate_idx]['effective_date'] <= current_date:
            rc = rate_changes[rate_idx]
            old_monthly_r = monthly_rate(rate_pct)
            remaining = derive_remaining_periods(balance, installment, old_monthly_r)
            new_rate_pct = float(loan['margin_pct']) + float(rc['new_base_index_pct'])
            new_monthly_r = monthly_rate(new_rate_pct)
            if remaining is not None and remaining > 0:
                installment = calculate_installment(balance, new_monthly_r, remaining)
            rate_pct = new_rate_pct
            rate_idx += 1

        monthly_r = monthly_rate(rate_pct)
        interest = balance * monthly_r
        scheduled_principal = installment - interest
        period_payments = extra_by_period.get((current_date.year, current_date.month), [])
        if pinned_this_period_at is not None:
            # A snapshot pinned this period: its reported balance already
            # reflects any extra payment the bank had processed by that
            # date, so only count payments made after the chart's own date
            # to avoid subtracting the same real payment twice.
            extra_paid = sum(float(p['amount']) for p in period_payments if p['date'] > pinned_this_period_at)
        else:
            extra_paid = sum(float(p['amount']) for p in period_payments)

        if pinned_after_anchor:
            # This period's scheduled payment is already reflected in the
            # pinned balance (see the fix note above) — don't subtract it
            # again. interest/scheduled_principal are still recorded below
            # for continuity with every other period's record, computed
            # against the pinned (already-reduced) balance rather than the
            # true pre-payment one — a small, accepted approximation for
            # this one period only, not worth the added complexity of
            # reconstructing the exact pre-payment split from the reported
            # figure alone.
            balance_end = balance - extra_paid
        else:
            balance_end = balance - scheduled_principal - extra_paid
        total_interest += interest

        periods.append({
            'date': current_date,
            'balance_start': round(balance, 2),
            'rate_pct': round(rate_pct, 3),
            'installment': round(installment, 2),
            'interest': round(interest, 2),
            'scheduled_principal': round(scheduled_principal, 2),
            'extra_paid': round(extra_paid, 2),
            'balance_end': round(max(balance_end, 0), 2),
        })

        if balance_end <= 0:
            payoff_date = current_date
            break

        balance = balance_end
        current_date = _add_month(current_date)

    return {
        'periods': periods,
        'payoff_date': payoff_date,
        'total_interest': round(total_interest, 2),
        'reconciliation': reconciliation,
    }


def _add_month(d):
    if d.month == 12:
        return date(d.year + 1, 1, d.day)
    try:
        return date(d.year, d.month + 1, d.day)
    except ValueError:
        # day doesn't exist in the next month (e.g. Jan 31 -> Feb) — clamp
        # to that month's last day rather than raising.
        next_month = d.month + 1
        first_of_month_after = date(d.year, next_month + 1, 1) if next_month < 12 else date(d.year + 1, 1, 1)
        from datetime import timedelta
        return first_of_month_after - timedelta(days=1)
