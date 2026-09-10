"""
Aura Financial Tracker - Secure Version
OFX (Open Financial Exchange) Parser
Sprint 18: Data Import Expansion

Security properties (contrast with vulnerable-version/utils/ofx_parser.py):
- Uses defusedxml, which disables DTD processing and external entity
  resolution — the standard Python defense against XXE (external entity
  file disclosure / SSRF) and entity-expansion ("billion laughs") DoS.
  Plain xml.etree.ElementTree is not vulnerable to classic XXE either, but
  defusedxml additionally blocks entity-expansion DoS that ElementTree
  alone does not, so it's used here rather than relying on that default.
"""

import re
from datetime import datetime
from defusedxml import ElementTree as ET

MAX_TRANSACTIONS = 1000


def _normalize_sgml(content):
    """
    Best-effort OFX 1.x (SGML) -> well-formed XML normalization: strips the
    plain-text header block before <OFX>, and auto-closes tags that have
    inline content but no closing tag on the same line. OFX 2.x (already
    well-formed XML) passes through unchanged.
    """
    match = re.search(r'<OFX>', content, re.IGNORECASE)
    if match:
        content = content[match.start():]
    return re.sub(r'<([A-Za-z0-9.]+)>([^<\r\n]+)\r?\n', r'<\1>\2</\1>\n', content)


def parse_ofx(content):
    """
    Parses OFX statement content into a list of dicts:
    {date (ISO string), amount (float, OFX sign preserved), description,
    external_id}. Caller converts the amount's sign into this app's
    income/expense type. Raises ValueError on unparseable content.
    """
    try:
        root = ET.fromstring(_normalize_sgml(content))
    except Exception as e:
        raise ValueError(f"Could not parse OFX file: {e}")

    transactions = []
    for stmttrn in root.iter('STMTTRN'):
        if len(transactions) >= MAX_TRANSACTIONS:
            break

        date_el = stmttrn.find('DTPOSTED')
        amount_el = stmttrn.find('TRNAMT')
        if date_el is None or amount_el is None:
            continue

        raw_date = (date_el.text or '').strip()[:8]  # YYYYMMDD, ignore any time/timezone suffix
        try:
            parsed_date = datetime.strptime(raw_date, '%Y%m%d').date()
        except ValueError:
            continue

        try:
            amount = float((amount_el.text or '').strip())
        except (TypeError, ValueError):
            continue

        name_el = stmttrn.find('NAME')
        memo_el = stmttrn.find('MEMO')
        fitid_el = stmttrn.find('FITID')

        description = (
            (name_el.text if name_el is not None else None)
            or (memo_el.text if memo_el is not None else None)
            or 'OFX import'
        )
        external_id = (fitid_el.text or '').strip() if fitid_el is not None and fitid_el.text else None

        transactions.append({
            'date': parsed_date.isoformat(),
            'amount': amount,
            'description': description.strip()[:255],
            'external_id': external_id,
        })

    return transactions
