"""
Aura Financial Tracker - Vulnerable Version
Report Data API — Widget Data Endpoints (WITH INTENTIONAL VULNERABILITIES)
Sprint 8: Flame Breathing - Eighth Form

All endpoints accept ?user_id= and ?period= (1M / 3M / 6M / 1Y / ALL).
VULNERABILITY: No authentication — any user_id returns that user's data (IDOR).
VULNERABILITY: SQL Injection throughout — user_id and period injected directly.
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from models.transaction import Transaction
from utils.currency import get_rate_map, rate_case_sql
from utils import flag_engine

api_reports_data_bp = Blueprint('api_reports_data', __name__)

# Categories classified as "fixed" costs for the fixed/variable split widget.
FIXED_CATEGORY_KEYWORDS = ['housing', 'utilities', 'obligation', 'loan', 'mortgage',
                            'subscription', 'rent', 'insurance', 'debt']

# Sprint 20: fixed statistical-heuristic constant (not configurable per widget)
# — ANOMALY_WINDOW_MONTHS/ANOMALY_THRESHOLD_PCT moved to Transaction (Sprint 25,
# alongside get_monthly_anomalies()); MOVING_AVG_WINDOW stays here too since
# spending_trend()'s own chart moving-average uses it directly.
MOVING_AVG_WINDOW = 3


def get_mysql():
    from flask import current_app
    return current_app.extensions['mysql']


def _start_date(period):
    """Returns ISO date string for the start of the requested period, or None for ALL."""
    now = datetime.now().date()
    periods = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365}
    days = periods.get(period)
    if days is None:
        return None
    return str(now - timedelta(days=days))


def _date_filter(period, table_alias='t'):
    """Returns SQL AND clause for period filter, or empty string for ALL."""
    start = _start_date(period)
    if not start:
        return ''
    # VULN: start date derived from user-supplied period string (SQL Injection if period is manipulated)
    return f"AND {table_alias}.transaction_date >= '{start}'"


def _category_filter(category_ids_str, table_alias='t'):
    """
    Returns AND clause filtering by category IDs.
    VULNERABILITY: category_ids injected directly into IN() — SQL Injection
    e.g. category_ids='1) OR (1=1' → AND t.category_id IN (1) OR (1=1)
    """
    if not category_ids_str:
        return ''
    # VULN: SQL Injection — category_ids_str appended without parameterisation
    return f"AND {table_alias}.category_id IN ({category_ids_str})"


def _account_filter(account_ids_str, table_alias='t'):
    """
    Returns AND clause filtering by account IDs.
    VULNERABILITY: account_ids injected directly into IN() — SQL Injection
    """
    if not account_ids_str:
        return ''
    # VULN: SQL Injection — account_ids_str appended without parameterisation
    return f"AND {table_alias}.account_id IN ({account_ids_str})"


# ── 1. Income vs Expenses by month ───────────────────────────────────────────

@api_reports_data_bp.route('/income-expense', methods=['GET'])
def income_expense():
    """
    Returns monthly income and expense totals for bar chart.
    VULNERABILITY: SQL Injection via user_id and period
    VULNERABILITY: IDOR — no session check
    """
    try:
        user_id      = request.args.get('user_id', '')
        period       = request.args.get('period', '6M').upper()
        category_ids = request.args.get('category_ids', '')
        account_ids  = request.args.get('account_ids', '')
        date_f  = _date_filter(period)
        cat_f   = _category_filter(category_ids)
        acc_f   = _account_filter(account_ids)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection via user_id, category_ids, account_ids
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   t.type,
                   SUM({case_sql}) AS total
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.is_transfer = FALSE
            {date_f}
            {cat_f}
            {acc_f}
            GROUP BY month, t.type
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        # Pivot into {month: {income: X, expense: Y}}
        months_map = {}
        for month, ttype, total in rows:
            if month not in months_map:
                months_map[month] = {'income': 0.0, 'expense': 0.0}
            months_map[month][ttype] = float(total)

        sorted_months = sorted(months_map.keys())
        result = {
            'months':   sorted_months,
            'income':   [months_map[m]['income']  for m in sorted_months],
            'expense':  [months_map[m]['expense'] for m in sorted_months],
            'net':      [round(months_map[m]['income'] - months_map[m]['expense'], 2)
                         for m in sorted_months],
            'total_income':  round(sum(months_map[m]['income']  for m in sorted_months), 2),
            'total_expense': round(sum(months_map[m]['expense'] for m in sorted_months), 2),
        }

        # Sprint 44 (VULN-060 flag): reading someone else's income/expense
        # data via the user_id param is the proof.
        attacker_id = session.get('user_id')
        if attacker_id and user_id and str(user_id) != str(attacker_id):
            flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-060')

        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 2. Expense distribution by category ──────────────────────────────────────

@api_reports_data_bp.route('/expense-distribution', methods=['GET'])
def expense_distribution():
    """
    Returns per-category expense totals for donut chart.
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id      = request.args.get('user_id', '')
        period       = request.args.get('period', '1M').upper()
        category_ids = request.args.get('category_ids', '')
        date_f  = _date_filter(period)
        cat_f   = _category_filter(category_ids)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection via user_id, category_ids
        cursor.execute(f"""
            SELECT COALESCE(c.name, 'Uncategorized') AS category,
                   COALESCE(c.color, '#6c757d')      AS color,
                   SUM({case_sql})                    AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
            {date_f}
            {cat_f}
            GROUP BY t.category_id, c.name, c.color
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        cursor.close()

        categories = [{'name': r[0], 'color': r[1], 'total': float(r[2])} for r in rows]
        grand_total = sum(c['total'] for c in categories)
        for c in categories:
            c['pct'] = round(c['total'] / grand_total * 100, 1) if grand_total else 0

        # Sprint 44 (VULN-054 flag): a non-numeric value inside category_ids
        # that the query still executed successfully with is real injected
        # SQL syntax, not coincidental valid input (same signal as VULN-072).
        if category_ids and not all(p.strip().isdigit() for p in category_ids.split(',') if p.strip()):
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-054')

        return jsonify({'success': True, 'data': {'categories': categories, 'total': round(grand_total, 2)}}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 3. Category heatmap (month × category matrix) ────────────────────────────

@api_reports_data_bp.route('/category-heatmap', methods=['GET'])
def category_heatmap():
    """
    Returns month × category expense totals for heatmap grid.
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id      = request.args.get('user_id', '')
        period       = request.args.get('period', '1Y').upper()
        category_ids = request.args.get('category_ids', '')
        date_f  = _date_filter(period)
        cat_f   = _category_filter(category_ids)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection via user_id, category_ids
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   COALESCE(c.name, 'Uncategorized')        AS category,
                   SUM({case_sql})                           AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
            {date_f}
            {cat_f}
            GROUP BY month, t.category_id, c.name
            ORDER BY month ASC, total DESC
        """)
        rows = cursor.fetchall()
        cursor.close()

        months_set = []
        cats_set   = []
        data_map   = {}

        for month, cat, total in rows:
            if month not in months_set:
                months_set.append(month)
            if cat not in cats_set:
                cats_set.append(cat)
            data_map[(month, cat)] = float(total)

        matrix = {}
        for cat in cats_set:
            matrix[cat] = [data_map.get((m, cat), 0.0) for m in months_set]

        max_val = max((v for row in matrix.values() for v in row), default=1.0)

        return jsonify({'success': True, 'data': {
            'months':    months_set,
            'categories': cats_set,
            'matrix':    matrix,
            'max_value': max_val,
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 4. Top 5 categories trend ─────────────────────────────────────────────────

@api_reports_data_bp.route('/top-categories', methods=['GET'])
def top_categories():
    """
    Returns monthly totals for the top 5 expense categories (by total spend).
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id = request.args.get('user_id', '')
        period  = request.args.get('period', '6M').upper()
        date_f  = _date_filter(period)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()

        category_ids = request.args.get('category_ids', '')
        cat_f        = _category_filter(category_ids)

        # Step 1: find top 5 categories by total spend in the period
        # VULN: SQL Injection via user_id, category_ids
        cursor.execute(f"""
            SELECT COALESCE(c.name, 'Uncategorized') AS category,
                   COALESCE(c.color, '#6c757d')      AS color,
                   SUM({case_sql})                    AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
            {date_f}
            {cat_f}
            GROUP BY t.category_id, c.name, c.color
            ORDER BY total DESC
            LIMIT 5
        """)
        top = cursor.fetchall()

        if not top:
            cursor.close()
            return jsonify({'success': True, 'data': {'months': [], 'series': []}}), 200

        top_names = [r[0] for r in top]
        top_colors = {r[0]: r[1] for r in top}
        names_in = ', '.join(f"'{n}'" for n in top_names)

        # Step 2: monthly breakdown for those categories
        # VULN: SQL Injection via user_id, names_in, category_ids
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   COALESCE(c.name, 'Uncategorized')        AS category,
                   SUM({case_sql})                           AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
              AND COALESCE(c.name, 'Uncategorized') IN ({names_in})
            {date_f}
            {cat_f}
            GROUP BY month, t.category_id, c.name
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        months_set = sorted({r[0] for r in rows})
        data_map   = {(r[0], r[1]): float(r[2]) for r in rows}

        series = []
        for name in top_names:
            series.append({
                'name':  name,
                'color': top_colors[name],
                'data':  [data_map.get((m, name), 0.0) for m in months_set],
            })

        return jsonify({'success': True, 'data': {'months': months_set, 'series': series}}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 5. Fixed vs variable split ────────────────────────────────────────────────

@api_reports_data_bp.route('/fixed-variable', methods=['GET'])
def fixed_variable():
    """
    Returns monthly fixed and variable expense totals.
    Fixed = categories whose names contain keywords in FIXED_CATEGORY_KEYWORDS.
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id = request.args.get('user_id', '')
        period  = request.args.get('period', '3M').upper()
        date_f  = _date_filter(period)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   COALESCE(c.name, 'Uncategorized')        AS category,
                   SUM({case_sql})                           AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
            {date_f}
            GROUP BY month, t.category_id, c.name
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        months_set = sorted({r[0] for r in rows})
        fixed_map  = {m: 0.0 for m in months_set}
        var_map    = {m: 0.0 for m in months_set}

        for month, cat, total in rows:
            cat_lower = cat.lower()
            is_fixed  = any(kw in cat_lower for kw in FIXED_CATEGORY_KEYWORDS)
            if is_fixed:
                fixed_map[month] += float(total)
            else:
                var_map[month]   += float(total)

        return jsonify({'success': True, 'data': {
            'months':   months_set,
            'fixed':    [round(fixed_map[m], 2) for m in months_set],
            'variable': [round(var_map[m],   2) for m in months_set],
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 6. Financial obligations monthly ─────────────────────────────────────────

@api_reports_data_bp.route('/obligations', methods=['GET'])
def obligations():
    """
    Returns monthly totals for obligation/debt/loan categories.
    Also returns YTD total for use by extra_repayments_ytd and debt_payments_metric widgets.
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id = request.args.get('user_id', '')
        period  = request.args.get('period', '1Y').upper()
        date_f  = _date_filter(period)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()

        # All obligation-like categories
        kw_conditions = " OR ".join(
            f"LOWER(c.name) LIKE '%{kw}%'"
            for kw in ['obligation', 'loan', 'mortgage', 'debt', 'housing', 'rent', 'credit']
        )

        # VULN: SQL Injection
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   SUM({case_sql})                           AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND ({kw_conditions})
            {date_f}
            GROUP BY month
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        months  = [r[0] for r in rows]
        totals  = [float(r[1]) for r in rows]
        ytd     = round(sum(totals), 2)

        # Extra repayments: approximate as any month above the median payment
        avg = (ytd / len(totals)) if totals else 0.0
        extra = round(sum(max(t - avg, 0.0) for t in totals), 2)

        return jsonify({'success': True, 'data': {
            'months':  months,
            'totals':  totals,
            'ytd':     ytd,
            'extra_ytd': extra,
            'avg_monthly': round(avg, 2),
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 7. Potential to save ──────────────────────────────────────────────────────

@api_reports_data_bp.route('/potential-to-save', methods=['GET'])
def potential_to_save():
    """
    Returns monthly net (income − expenses) and running cumulative.
    VULNERABILITY: SQL Injection via user_id
    """
    try:
        user_id     = request.args.get('user_id', '')
        period      = request.args.get('period', '1M').upper()
        account_ids = request.args.get('account_ids', '')
        date_f = _date_filter(period)
        acc_f  = _account_filter(account_ids)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection via user_id, account_ids
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   t.type,
                   SUM({case_sql}) AS total
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.is_transfer = FALSE
            {date_f}
            {acc_f}
            GROUP BY month, t.type
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        pivot = {}
        for month, ttype, total in rows:
            if month not in pivot:
                pivot[month] = {'income': 0.0, 'expense': 0.0}
            pivot[month][ttype] = float(total)

        sorted_months = sorted(pivot.keys())
        net_by_month  = [round(pivot[m]['income'] - pivot[m]['expense'], 2) for m in sorted_months]
        cumulative    = []
        running       = 0.0
        for n in net_by_month:
            running += n
            cumulative.append(round(running, 2))

        current_net = net_by_month[-1] if net_by_month else 0.0

        # Sprint 44 (VULN-055 flag): a non-numeric value inside account_ids
        # that the query still executed successfully with is real injected
        # SQL syntax, not coincidental valid input (same signal as VULN-072).
        if account_ids and not all(p.strip().isdigit() for p in account_ids.split(',') if p.strip()):
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-055')

        return jsonify({'success': True, 'data': {
            'months':      sorted_months,
            'net':         net_by_month,
            'cumulative':  cumulative,
            'current_net': current_net,
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 8. Savings goals progress ─────────────────────────────────────────────────

@api_reports_data_bp.route('/savings-goals', methods=['GET'])
def savings_goals():
    """
    Returns all active savings goals with progress data.
    VULNERABILITY: SQL Injection via user_id, IDOR
    """
    try:
        user_id = request.args.get('user_id', '')

        mysql = get_mysql()
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection
        cursor.execute(f"""
            SELECT id, name, target_amount, current_amount, target_date, status
            FROM savings_goals
            WHERE user_id = {user_id}
              AND status = 'active'
            ORDER BY target_date ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        goals = []
        for r in rows:
            target  = float(r[2]) if r[2] else 0.0
            current = float(r[3]) if r[3] else 0.0
            pct     = round(current / target * 100, 1) if target > 0 else 0.0
            goals.append({
                'id':             r[0],
                'name':           r[1],
                'target_amount':  target,
                'current_amount': current,
                'pct':            pct,
                'target_date':    str(r[4]) if r[4] else None,
                'remaining':      round(max(target - current, 0.0), 2),
            })

        return jsonify({'success': True, 'data': {'goals': goals}}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 9. Budget vs Actual ───────────────────────────────────────────────────────

@api_reports_data_bp.route('/budget-vs-actual', methods=['GET'])
def budget_vs_actual():
    """
    Returns budget limits vs actual spend per category for the most recent active budget.
    VULNERABILITY: SQL Injection via user_id, IDOR
    """
    try:
        user_id      = request.args.get('user_id', '')
        period       = request.args.get('period', '1M').upper()
        category_ids = request.args.get('category_ids', '')
        date_f = _date_filter(period)
        cat_f  = _category_filter(category_ids, table_alias='bc')

        mysql = get_mysql()
        cursor = mysql.connection.cursor()

        # Get the most recent active budget for this user
        # VULN: SQL Injection
        cursor.execute(f"""
            SELECT id, name, start_date, end_date
            FROM budgets
            WHERE user_id = {user_id} AND is_active = TRUE
            ORDER BY start_date DESC
            LIMIT 1
        """)
        budget_row = cursor.fetchone()

        if not budget_row:
            cursor.close()
            return jsonify({'success': True, 'data': {'categories': [], 'budget_name': None}}), 200

        budget_id   = budget_row[0]
        budget_name = budget_row[1]
        start_date  = budget_row[2]
        end_date    = budget_row[3]

        # Get category limits and actual spend
        # VULN: SQL Injection via user_id, budget_id, category_ids
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
        cursor.execute(f"""
            SELECT c.name,
                   bc.limit_amount,
                   COALESCE(SUM({case_sql}), 0) AS spent
            FROM budget_categories bc
            LEFT JOIN categories c  ON bc.category_id = c.id
            LEFT JOIN transactions t ON t.category_id = bc.category_id
                AND t.type = 'expense'
                AND t.transaction_date BETWEEN '{start_date}' AND '{end_date}'
                AND t.user_id = {user_id}
            LEFT JOIN accounts ac ON t.account_id = ac.id
            WHERE bc.budget_id = {budget_id}
            {cat_f}
            GROUP BY bc.category_id, c.name, bc.limit_amount
            ORDER BY bc.limit_amount DESC
        """)
        rows = cursor.fetchall()
        cursor.close()

        categories = [{
            'name':   r[0],
            'budget': float(r[1]),
            'actual': float(r[2]),
            'over':   float(r[2]) > float(r[1]),
        } for r in rows]

        return jsonify({'success': True, 'data': {
            'budget_name': budget_name,
            'categories':  categories,
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 10. Spending trend & anomaly detection ────────────────────────────────────
# Anomaly detection itself now lives in Transaction.get_monthly_anomalies()
# (Sprint 25) — relocated so the AI-insight scheduler job can reuse it.

@api_reports_data_bp.route('/spending-trend', methods=['GET'])
def spending_trend():
    """
    Returns monthly expense totals + a 3-month moving average + a global
    anomaly list.
    VULNERABILITY (VULN-072): SQL Injection via user_id, IDOR — no session check.
    """
    try:
        user_id      = request.args.get('user_id', '')
        period       = request.args.get('period', '6M').upper()
        category_ids = request.args.get('category_ids', '')
        account_ids  = request.args.get('account_ids', '')
        date_f = _date_filter(period)
        cat_f  = _category_filter(category_ids)
        acc_f  = _account_filter(account_ids)

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        # VULN: SQL Injection via user_id, category_ids, account_ids
        cursor.execute(f"""
            SELECT DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                   SUM({case_sql})                           AS total
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = {user_id}
              AND t.type = 'expense'
              AND t.is_transfer = FALSE
            {date_f}
            {cat_f}
            {acc_f}
            GROUP BY month
            ORDER BY month ASC
        """)
        rows = cursor.fetchall()
        cursor.close()

        months = [r[0] for r in rows]
        totals = [float(r[1]) for r in rows]

        moving_avg = []
        for i in range(len(totals)):
            if i < MOVING_AVG_WINDOW - 1:
                moving_avg.append(None)
            else:
                window = totals[i - MOVING_AVG_WINDOW + 1:i + 1]
                moving_avg.append(round(sum(window) / MOVING_AVG_WINDOW, 2))

        anomalies = Transaction.get_monthly_anomalies(mysql, user_id)

        # Sprint 43 (VULN-072 flag): a legitimate user_id is always purely
        # numeric — if the raw value isn't, and the query still executed
        # (we're past the try block's risky line without an exception),
        # that's real injected SQL syntax being accepted by MySQL, not
        # coincidental valid input. Credited to the attacker's own session
        # if they're logged in while testing.
        if user_id and not str(user_id).isdigit():
            attacker_id = session.get('user_id')
            if attacker_id:
                flag_engine.mark_solved_with_flag(mysql, attacker_id, 'VULN-072')

        return jsonify({'success': True, 'data': {
            'months': months, 'totals': totals, 'moving_avg': moving_avg, 'anomalies': anomalies,
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


# ── 11. Year-over-year category comparison ────────────────────────────────────

@api_reports_data_bp.route('/yoy-comparison', methods=['GET'])
def yoy_comparison():
    """
    This year (Jan 1 -> today) vs last year (Jan 1 -> Dec 31), per category.
    VULNERABILITY (VULN-072): SQL Injection via user_id, IDOR — no session check.
    """
    try:
        user_id = request.args.get('user_id', '')

        today = datetime.now().date()
        this_year_start = f"{today.year}-01-01"
        last_year_start = f"{today.year - 1}-01-01"
        last_year_end = f"{today.year - 1}-12-31"

        mysql = get_mysql()
        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)

        def _totals_by_category(date_from, date_to):
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection via user_id
            cursor.execute(f"""
                SELECT COALESCE(c.name, 'Uncategorized') AS category,
                       SUM({case_sql})                    AS total
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE t.user_id = {user_id}
                  AND t.type = 'expense'
                  AND t.is_transfer = FALSE
                  AND t.transaction_date BETWEEN '{date_from}' AND '{date_to}'
                GROUP BY t.category_id, c.name
            """)
            rows = cursor.fetchall()
            cursor.close()
            return {r[0]: float(r[1]) for r in rows}

        this_year_map = _totals_by_category(this_year_start, str(today))
        last_year_map = _totals_by_category(last_year_start, last_year_end)

        names = sorted(set(this_year_map) | set(last_year_map))
        categories = []
        for name in names:
            ty = this_year_map.get(name, 0.0)
            ly = last_year_map.get(name, 0.0)
            pct_change = round((ty - ly) / ly * 100, 1) if ly > 0 else None
            categories.append({
                'name': name, 'this_year': round(ty, 2), 'last_year': round(ly, 2), 'pct_change': pct_change,
            })

        categories.sort(key=lambda c: c['this_year'], reverse=True)

        return jsonify({'success': True, 'data': {'categories': categories}}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
