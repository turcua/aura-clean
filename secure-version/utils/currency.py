"""
Aura Financial Tracker - Secure Version
Currency Conversion Helper
Sprint 17: Multi-Currency (static rates)

Converts amounts between RON (base) and EUR/USD/IDR using the rates stored
in exchange_rates. RON is the implicit base (1.0) and never stored as a row.
Rates are stored as "1 unit of currency = X RON", so converting between any
two currencies goes through RON as an intermediate step:
    amount_in_ron = amount * rate_to_base[from]
    result        = amount_in_ron / rate_to_base[to]
"""

from models.exchange_rate import ExchangeRate

BASE_CURRENCY = 'RON'


def get_rate_map(mysql):
    """Returns {currency_code: rate_to_base}, including the implicit RON = 1.0."""
    rates = {BASE_CURRENCY: 1.0}
    for r in ExchangeRate.get_all(mysql):
        rates[r.currency_code] = r.rate_to_base
    return rates


def _non_base_currencies(rate_map):
    """
    Fixed 2026-08-12 (BUG-19, Sprint 50): rate_case_sql()/rate_case_params()
    used to hardcode exactly EUR/USD/IDR, silently treating any other
    currency as already-RON in every aggregate query. Currency creation
    (POST /api/currencies/create) accepts any 3-letter code, so this was a
    real, live data-accuracy gap for anyone using a 4th currency. Both
    functions below now derive their currency list from rate_map itself
    (populated from the real `currencies`/`exchange_rates` tables via
    get_rate_map()) instead of a fixed list — sorted for a deterministic
    CASE/params order between the two functions.
    """
    return sorted(c for c in rate_map if c != BASE_CURRENCY)


def convert(amount, from_currency, to_currency, rate_map):
    """
    Converts `amount` from from_currency to to_currency using a pre-fetched
    rate_map (see get_rate_map). Returns None — rather than dividing by a
    missing rate — if either currency isn't present in rate_map.
    """
    if from_currency == to_currency:
        return amount
    from_rate = rate_map.get(from_currency)
    to_rate = rate_map.get(to_currency)
    if not from_rate or not to_rate:
        return None
    amount_in_base = amount * from_rate
    return amount_in_base / to_rate


def rate_case_sql(amount_column, currency_column, rate_map):
    """
    Returns a parameterized SQL CASE expression converting amount_column
    (an amount stored in currency_column's currency) to RON — for use inside
    a SUM() in queries that aggregate across possibly mixed-currency
    accounts (dashboard totals, budget spending, report widgets). Pair with
    rate_case_params() for the %s values it expects, in the same order —
    both now iterate _non_base_currencies(rate_map) so any currency actually
    in use gets a real WHEN branch, not just EUR/USD/IDR. RON and any value
    not in rate_map — including NULL, for transactions with no linked
    account — pass through unconverted via ELSE, which is correct since RON
    is the implicit base and un-linked transactions are treated as already
    being in RON.

    Signature changed 2026-08-12 (BUG-19): now takes rate_map directly
    (previously only rate_case_params() did) since the CASE branches
    themselves need to know which currencies exist, not just their rates.
    """
    branches = " ".join(f"WHEN '{code}' THEN {amount_column} * %s" for code in _non_base_currencies(rate_map))
    return f"(CASE {currency_column} {branches} ELSE {amount_column} END)"


def rate_case_params(rate_map):
    """Params for rate_case_sql(), in the same currency order (_non_base_currencies)."""
    return [rate_map[code] for code in _non_base_currencies(rate_map)]
