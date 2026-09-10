"""
Aura Financial Tracker
Bank Chart PDF Parser
Sprint 30 (extension): Loan Intelligence — Bank Chart Upload Assist

Pure text extraction + best-effort field guessing. Never trusted blindly —
the caller always surfaces both the raw extracted text and the guessed
fields as pre-filled, still-editable form inputs, so a human confirms or
corrects before anything is saved. Identical in both versions, same
rationale as utils/loan_engine.py: this is not a vulnerable/secure
contrast point.
"""

import re
from datetime import datetime

import pdfplumber


def extract_text(file_stream):
    """Returns the full extracted text from a PDF file stream."""
    text_parts = []
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or '')
    return '\n'.join(text_parts)


def guess_chart_fields(text):
    """
    Best-effort regex guesses over common Romanian bank amortization chart
    terminology. Deliberately approximate — real chart layouts vary (even
    across exports from the same bank, per the Release 8 design
    conversation), so this is an assist, not an authority. The caller always
    shows the raw text alongside these guesses.
    """
    guesses = {
        'remaining_principal': None,
        'remaining_term_months': None,
        'current_rate_pct': None,
        'remaining_interest_total': None,
        'reported_installment': None,
        'effective_date': None,
    }

    # "Numar Rate" / "Nr. Rate" — remaining installment count, a real,
    # confirmed label from the user's actual bank charts (Banca Transilvania
    # format: "Numar rate: 179").
    m = re.search(r'(?:Numar|Nr\.?)\s*[Rr]ate\w*[:\s]+(\d+)', text)
    if m:
        guesses['remaining_term_months'] = int(m.group(1))

    # Total interest rate — Banca Transilvania's "Procent dobanda: 7.56"
    # (no % sign at all), falling back to a generic "Dobanda: X%" form for
    # other bank layouts.
    m = re.search(r'Procent\s+doband[aă][:\s]+([\d.,]+)', text, re.IGNORECASE)
    if not m:
        m = re.search(r'Dob[aâ]nd[aă]\w*[:\s]+([\d.,]+)\s*%', text, re.IGNORECASE)
    if m:
        guesses['current_rate_pct'] = _parse_number(m.group(1))

    # Remaining principal — Banca Transilvania charts have no standalone
    # "Sold: X" label; the reliable figure is the "Total RON:" summary
    # row's principal-sum column, which by construction equals the total
    # remaining balance (sum of every remaining row's principal portion).
    # Falls back to a labeled "Sold" figure for other bank layouts.
    m = re.search(r'Total\s+RON:\s*[\d.,]+\s+([\d.,]+)', text, re.IGNORECASE)
    if not m:
        m = re.search(r'Sold\w*[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if m:
        guesses['remaining_principal'] = _parse_number(m.group(1))

    # Remaining total interest ("Dobanda") — the Total RON: row's third
    # number, immediately after the principal-sum column captured above.
    # Confirmed against a real chart: 402,837.97 (total remaining payments)
    # = 241,264.19 (remaining principal) + 161,573.78 (remaining interest) —
    # the arithmetic checks out exactly, confirming this is genuinely the
    # interest component, not a mislabeled duplicate of the balance.
    m = re.search(r'Total\s+RON:\s*[\d.,]+\s+[\d.,]+\s+([\d.,]+)', text, re.IGNORECASE)
    if m:
        guesses['remaining_interest_total'] = _parse_number(m.group(1))

    # Reported installment — the "TOTAL DE PLATA" figure on the chart's
    # very first payment row (row "1"), the bank's own already-fixed
    # payment amount. Added 2026-08-12: the engine used to always
    # *re-derive* the installment from (balance, rate, remaining_term_months)
    # via the amortization formula on every snapshot, but remaining_term_months
    # is an integer approximation of the bank's more precise internal figure,
    # so the re-derived value drifts slightly from what the bank actually
    # charges whenever the rate hasn't genuinely changed. Capturing the
    # bank's own stated figure directly avoids that drift — see
    # utils/loan_engine.py's project(), which now prefers this field over
    # calculate_installment() when present.
    m = re.search(r'^1\s+\d{1,2}-[A-Za-z]{3}-\d{4}\s+([\d.,]+)', text, re.MULTILINE)
    if m:
        guesses['reported_installment'] = _parse_number(m.group(1))

    # Effective date — Banca Transilvania's own chart-generation timestamp
    # ("Tiparit: /2026-07-29 19:02:13") is a far more reliable anchor than
    # guessing from a payment row, and matches the same "chart generation
    # date" convention already used for the real April 2025 snapshot.
    # Falls back to any dd.mm.yyyy / dd/mm/yyyy date found in the document.
    m = re.search(r'Tiparit:\s*/?(\d{4}-\d{2}-\d{2})', text)
    if m:
        guesses['effective_date'] = m.group(1)
    else:
        m = re.search(r'(\d{2}[./]\d{2}[./]\d{4})', text)
        if m:
            guesses['effective_date'] = _normalize_date(m.group(1))

    return guesses


def _parse_number(raw):
    """
    Handles both Romanian ('1.234,56') and US/plain ('1,234.56') number
    formats by treating whichever separator appears last as the decimal
    point — more robust than assuming one convention, since the user's real
    Banca Transilvania charts turned out to use the US style despite
    Romanian labels ('241,264.19', not '241.264,19').
    """
    raw = raw.strip()
    last_comma = raw.rfind(',')
    last_dot = raw.rfind('.')
    if last_comma > last_dot:
        raw = raw.replace('.', '').replace(',', '.')
    elif last_dot > last_comma:
        raw = raw.replace(',', '')
    try:
        return float(raw)
    except ValueError:
        return None


def _normalize_date(raw):
    for fmt in ('%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None
