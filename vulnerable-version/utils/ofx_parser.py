"""
Aura Financial Tracker - Vulnerable Version
OFX (Open Financial Exchange) Parser (WITH INTENTIONAL VULNERABILITIES)
Sprint 18: Data Import Expansion

VULN-067: genuine XXE via lxml.etree with unhardened settings. lxml's
XMLParser defaults to resolve_entities=True (unlike every parser in
Python's standard library — see the correction history below for two
earlier, empirically-disproven attempts at stdlib-based XXE that don't
work on modern CPython/expat). This mirrors how XXE actually shows up in
real-world Python apps today: rarely stdlib, almost always a third-party
library like lxml (commonly pulled in for speed/features over ElementTree)
whose defaults differ from stdlib and go unnoticed.

resolve_entities and no_network are both set explicitly below (rather than
relying on ambient defaults, which vary by lxml version) so this stays
reliably exploitable: a crafted OFX file containing e.g.
    <!DOCTYPE OFX [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
and a field referencing &xxe; will have that file's contents substituted
into the parsed tree (file disclosure), or an "http://" SYSTEM URL used
for SSRF against internal services.

Also still true regardless of which parser is used: no file-size or
record-count limit (see the "no cap" comment in parse_ofx below) — unlike
secure-version's MAX_TRANSACTIONS + Config.MAX_CONTENT_LENGTH caps.

Correction history (both verified empirically during Sprint 18 testing,
kept here so the reasoning isn't repeated by mistake later):
1. Originally documented as classic external-entity XXE via xml.dom.
   minidom (file disclosure via <!ENTITY xxe SYSTEM "file:///etc/passwd">).
   Wrong — Python's expat (which minidom, xml.sax, and ElementTree all sit
   on top of) only resolves *external* entities if the caller explicitly
   registers an ExternalEntityRefHandler, which none of these stdlib
   wrappers do.
2. Then reframed as internal entity-expansion ("billion laughs") DoS via
   minidom. Also wrong on this Python version — expat has enforced a
   built-in amplification-ratio limit by default since ~2021
   (CVE-2013-0340 remediation, bundled in expat 2.4.0+), independent of
   anything the Python-level code does, so nested-entity payloads are
   rejected before they can expand.
Switching to lxml (a real third-party dependency, not stdlib) is what
makes the XXE genuinely exploitable again.
"""

import re
from datetime import datetime
from lxml import etree


def _normalize_sgml(content):
    """
    OFX 1.x (SGML) -> XML normalization. Strips the plain-text SGML header
    block (e.g. "OFXHEADER:100\\nDATA:OFXSGML\\n...") that precedes <OFX> in
    legacy files — but only when that prefix isn't itself a DOCTYPE, so a
    file that already has a DTD (whether a legitimate one or the VULN-067
    XXE payload above) reaches the parser intact instead of being stripped.
    """
    match = re.search(r'<OFX>', content, re.IGNORECASE)
    if match:
        prefix = content[:match.start()]
        if not re.search(r'<!DOCTYPE', prefix, re.IGNORECASE):
            content = content[match.start():]
    return re.sub(r'<([A-Za-z0-9.]+)>([^<\r\n]+)\r?\n', r'<\1>\2</\1>\n', content)


def _text(el, tag):
    child = el.find(tag)
    return child.text if child is not None else None


def parse_ofx(content):
    """
    VULNERABILITY: XXE — lxml.etree.XMLParser configured with
    resolve_entities=True and no_network=False (both explicit, not left to
    version-dependent defaults) resolves DTD-declared entities, including
    external SYSTEM entities, with no hardening applied (no
    resolve_entities=False, no defusedxml).
    """
    normalized = _normalize_sgml(content)
    parser = etree.XMLParser(resolve_entities=True, no_network=False)  # VULN: unhardened
    try:
        root = etree.fromstring(normalized.encode('utf-8'), parser=parser)
    except Exception as e:
        raise ValueError(f"Could not parse OFX file: {e}")

    # VULN: no cap on record count — matches the existing CSV import's lack
    # of any file-size/row-count limit (memory-exhaustion DoS via a huge file)
    transactions = []
    for stmttrn in root.iter('STMTTRN'):
        raw_date = (_text(stmttrn, 'DTPOSTED') or '').strip()[:8]
        try:
            parsed_date = datetime.strptime(raw_date, '%Y%m%d').date()
        except ValueError:
            continue

        try:
            amount = float((_text(stmttrn, 'TRNAMT') or '').strip())
        except (TypeError, ValueError):
            continue

        description = (
            _text(stmttrn, 'NAME')
            or _text(stmttrn, 'MEMO')
            or 'OFX import'
        )
        external_id = _text(stmttrn, 'FITID')

        transactions.append({
            'date': parsed_date.isoformat(),
            'amount': amount,
            'description': description,
            'external_id': external_id,
        })

    return transactions
