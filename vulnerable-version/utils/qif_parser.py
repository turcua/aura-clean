"""
Aura Financial Tracker - Vulnerable Version
QIF (Quicken Interchange Format) Parser (WITH INTENTIONAL VULNERABILITIES)
Sprint 18: Data Import Expansion

QIF is plain text, not XML — there's no injection surface in the parsing
itself (that lives in the import endpoint instead: VULN-068 SQL Injection,
VULN-069 IDOR on the destination account). The vulnerability here is what's
*missing*: no cap on record count, matching the existing CSV import's lack
of any file-size/row-count limit.
"""

from datetime import datetime

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
        'description': description,
        'category_name': category_name,
    }


def parse_qif(content):
    """VULN: no cap on record count — a huge file processes every record."""
    transactions = []
    current = {}

    for line in content.splitlines():
        line = line.rstrip('\r\n')
        if not line or line.startswith('!'):
            continue

        code, value = line[0], line[1:].strip()

        if code == '^':
            if current:
                tx = _finalize_record(current)
                if tx:
                    transactions.append(tx)
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
            current['category'] = value.split('/')[0]

    return transactions
