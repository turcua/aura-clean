"""
Aura Financial Tracker - Secure Version
Export/Import API Routes
Sprint 14: Export/Import + Reports + Multi-Dashboard System

Security properties (contrast with vulnerable-version/routes/api/export.py):
- Every route requires @api_login_required; user_id always comes from session,
  never from a query/form param — vulnerable's IDOR lets ?user_id=<anyone> pull
  or import into any account
- Every query parameterized — no f-string SQL anywhere
- CSV/Excel cell values are formula-escaped (a value starting with =, +, -, or
  @ gets a leading apostrophe) before being written — vulnerable writes raw
  transaction descriptions straight into cells (CSV/Excel formula injection,
  e.g. description = "=cmd|' /C calc'!A0")
- CSV import validates the file extension, enforces Config.MAX_CONTENT_LENGTH
  (5 MB) at the Flask level, validates every field (date, type, amount) before
  insert, and looks up categories by name scoped to the session user's visible
  categories (own + defaults) — never auto-creates rows from unvalidated input
- Error messages are generic — no raw exception text or DB schema details are
  ever returned to the client (vulnerable's import endpoint echoes str(e) per
  failed row, leaking column/table names)
"""

import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, session, current_app
from models.transaction import Transaction
from models.account import Account
from routes.main import api_login_required
from utils.currency import get_rate_map, rate_case_sql, rate_case_params
from utils.ofx_parser import parse_ofx
from utils.qif_parser import parse_qif

api_export_bp = Blueprint('api_export', __name__)

ALLOWED_IMPORT_EXTENSIONS = ('.csv', '.txt')
ALLOWED_OFX_EXTENSIONS = ('.ofx', '.qfx')
ALLOWED_QIF_EXTENSIONS = ('.qif',)


def get_mysql():
    return current_app.extensions['mysql']


def _sanitize_cell(value):
    """Neutralizes CSV/Excel formula injection: a leading apostrophe forces
    spreadsheet apps to treat the cell as literal text instead of a formula."""
    s = str(value) if value is not None else ''
    if s and s[0] in ('=', '+', '-', '@'):
        return "'" + s
    return s


def fetch_transactions(mysql, user_id, date_from=None, date_to=None, type=None, account_id=None):
    cursor = mysql.connection.cursor()
    query = (
        "SELECT t.id, t.transaction_date, t.type, t.amount, t.description, "
        "c.name AS category_name, a.name AS account_name, COALESCE(a.currency, 'RON') AS currency "
        "FROM transactions t "
        "LEFT JOIN categories c ON t.category_id = c.id "
        "LEFT JOIN accounts a ON t.account_id = a.id "
        "WHERE t.user_id = %s"
    )
    params = [user_id]
    if date_from:
        query += " AND t.transaction_date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND t.transaction_date <= %s"
        params.append(date_to)
    if type in ('income', 'expense'):
        query += " AND t.type = %s"
        params.append(type)
    if account_id:
        query += " AND t.account_id = %s"
        params.append(account_id)
    query += " ORDER BY t.transaction_date DESC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    return rows


# ============================================================================
# EXPORT CSV
# ============================================================================
@api_export_bp.route('/csv', methods=['GET'])
@api_login_required
def export_csv():
    try:
        user_id = session['user_id']
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')
        account_id = request.args.get('account_id')

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter, account_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account'])

        for row in rows:
            writer.writerow([
                row[0], row[1], row[2], row[3], row[7],
                _sanitize_cell(row[4]), _sanitize_cell(row[5] or ''), _sanitize_cell(row[6] or '')
            ])

        output.seek(0)
        filename = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception:
        return jsonify({'success': False, 'message': 'Export error'}), 500


# ============================================================================
# EXPORT PDF
# ============================================================================
@api_export_bp.route('/pdf', methods=['GET'])
@api_login_required
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        user_id = session['user_id']
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("Aura Financial Tracker - Transaction Report", styles['Title']),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']),
        ]

        table_data = [['Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account']]
        for row in rows:
            table_data.append([
                str(row[1]), str(row[2]), f"{float(row[3]):.2f}", str(row[7]),
                _sanitize_cell(row[4]), _sanitize_cell(row[5] or ''), _sanitize_cell(row[6] or '')
            ])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4338ca')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)

        filename = f"transactions_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception:
        return jsonify({'success': False, 'message': 'PDF export error'}), 500


# ============================================================================
# EXPORT EXCEL
# ============================================================================
@api_export_bp.route('/excel', methods=['GET'])
@api_login_required
def export_excel():
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill

        user_id = session['user_id']
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')
        account_id = request.args.get('account_id')

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter, account_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"

        ws.append(['ID', 'Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account'])
        header_fill = PatternFill(start_color="4338CA", end_color="4338CA", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill

        for row in rows:
            ws.append([
                row[0], str(row[1]), row[2], float(row[3] or 0), row[7],
                _sanitize_cell(row[4]), _sanitize_cell(row[5] or ''), _sanitize_cell(row[6] or '')
            ])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"transactions_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception:
        return jsonify({'success': False, 'message': 'Excel export error'}), 500


# ============================================================================
# IMPORT CSV
# ============================================================================
@api_export_bp.route('/import/csv', methods=['POST'])
@api_login_required
def import_csv():
    try:
        user_id = session['user_id']

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        if not file.filename.lower().endswith(ALLOWED_IMPORT_EXTENSIONS):
            return jsonify({'success': False, 'message': 'Only .csv or .txt files are accepted'}), 400

        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({'success': False, 'message': 'File must be UTF-8 encoded text'}), 400

        reader = csv.DictReader(io.StringIO(content))

        mysql = get_mysql()
        imported = 0
        errors = []

        for i, row in enumerate(reader, start=2):
            if imported + len(errors) >= 1000:
                errors.append(f"Row {i}: import limit of 1000 rows reached, stopping")
                break
            try:
                date_str = (row.get('Date') or row.get('date') or '').strip()
                type_ = (row.get('Type') or row.get('type') or 'expense').strip().lower()
                amount_raw = row.get('Amount') or row.get('amount') or '0'
                description = (row.get('Description') or row.get('description') or '').strip()[:255]
                category_name = (row.get('Category') or row.get('category') or '').strip()

                if type_ not in ('income', 'expense'):
                    errors.append(f"Row {i}: type must be income or expense")
                    continue
                try:
                    amount = round(float(amount_raw), 2)
                except (TypeError, ValueError):
                    errors.append(f"Row {i}: invalid amount")
                    continue
                if amount < 0:
                    errors.append(f"Row {i}: amount must be non-negative")
                    continue
                if not date_str:
                    errors.append(f"Row {i}: date is required")
                    continue

                category_id = None
                if category_name:
                    category_id = _find_category_id(mysql, user_id, category_name, type_)

                success, message, _ = Transaction.create(
                    mysql, user_id, category_id, type_, amount, description, date_str
                )
                if success:
                    imported += 1
                else:
                    errors.append(f"Row {i}: could not import")
            except Exception:
                errors.append(f"Row {i}: invalid data")
                continue

        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {imported} transactions'
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Import error'}), 500


def _find_category_id(mysql, user_id, name, type_):
    """Looks up a category visible to user_id (own or system default) by name+type. No auto-create."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id FROM categories WHERE name = %s AND type = %s "
            "AND (user_id = %s OR (is_default = TRUE AND user_id IS NULL)) LIMIT 1",
            (name, type_, user_id)
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    except Exception:
        return None


# ============================================================================
# IMPORT OFX
# ============================================================================
@api_export_bp.route('/import/ofx', methods=['POST'])
@api_login_required
def import_ofx():
    """
    OFX statements are inherently tied to one account (Sprint 18 scope
    decision) — account_id is required and validated as owned by the
    session user before anything is imported into it.
    """
    try:
        user_id = session['user_id']

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        if not file.filename.lower().endswith(ALLOWED_OFX_EXTENSIONS):
            return jsonify({'success': False, 'message': 'Only .ofx or .qfx files are accepted'}), 400

        try:
            account_id = int(request.form.get('account_id'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'account_id is required'}), 400

        mysql = get_mysql()
        account = Account.get_by_id(mysql, account_id, user_id)
        if not account:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400

        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({'success': False, 'message': 'File must be UTF-8 encoded text'}), 400

        try:
            parsed = parse_ofx(content)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400

        imported = 0
        skipped_duplicate = 0
        errors = []

        for i, tx in enumerate(parsed, start=1):
            try:
                tx_type = 'income' if tx['amount'] >= 0 else 'expense'
                amount = round(abs(tx['amount']), 2)

                success, message, _ = Transaction.create(
                    mysql, user_id, None, tx_type, amount, tx['description'], tx['date'],
                    account_id=account_id, external_id=tx['external_id']
                )
                if success:
                    imported += 1
                elif 'external_id already exists' in message:
                    skipped_duplicate += 1
                else:
                    errors.append(f"Transaction {i}: could not import")
            except Exception:
                errors.append(f"Transaction {i}: invalid data")
                continue

        return jsonify({
            'success': True,
            'imported': imported,
            'skipped_duplicate': skipped_duplicate,
            'errors': errors,
            'message': f'Imported {imported} transactions ({skipped_duplicate} duplicates skipped)'
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Import error'}), 500


# ============================================================================
# IMPORT QIF
# ============================================================================
@api_export_bp.route('/import/qif', methods=['POST'])
@api_login_required
def import_qif():
    """
    Same account-ownership requirement as /import/ofx (Sprint 18 scope
    decision). QIF has no per-transaction unique ID, so unlike OFX there is
    no dedup here — re-importing the same file creates duplicate rows, same
    as CSV import.
    """
    try:
        user_id = session['user_id']

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        if not file.filename.lower().endswith(ALLOWED_QIF_EXTENSIONS):
            return jsonify({'success': False, 'message': 'Only .qif files are accepted'}), 400

        try:
            account_id = int(request.form.get('account_id'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'account_id is required'}), 400

        mysql = get_mysql()
        account = Account.get_by_id(mysql, account_id, user_id)
        if not account:
            return jsonify({'success': False, 'message': 'Invalid account'}), 400

        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({'success': False, 'message': 'File must be UTF-8 encoded text'}), 400

        parsed = parse_qif(content)

        imported = 0
        errors = []

        for i, tx in enumerate(parsed, start=1):
            try:
                tx_type = 'income' if tx['amount'] >= 0 else 'expense'
                amount = round(abs(tx['amount']), 2)

                category_id = None
                if tx['category_name']:
                    category_id = _find_category_id(mysql, user_id, tx['category_name'], tx_type)

                success, message, _ = Transaction.create(
                    mysql, user_id, category_id, tx_type, amount, tx['description'], tx['date'],
                    account_id=account_id
                )
                if success:
                    imported += 1
                else:
                    errors.append(f"Transaction {i}: could not import")
            except Exception:
                errors.append(f"Transaction {i}: invalid data")
                continue

        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {imported} transactions'
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Import error'}), 500


# ============================================================================
# REPORTS - Summary Data
# ============================================================================
@api_export_bp.route('/reports/summary', methods=['GET'])
@api_login_required
def reports_summary():
    try:
        user_id = session['user_id']
        date_from = request.args.get('date_from', '2020-01-01')
        date_to = request.args.get('date_to', '2099-12-31')

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()

        # by_category and by_month aggregate across every account, so mixed
        # currencies are converted to RON first (Sprint 17, MC-006) — same
        # treatment as reports_data.py's income_expense/expense_distribution.
        cursor.execute(
            f"SELECT c.name, t.type, SUM({case_sql}) AS total, COUNT(*) AS count "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.is_transfer = FALSE AND t.transaction_date BETWEEN %s AND %s "
            f"GROUP BY c.name, t.type ORDER BY total DESC",
            tuple(rate_case_params(rate_map) + [user_id, date_from, date_to])
        )
        by_category = [{'category': r[0] or 'Uncategorized', 'type': r[1], 'total': float(r[2]), 'count': r[3]}
                        for r in cursor.fetchall()]

        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, "
            f"SUM(CASE WHEN t.type='income' THEN {case_sql} ELSE 0 END) AS income, "
            f"SUM(CASE WHEN t.type='expense' THEN {case_sql} ELSE 0 END) AS expenses "
            f"FROM transactions t "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.is_transfer = FALSE AND t.transaction_date BETWEEN %s AND %s "
            f"GROUP BY month ORDER BY month",
            tuple(rate_case_params(rate_map) * 2 + [user_id, date_from, date_to])
        )
        by_month = [{'month': r[0], 'income': float(r[1]), 'expenses': float(r[2])} for r in cursor.fetchall()]

        # by_account groups by a single account, so each row is already in
        # one currency — no conversion needed, just surface it for display.
        cursor.execute(
            "SELECT a.name, SUM(CASE WHEN t.type='income' THEN t.amount ELSE 0 END) AS income, "
            "SUM(CASE WHEN t.type='expense' THEN t.amount ELSE 0 END) AS expenses, "
            "COALESCE(a.currency, 'RON') AS currency "
            "FROM transactions t "
            "LEFT JOIN accounts a ON t.account_id = a.id "
            "WHERE t.user_id = %s AND t.is_transfer = FALSE AND t.transaction_date BETWEEN %s AND %s "
            "GROUP BY a.name, a.currency",
            (user_id, date_from, date_to)
        )
        by_account = [{'account': r[0] or 'No Account', 'income': float(r[1]), 'expenses': float(r[2]), 'currency': r[3]}
                      for r in cursor.fetchall()]

        cursor.close()

        return jsonify({
            'success': True, 'by_category': by_category, 'by_month': by_month, 'by_account': by_account
        }), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Report error'}), 500
