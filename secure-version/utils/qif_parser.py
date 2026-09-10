"""
Aura Financial Tracker - Secure Version
QIF (Quicken Interchange Format) Parser
Sprint 18: Data Import Expansion

QIF is a plain-text, line-based format — no XML/XXE surface here. The
main risks are unbounded input (capped via MAX_TRANSACTIONS, same as the
OFX parser) and malformed date/amount values, both handled defensively:
a record with an unparseable date or amount is skipped rather than
raising, so one bad record in a file doesn't abort the whole import.
"""

from datetime import datetime

MAX_TRANSACTIONS = 1000

_DATE_FORMATS = ('%m/%d/%Y', "%m/%d'%y", '%m/%d/%y')


def _parse_qif_date(raw):
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _finalize_record(fields):
    raw_date = fields.get('date')
    raw_amount = fields.get('amount')
    if not raw_date or raw_amount is None:
        return None

    parsed_date = _parse_qif_date(raw_date)
    if not parsed_date:
        return None

    try:
        amount = float(raw_amount.replace(',', ''))
    except (TypeError, ValueError):
        return None

    description = fields.get('payee') or fields.get('memo') or 'QIF import'
    category_name = fields.get('category')

    return {
        'date': parsed_date.isoformat(),
        'amount': amount,
        'description': description.strip()[:255],
        'category_name': category_name.strip()[:100] if category_name else None,
    }


def parse_qif(content):
    """
    Parses QIF Bank/Cash/CCard transaction records (D/T/P/L/M field codes,
    records separated by a lone '^') into a list of dicts:
    {date, amount, description, category_name}. QIF has no per-transaction
    unique ID (unlike OFX's FITID) — imported transactions never get an
    external_id, so re-importing the same file is not deduplicated, same
    as the existing CSV import's behavior.
    """
    transactions = []
    current = {}

    for line in content.splitlines():
        line = line.rstrip('\r\n')
        if not line or line.startswith('!'):
            continue  # header/type lines (e.g. "!Type:Bank") — not a field we need

        code, value = line[0], line[1:].strip()

        if code == '^':
            if current:
                tx = _finalize_record(current)
                if tx:
                    transactions.append(tx)
                    if len(transactions) >= MAX_TRANSACTIONS:
                        break
            current = {}
        elif code == 'D':
            current['date'] = value
        elif code in ('T', 'U'):
            current['amount'] = value
        elif code == 'P':
            current['payee'] = value
        elif code == 'M':
            current['memo'] = value
        elif code == 'L':
            current['category'] = value.split('/')[0]  # drop QIF's optional class suffix
        # other field codes (N, A, etc.) intentionally ignored — out of scope

    return transactions
