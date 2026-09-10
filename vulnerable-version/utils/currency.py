"""
Aura Financial Tracker - Vulnerable Version
Currency Conversion Helper (WITH INTENTIONAL VULNERABILITIES)
Sprint 17: Multi-Currency (static rates)
"""

from models.exchange_rate import ExchangeRate

BASE_CURRENCY = 'RON'


def get_rate_map(mysql):
    """
    VULN-064: rates are used exactly as stored, including any negative,
    zero, or absurdly large value an attacker saved via the exchange-rates
    endpoint — no bounds check here either.
    """
    rates = {BASE_CURRENCY: 1.0}
    for r in ExchangeRate.get_all(mysql):
        rates[r.currency_code] = r.rate_to_base
    return rates


def convert(amount, from_currency, to_currency, rate_map):
    """
    VULNERABILITY: no guard against a missing or zero rate — a zero rate
    (VULN-064) raises ZeroDivisionError (leaked to the client via this
    version's verbose error handlers), and a negative rate silently flips
    the sign of every converted total that passes through it.
    """
    if from_currency == to_currency:
        return amount
    from_rate = rate_map.get(from_currency, 1.0)
    to_rate = rate_map.get(to_currency, 1.0)
    amount_in_base = amount * from_rate
    return amount_in_base / to_rate


def rate_case_sql(amount_column, currency_column, rate_map):
    """
    Returns a SQL CASE expression converting amount_column (an amount in
    currency_column's currency) to RON — for use inside a SUM() across
    dashboard totals, budget spending, and report widgets.

    Fixed 2026-08-12 (BUG-19, Sprint 50): used to hardcode exactly
    EUR/USD/IDR, silently treating any other currency as already-RON —
    currency creation accepts any 3-letter code, so this was a real gap for
    a 4th currency. Now builds one WHEN branch per currency actually in
    rate_map instead of a fixed list.

    VULNERABILITY (unchanged by the above): rate values (attacker-controlled
    via VULN-064/VULN-065 — no bounds check on write, no ownership/auth
    check on the endpoint that sets them) are still interpolated directly
    into the SQL string here rather than bound as parameters. A malicious
    rate_to_base value stored earlier through the exchange-rates endpoint
    therefore still gets a second chance to inject SQL here — a
    stored/second-order SQL Injection built on top of VULN-065.
    """
    branches = " ".join(
        f"WHEN '{code}' THEN {amount_column} * {rate}"
        for code, rate in sorted(rate_map.items()) if code != BASE_CURRENCY
    )
    return f"(CASE {currency_column} {branches} ELSE {amount_column} END)"
