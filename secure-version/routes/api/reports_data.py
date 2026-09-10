"""
Aura Financial Tracker - Secure Version
Report Data API — Widget Data Endpoints
Sprint 14: Export/Import + Reports + Multi-Dashboard System

All endpoints accept ?period= (1M / 3M / 6M / 1Y / ALL) and optional
?category_ids=/?account_ids= (comma-separated).

Security properties (contrast with vulnerable-version/routes/api/reports_data.py):
- Every route requires @api_login_required; user_id always comes from session
- category_ids / account_ids are parsed, then filtered down to only the IDs
  actually owned by (or visible to) the session user before being used in a
  query — vulnerable's _category_filter()/_account_filter() splice the raw
  query-string value directly into an IN (...) clause (SQL Injection, e.g.
  category_ids='1) OR (1=1')
- Every WHERE/IN clause is parameterized — no f-string SQL anywhere
- period is validated against a fixed whitelist before use
"""

from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timedelta
from models.category import Category
from models.account import Account
from models.transaction import Transaction
from routes.main import api_login_required
from utils.currency import get_rate_map, rate_case_sql, rate_case_params

api_reports_data_bp = Blueprint('api_reports_data', __name__)

FIXED_CATEGORY_KEYWORDS = ['housing', 'utilities', 'obligation', 'loan', 'mortgage',
                            'subscription', 'rent', 'insurance', 'debt']

OBLIGATION_KEYWORDS = ['obligation', 'loan', 'mortgage', 'debt', 'housing', 'rent', 'credit']

ALLOWED_PERIODS = {'1M', '3M', '6M', '1Y', 'ALL'}

# Sprint 20: fixed statistical-heuristic constant (not configurable per widget)
# — ANOMALY_WINDOW_MONTHS/ANOMALY_THRESHOLD_PCT moved to Transaction (Sprint 25,
# alongside get_monthly_anomalies()); MOVING_AVG_WINDOW stays here too since
# spending_trend()'s own chart moving-average uses it directly.
MOVING_AVG_WINDOW = 3


def get_mysql():
    return current_app.extensions['mysql']


def _period(raw, default):
    p = (raw or default).upper()
    return p if p in ALLOWED_PERIODS else default


def _start_date(period):
    now = datetime.now().date()
    periods = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365}
    days = periods.get(period)
    if days is None:
        return None
    return str(now - timedelta(days=days))


def _parse_id_list(raw):
    if not raw:
        return []
    out = []
    for part in raw.split(','):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def _owned_category_ids(mysql, user_id, raw):
    ids = _parse_id_list(raw)
    return [i for i in ids if Category.get_by_id(mysql, i, user_id)]


def _owned_account_ids(mysql, user_id, raw):
    ids = _parse_id_list(raw)
    return [i for i in ids if Account.get_by_id(mysql, i, user_id)]


def _in_clause(column, ids):
    """Returns (sql_fragment, params) for `AND column IN (%s, %s, ...)`, or ('', []) if ids is empty."""
    if not ids:
        return '', []
    placeholders = ', '.join(['%s'] * len(ids))
    return f"AND {column} IN ({placeholders})", list(ids)


# ── 1. Income vs Expenses by month ───────────────────────────────────────────

@api_reports_data_bp.route('/income-expense', methods=['GET'])
@api_login_required
def income_expense():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '6M')
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        acc_ids = _owned_account_ids(mysql, user_id, request.args.get('account_ids', ''))
        cat_sql, cat_params = _in_clause('t.category_id', cat_ids)
        acc_sql, acc_params = _in_clause('t.account_id', acc_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, t.type, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.is_transfer = FALSE {date_sql} {cat_sql} {acc_sql} "
            f"GROUP BY month, t.type ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + cat_params + acc_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        months_map = {}
        for month, ttype, total in rows:
            months_map.setdefault(month, {'income': 0.0, 'expense': 0.0})
            months_map[month][ttype] = float(total)

        sorted_months = sorted(months_map.keys())
        result = {
            'months': sorted_months,
            'income': [months_map[m]['income'] for m in sorted_months],
            'expense': [months_map[m]['expense'] for m in sorted_months],
            'net': [round(months_map[m]['income'] - months_map[m]['expense'], 2) for m in sorted_months],
            'total_income': round(sum(months_map[m]['income'] for m in sorted_months), 2),
            'total_expense': round(sum(months_map[m]['expense'] for m in sorted_months), 2),
        }
        return jsonify({'success': True, 'data': result}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 2. Expense distribution by category ──────────────────────────────────────

@api_reports_data_bp.route('/expense-distribution', methods=['GET'])
@api_login_required
def expense_distribution():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '1M')
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        cat_sql, cat_params = _in_clause('t.category_id', cat_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT COALESCE(c.name, 'Uncategorized') AS category, "
            f"COALESCE(c.color, '#6c757d') AS color, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE {date_sql} {cat_sql} "
            f"GROUP BY t.category_id, c.name, c.color ORDER BY total DESC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + cat_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        categories = [{'name': r[0], 'color': r[1], 'total': float(r[2])} for r in rows]
        grand_total = sum(c['total'] for c in categories)
        for c in categories:
            c['pct'] = round(c['total'] / grand_total * 100, 1) if grand_total else 0

        return jsonify({'success': True, 'data': {'categories': categories, 'total': round(grand_total, 2)}}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 3. Category heatmap (month × category matrix) ────────────────────────────

@api_reports_data_bp.route('/category-heatmap', methods=['GET'])
@api_login_required
def category_heatmap():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '1Y')
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        cat_sql, cat_params = _in_clause('t.category_id', cat_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, "
            f"COALESCE(c.name, 'Uncategorized') AS category, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE {date_sql} {cat_sql} "
            f"GROUP BY month, t.category_id, c.name ORDER BY month ASC, total DESC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + cat_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        months_set, cats_set, data_map = [], [], {}
        for month, cat, total in rows:
            if month not in months_set:
                months_set.append(month)
            if cat not in cats_set:
                cats_set.append(cat)
            data_map[(month, cat)] = float(total)

        matrix = {cat: [data_map.get((m, cat), 0.0) for m in months_set] for cat in cats_set}
        max_val = max((v for row in matrix.values() for v in row), default=1.0)

        return jsonify({'success': True, 'data': {
            'months': months_set, 'categories': cats_set, 'matrix': matrix, 'max_value': max_val,
        }}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 4. Top 5 categories trend ─────────────────────────────────────────────────

@api_reports_data_bp.route('/top-categories', methods=['GET'])
@api_login_required
def top_categories():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '6M')
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        cat_sql, cat_params = _in_clause('t.category_id', cat_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT COALESCE(c.name, 'Uncategorized') AS category, "
            f"COALESCE(c.color, '#6c757d') AS color, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE {date_sql} {cat_sql} "
            f"GROUP BY t.category_id, c.name, c.color ORDER BY total DESC LIMIT 5",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + cat_params)
        )
        top = cursor.fetchall()

        if not top:
            cursor.close()
            return jsonify({'success': True, 'data': {'months': [], 'series': []}}), 200

        top_names = [r[0] for r in top]
        top_colors = {r[0]: r[1] for r in top}
        names_placeholders = ', '.join(['%s'] * len(top_names))

        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, "
            f"COALESCE(c.name, 'Uncategorized') AS category, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE "
            f"AND COALESCE(c.name, 'Uncategorized') IN ({names_placeholders}) "
            f"{date_sql} {cat_sql} "
            f"GROUP BY month, t.category_id, c.name ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + top_names + date_params + cat_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        months_set = sorted({r[0] for r in rows})
        data_map = {(r[0], r[1]): float(r[2]) for r in rows}

        series = [{
            'name': name, 'color': top_colors[name],
            'data': [data_map.get((m, name), 0.0) for m in months_set],
        } for name in top_names]

        return jsonify({'success': True, 'data': {'months': months_set, 'series': series}}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 5. Fixed vs variable split ────────────────────────────────────────────────

@api_reports_data_bp.route('/fixed-variable', methods=['GET'])
@api_login_required
def fixed_variable():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '3M')
        mysql = get_mysql()

        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, "
            f"COALESCE(c.name, 'Uncategorized') AS category, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE {date_sql} "
            f"GROUP BY month, t.category_id, c.name ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        months_set = sorted({r[0] for r in rows})
        fixed_map = {m: 0.0 for m in months_set}
        var_map = {m: 0.0 for m in months_set}

        for month, cat, total in rows:
            cat_lower = cat.lower()
            is_fixed = any(kw in cat_lower for kw in FIXED_CATEGORY_KEYWORDS)
            if is_fixed:
                fixed_map[month] += float(total)
            else:
                var_map[month] += float(total)

        return jsonify({'success': True, 'data': {
            'months': months_set,
            'fixed': [round(fixed_map[m], 2) for m in months_set],
            'variable': [round(var_map[m], 2) for m in months_set],
        }}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 6. Financial obligations monthly ─────────────────────────────────────────

@api_reports_data_bp.route('/obligations', methods=['GET'])
@api_login_required
def obligations():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '1Y')
        mysql = get_mysql()

        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        kw_conditions = " OR ".join("LOWER(c.name) LIKE %s" for _ in OBLIGATION_KEYWORDS)
        kw_params = [f"%{kw}%" for kw in OBLIGATION_KEYWORDS]

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN categories c ON t.category_id = c.id "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND ({kw_conditions}) {date_sql} "
            f"GROUP BY month ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + kw_params + date_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        months = [r[0] for r in rows]
        totals = [float(r[1]) for r in rows]
        ytd = round(sum(totals), 2)
        avg = (ytd / len(totals)) if totals else 0.0
        extra = round(sum(max(t - avg, 0.0) for t in totals), 2)

        return jsonify({'success': True, 'data': {
            'months': months, 'totals': totals, 'ytd': ytd,
            'extra_ytd': extra, 'avg_monthly': round(avg, 2),
        }}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 7. Potential to save ──────────────────────────────────────────────────────

@api_reports_data_bp.route('/potential-to-save', methods=['GET'])
@api_login_required
def potential_to_save():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '1M')
        mysql = get_mysql()

        acc_ids = _owned_account_ids(mysql, user_id, request.args.get('account_ids', ''))
        acc_sql, acc_params = _in_clause('t.account_id', acc_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, t.type, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.is_transfer = FALSE {date_sql} {acc_sql} "
            f"GROUP BY month, t.type ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + acc_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        pivot = {}
        for month, ttype, total in rows:
            pivot.setdefault(month, {'income': 0.0, 'expense': 0.0})
            pivot[month][ttype] = float(total)

        sorted_months = sorted(pivot.keys())
        net_by_month = [round(pivot[m]['income'] - pivot[m]['expense'], 2) for m in sorted_months]
        cumulative, running = [], 0.0
        for n in net_by_month:
            running += n
            cumulative.append(round(running, 2))

        current_net = net_by_month[-1] if net_by_month else 0.0

        return jsonify({'success': True, 'data': {
            'months': sorted_months, 'net': net_by_month,
            'cumulative': cumulative, 'current_net': current_net,
        }}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 8. Savings goals progress ─────────────────────────────────────────────────

@api_reports_data_bp.route('/savings-goals', methods=['GET'])
@api_login_required
def savings_goals():
    try:
        user_id = session['user_id']
        mysql = get_mysql()

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, target_amount, current_amount, target_date, status "
            "FROM savings_goals WHERE user_id = %s AND status = 'active' ORDER BY target_date ASC",
            (user_id,)
        )
        rows = cursor.fetchall()
        cursor.close()

        goals = []
        for r in rows:
            target = float(r[2]) if r[2] else 0.0
            current = float(r[3]) if r[3] else 0.0
            pct = round(current / target * 100, 1) if target > 0 else 0.0
            goals.append({
                'id': r[0], 'name': r[1], 'target_amount': target, 'current_amount': current,
                'pct': pct, 'target_date': str(r[4]) if r[4] else None,
                'remaining': round(max(target - current, 0.0), 2),
            })

        return jsonify({'success': True, 'data': {'goals': goals}}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 9. Budget vs Actual ───────────────────────────────────────────────────────

@api_reports_data_bp.route('/budget-vs-actual', methods=['GET'])
@api_login_required
def budget_vs_actual():
    try:
        user_id = session['user_id']
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        cat_sql, cat_params = _in_clause('bc.category_id', cat_ids)

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, name, start_date, end_date FROM budgets "
            "WHERE user_id = %s AND is_active = TRUE ORDER BY start_date DESC LIMIT 1",
            (user_id,)
        )
        budget_row = cursor.fetchone()

        if not budget_row:
            cursor.close()
            return jsonify({'success': True, 'data': {'categories': [], 'budget_name': None}}), 200

        budget_id, budget_name, start_date, end_date = budget_row

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'ac.currency', rate_map)
        cursor.execute(
            f"SELECT c.name, bc.limit_amount, COALESCE(SUM({case_sql}), 0) AS spent "
            f"FROM budget_categories bc "
            f"LEFT JOIN categories c ON bc.category_id = c.id "
            f"LEFT JOIN transactions t ON t.category_id = bc.category_id "
            f"  AND t.type = 'expense' AND t.transaction_date BETWEEN %s AND %s AND t.user_id = %s "
            f"LEFT JOIN accounts ac ON t.account_id = ac.id "
            f"WHERE bc.budget_id = %s {cat_sql} "
            f"GROUP BY bc.category_id, c.name, bc.limit_amount ORDER BY bc.limit_amount DESC",
            tuple(rate_case_params(rate_map) + [start_date, end_date, user_id, budget_id] + cat_params)
        )
        rows = cursor.fetchall()
        cursor.close()

        categories = [{
            'name': r[0], 'budget': float(r[1]), 'actual': float(r[2]), 'over': float(r[2]) > float(r[1]),
        } for r in rows]

        return jsonify({'success': True, 'data': {'budget_name': budget_name, 'categories': categories}}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 10. Spending trend & anomaly detection ────────────────────────────────────
# Anomaly detection itself now lives in Transaction.get_monthly_anomalies()
# (Sprint 25) — relocated so the AI-insight scheduler job can reuse it.

@api_reports_data_bp.route('/spending-trend', methods=['GET'])
@api_login_required
def spending_trend():
    try:
        user_id = session['user_id']
        period = _period(request.args.get('period'), '6M')
        mysql = get_mysql()

        cat_ids = _owned_category_ids(mysql, user_id, request.args.get('category_ids', ''))
        acc_ids = _owned_account_ids(mysql, user_id, request.args.get('account_ids', ''))
        cat_sql, cat_params = _in_clause('t.category_id', cat_ids)
        acc_sql, acc_params = _in_clause('t.account_id', acc_ids)
        start = _start_date(period)
        date_sql = "AND t.transaction_date >= %s" if start else ""
        date_params = [start] if start else []

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)
        cursor = mysql.connection.cursor()
        cursor.execute(
            f"SELECT DATE_FORMAT(t.transaction_date, '%%Y-%%m') AS month, SUM({case_sql}) AS total "
            f"FROM transactions t "
            f"LEFT JOIN accounts a ON t.account_id = a.id "
            f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE {date_sql} {cat_sql} {acc_sql} "
            f"GROUP BY month ORDER BY month ASC",
            tuple(rate_case_params(rate_map) + [user_id] + date_params + cat_params + acc_params)
        )
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

        return jsonify({'success': True, 'data': {
            'months': months, 'totals': totals, 'moving_avg': moving_avg, 'anomalies': anomalies,
        }}), 200
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ── 11. Year-over-year category comparison ────────────────────────────────────

@api_reports_data_bp.route('/yoy-comparison', methods=['GET'])
@api_login_required
def yoy_comparison():
    """
    This year (Jan 1 -> today) vs last year (Jan 1 -> Dec 31), per category.
    Intentionally not day-of-year-adjusted — "this year" is year-to-date,
    "last year" is a full calendar year, a known simplification stated in
    the sprint plan (Sprint 20 scope decision 2).
    """
    try:
        user_id = session['user_id']
        mysql = get_mysql()

        today = datetime.now().date()
        this_year_start = f"{today.year}-01-01"
        last_year_start = f"{today.year - 1}-01-01"
        last_year_end = f"{today.year - 1}-12-31"

        rate_map = get_rate_map(mysql)
        case_sql = rate_case_sql('t.amount', 'a.currency', rate_map)

        def _totals_by_category(date_from, date_to):
            cursor = mysql.connection.cursor()
            cursor.execute(
                f"SELECT COALESCE(c.name, 'Uncategorized') AS category, SUM({case_sql}) AS total "
                f"FROM transactions t "
                f"LEFT JOIN categories c ON t.category_id = c.id "
                f"LEFT JOIN accounts a ON t.account_id = a.id "
                f"WHERE t.user_id = %s AND t.type = 'expense' AND t.is_transfer = FALSE "
                f"AND t.transaction_date BETWEEN %s AND %s "
                f"GROUP BY t.category_id, c.name",
                tuple(rate_case_params(rate_map) + [user_id, date_from, date_to])
            )
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
    except Exception:
        return jsonify({'success': False, 'message': 'Server error'}), 500
