"""
Aura Financial Tracker - Vulnerable Version
Export/Import API Routes (WITH INTENTIONAL VULNERABILITIES)
Sprint 5: Shadow Ledger
"""

import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, session
from models.transaction import Transaction
from models.account import Account
from utils.currency import get_rate_map, rate_case_sql
from utils.ofx_parser import parse_ofx
from utils.qif_parser import parse_qif
from utils import flag_engine

api_export_bp = Blueprint('api_export', __name__)


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


def fetch_transactions(mysql, user_id, date_from=None, date_to=None, type=None, account_id=None):
    """
    VULNERABILITY: SQL Injection in all filter parameters
    VULNERABILITY: IDOR - user_id from request, not session
    """
    cursor = mysql.connection.cursor()
    # VULN: SQL Injection
    query = f"""
        SELECT t.id, t.transaction_date, t.type, t.amount, t.description,
               c.name as category_name, a.name as account_name,
               COALESCE(a.currency, 'RON') as currency
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN accounts a ON t.account_id = a.id
        WHERE t.user_id = {user_id}
    """
    if date_from:
        query += f" AND t.transaction_date >= '{date_from}'"
    if date_to:
        query += f" AND t.transaction_date <= '{date_to}'"
    if type:
        query += f" AND t.type = '{type}'"
    if account_id:
        query += f" AND t.account_id = {account_id}"
    query += " ORDER BY t.transaction_date DESC"
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return rows


# ============================================================================
# EXPORT CSV
# ============================================================================
@api_export_bp.route('/csv', methods=['GET'])
def export_csv():
    """
    Export transactions as CSV.
    VULNERABILITIES:
    - No authentication check
    - IDOR: user_id from query param, not session
    - SQL Injection in filter params
    - CSV Injection: transaction descriptions written raw (=CMD, @SUM, etc.)
    - No output sanitization
    """
    try:
        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')
        account_id = request.args.get('account_id')

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter, account_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account'])

        for row in rows:
            # VULN: CSV Injection - description written without sanitization
            # Payloads like =CMD|' /C calc'!A0 will execute in Excel
            writer.writerow([row[0], row[1], row[2], row[3], row[7], row[4], row[5] or '', row[6] or ''])

        output.seek(0)
        filename = f"transactions_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv"

        # Sprint 44 (VULN-044 flag): downloading someone else's export via
        # the user_id param, with zero authentication of any kind, is the
        # proof.
        attacker_id = session.get('user_id')
        if attacker_id and str(user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-044')

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        # VULN: Stack trace in response
        return jsonify({'success': False, 'message': f'Export error: {str(e)}'}), 500


# ============================================================================
# EXPORT PDF
# ============================================================================
@api_export_bp.route('/pdf', methods=['GET'])
def export_pdf():
    """
    Export transactions as PDF using reportlab.
    VULNERABILITIES:
    - No authentication check, IDOR, SQL Injection in filters
    - No output encoding (XSS-equivalent in PDF)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Aura Financial Tracker - Transaction Report", styles['Title']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"User ID: {user_id}", styles['Normal']))

        table_data = [['Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account']]
        for row in rows:
            table_data.append([
                str(row[1]), str(row[2]), f"{float(row[3]):.2f}", str(row[7]),
                str(row[4] or ''), str(row[5] or ''), str(row[6] or '')
            ])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.red),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightyellow]),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)

        filename = f"transactions_{user_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({'success': False, 'message': f'PDF export error: {str(e)}'}), 500


# ============================================================================
# EXPORT EXCEL
# ============================================================================
@api_export_bp.route('/excel', methods=['GET'])
def export_excel():
    """
    Export transactions as Excel (.xlsx) using openpyxl.
    VULNERABILITIES:
    - No authentication, IDOR, SQL Injection
    - CSV/Formula injection in Excel cells
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill

        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        type_filter = request.args.get('type')
        account_id = request.args.get('account_id')

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        mysql = get_mysql()
        rows = fetch_transactions(mysql, user_id, date_from, date_to, type_filter, account_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"

        headers = ['ID', 'Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Account']
        ws.append(headers)

        header_fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill

        for row in rows:
            # VULN: Formula injection - raw values written to cells
            ws.append([row[0], str(row[1]), row[2], float(row[3] or 0), row[7], row[4] or '', row[5] or '', row[6] or ''])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"transactions_{user_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'Excel export error: {str(e)}'}), 500


# ============================================================================
# IMPORT CSV
# ============================================================================
@api_export_bp.route('/import/csv', methods=['POST'])
def import_csv():
    """
    Import transactions from a CSV file.
    VULNERABILITIES:
    - No authentication check
    - No CSRF protection
    - No file type validation (any file accepted)
    - No file size limit
    - CSV content injected directly into DB (SQL Injection)
    - IDOR: user_id from form field
    - No duplicate detection
    - Detailed error messages leak DB schema
    """
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['file']
        # VULN: No file type check - accepts any file
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        mysql = get_mysql()
        cursor = mysql.connection.cursor()
        imported = 0
        errors = []
        vault_hit = False

        for i, row in enumerate(reader, start=2):
            try:
                date = row.get('Date', row.get('date', ''))
                type_ = row.get('Type', row.get('type', 'expense'))
                amount = row.get('Amount', row.get('amount', 0))
                description = row.get('Description', row.get('description', ''))
                category_name = row.get('Category', row.get('category', ''))

                # VULN: SQL Injection - values from CSV written directly
                category_id = 'NULL'
                if category_name:
                    cursor.execute(
                        f"SELECT id FROM categories WHERE name = '{category_name}' AND user_id = {user_id} LIMIT 1"
                    )
                    cat = cursor.fetchone()
                    if cat:
                        category_id = cat[0]

                # Sprint 44 (VULN-043 flag, the "vault" pattern): the query
                # above executed without error even though category_name
                # deliberately references the ctf_vault table by name via
                # UNION — proving the injection reached a table with no
                # normal app relationship to categories at all, not a
                # coincidence. See database/init-vulnerable-sprint44.sql.
                if 'ctf_vault' in category_name.lower():
                    vault_hit = True

                # VULN: SQL Injection in all fields from CSV
                cursor.execute(f"""
                    INSERT INTO transactions (user_id, category_id, type, amount, description, transaction_date)
                    VALUES ({user_id}, {category_id}, '{type_}', {amount}, '{description}', '{date}')
                """)
                imported += 1

            except Exception as e:
                # VULN: Detailed DB errors exposed
                errors.append(f"Row {i}: {str(e)}")
                continue

        mysql.connection.commit()
        cursor.close()

        if vault_hit:
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-043')

        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {imported} transactions'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Import error: {str(e)}'}), 500


# ============================================================================
# IMPORT OFX
# ============================================================================
@api_export_bp.route('/import/ofx', methods=['POST'])
def import_ofx():
    """
    Import transactions from an OFX bank statement file.
    VULNERABILITIES:
    - No authentication check, no CSRF
    - VULN-067: XXE via utils/ofx_parser.parse_ofx() (xml.dom.minidom, unhardened —
      a crafted OFX file can read local files or trigger SSRF)
    - VULN-068: SQL Injection (via Transaction.create()'s string-concatenated INSERT,
      and directly in this route's duplicate-check query)
    - VULN-069: IDOR — account_id/user_id come straight from the request with
      no ownership check, so transactions (and their balance effect) can be
      imported into any user's account
    - No file type/size validation
    """
    try:
        user_id = request.form.get('user_id')
        account_id = request.form.get('account_id')
        if not user_id or not account_id:
            return jsonify({'success': False, 'message': 'user_id and account_id required'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        content = file.read().decode('utf-8', errors='replace')

        try:
            parsed = parse_ofx(content)  # VULN-067: XXE
        except Exception as e:
            return jsonify({'success': False, 'message': f'Could not parse OFX file: {str(e)}'}), 400

        # Sprint 44 (VULN-067 flag, the 11th pattern — XXE doesn't fit any
        # of the other 10 shapes since it isn't a leak the app itself
        # returns to the caller in a structured way): a marker file at a
        # known local path (vulnerable-version/ctf_vault_flag.txt, copied
        # to /app/ctf_vault_flag.txt in the image) is the target. If the
        # confirmed file:/// entity read actually pulled it in, its
        # contents show up in whatever OFX field referenced the entity.
        xxe_marker_hit = any(
            'AURA_XXE_VAULT_MARKER' in str(tx.get(field, ''))
            for tx in parsed
            for field in ('description', 'external_id')
        )

        mysql = get_mysql()
        imported = 0
        skipped_duplicate = 0
        errors = []

        for i, tx in enumerate(parsed, start=1):
            try:
                tx_type = 'income' if tx['amount'] >= 0 else 'expense'
                amount = abs(tx['amount'])

                # VULN: SQL Injection, IDOR — no ownership scoping on account_id
                if tx['external_id']:
                    cursor = mysql.connection.cursor()
                    cursor.execute(
                        f"SELECT id FROM transactions WHERE account_id = {account_id} "
                        f"AND external_id = '{tx['external_id']}'"
                    )
                    dup = cursor.fetchone()
                    cursor.close()
                    if dup:
                        skipped_duplicate += 1
                        continue

                success, message, _ = Transaction.create(
                    mysql, user_id, None, tx_type, amount, tx['description'], tx['date'],
                    account_id=account_id, external_id=tx['external_id']
                )
                if success:
                    imported += 1
                else:
                    errors.append(f"Transaction {i}: {message}")
            except Exception as e:
                errors.append(f"Transaction {i}: {str(e)}")
                continue

        attacker_id = session.get('user_id')
        if attacker_id:
            # Sprint 44 (VULN-069 flag): importing into an account that
            # isn't the caller's own is the proof.
            dest_account = Account.get_by_id(mysql, account_id) if str(account_id).isdigit() else None
            if dest_account and str(dest_account.user_id) != str(attacker_id):
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-069')

            # Sprint 44 (VULN-068 flag): a non-numeric account_id that the
            # duplicate-check query still executed successfully with is
            # real injected SQL syntax, not coincidental valid input.
            if account_id and not str(account_id).isdigit():
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-068')

            if xxe_marker_hit:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-067')

        return jsonify({
            'success': True,
            'imported': imported,
            'skipped_duplicate': skipped_duplicate,
            'errors': errors,
            'message': f'Imported {imported} transactions ({skipped_duplicate} duplicates skipped)'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Import error: {str(e)}'}), 500


# ============================================================================
# IMPORT QIF
# ============================================================================
@api_export_bp.route('/import/qif', methods=['POST'])
def import_qif():
    """
    Import transactions from a QIF (Quicken) file.
    VULNERABILITIES:
    - No authentication check, no CSRF
    - VULN-068: SQL Injection (category lookup below, and Transaction.create()'s
      string-concatenated INSERT)
    - VULN-069: IDOR — account_id/user_id come straight from the request with
      no ownership check
    - No file type/size validation, no duplicate detection (QIF has no FITID)
    """
    try:
        user_id = request.form.get('user_id')
        account_id = request.form.get('account_id')
        if not user_id or not account_id:
            return jsonify({'success': False, 'message': 'user_id and account_id required'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        content = file.read().decode('utf-8', errors='replace')
        parsed = parse_qif(content)

        mysql = get_mysql()
        cursor = mysql.connection.cursor()
        imported = 0
        errors = []

        for i, tx in enumerate(parsed, start=1):
            try:
                tx_type = 'income' if tx['amount'] >= 0 else 'expense'
                amount = abs(tx['amount'])

                # VULN: SQL Injection - category name from QIF file written directly
                category_id = 'NULL'
                if tx['category_name']:
                    cursor.execute(
                        f"SELECT id FROM categories WHERE name = '{tx['category_name']}' AND user_id = {user_id} LIMIT 1"
                    )
                    cat = cursor.fetchone()
                    if cat:
                        category_id = cat[0]

                success, message, _ = Transaction.create(
                    mysql, user_id, category_id if category_id != 'NULL' else None,
                    tx_type, amount, tx['description'], tx['date'], account_id=account_id
                )
                if success:
                    imported += 1
                else:
                    errors.append(f"Transaction {i}: {message}")
            except Exception as e:
                errors.append(f"Transaction {i}: {str(e)}")
                continue

        cursor.close()

        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {imported} transactions'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Import error: {str(e)}'}), 500


# ============================================================================
# REPORTS - Summary Data
# ============================================================================
@api_export_bp.route('/reports/summary', methods=['GET'])
def reports_summary():
    """
    Advanced report summary: spending by category, by month, by account.
    VULNERABILITIES: No auth, IDOR, SQL Injection in all params
    """
    try:
        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from', '2026-01-01')
        date_to = request.args.get('date_to', '2026-12-31')

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id required'}), 400

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()

        # VULN: SQL Injection in user_id and date params. Currency
        # conversion rates interpolated unsafely too — see
        # utils/currency.rate_case_sql.
        # By category
        cursor.execute(f"""
            SELECT c.name, t.type, SUM({case_sql}) as total, COUNT(*) as count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.is_transfer = FALSE
              AND t.transaction_date BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY c.name, t.type
            ORDER BY total DESC
        """)
        by_category = [{'category': r[0] or 'Uncategorized', 'type': r[1], 'total': float(r[2]), 'count': r[3]}
                       for r in cursor.fetchall()]

        # By month
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') as month,
                   SUM(CASE WHEN t.type='income' THEN {case_sql} ELSE 0 END) as income,
                   SUM(CASE WHEN t.type='expense' THEN {case_sql} ELSE 0 END) as expenses
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.is_transfer = FALSE
              AND t.transaction_date BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY month ORDER BY month
        """)
        by_month = [{'month': r[0], 'income': float(r[1]), 'expenses': float(r[2])}
                    for r in cursor.fetchall()]

        # By account — a single account per row, already one currency, no
        # conversion needed, just surfaced for display.
        cursor.execute(f"""
            SELECT a.name, SUM(CASE WHEN t.type='income' THEN t.amount ELSE 0 END) as income,
                   SUM(CASE WHEN t.type='expense' THEN t.amount ELSE 0 END) as expenses,
                   COALESCE(a.currency, 'RON') as currency
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.is_transfer = FALSE
              AND t.transaction_date BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY a.name, a.currency
        """)
        by_account = [{'account': r[0] or 'No Account', 'income': float(r[1]), 'expenses': float(r[2]), 'currency': r[3]}
                      for r in cursor.fetchall()]

        cursor.close()

        return jsonify({
            'success': True,
            'by_category': by_category,
            'by_month': by_month,
            'by_account': by_account
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Report error: {str(e)}'}), 500
