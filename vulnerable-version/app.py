"""
Aura Financial Tracker - Vulnerable Version
Main Application File (WITH INTENTIONAL VULNERABILITIES)
Release 2: Shadow Extractor
"""

from flask import Flask, render_template, session, redirect, url_for, jsonify
from flask_mysqldb import MySQL
from prometheus_flask_exporter import PrometheusMetrics
from config import Config
from logging_config import configure_json_logging
import os
import secrets

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

configure_json_logging(app)  # Sprint 16 (OBS-001): structured JSON logs on stdout

# Initialize MySQL
mysql = MySQL(app)
app.extensions['mysql'] = mysql

# Sprint 16 (K8S-003): /metrics endpoint for Prometheus scraping
metrics = PrometheusMetrics(app, path='/metrics')


@app.route('/health')
def health():
    """Sprint 16 (OBS-002): liveness/readiness target for Kubernetes probes."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    status = 'ok' if db_status == 'ok' else 'degraded'
    status_code = 200 if status == 'ok' else 503
    return jsonify({'status': status, 'checks': {'database': db_status}}), status_code

# ── Sprint 1 & 2 routes ──────────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.main import main_bp
from routes.transactions import transactions_bp
from routes.categories import categories_bp
from routes.api.transactions import api_transactions_bp
from routes.api.categories import api_categories_bp

# ── Sprint 3 & 4 routes ──────────────────────────────────────────────────────
from routes.accounts import accounts_bp
from routes.recurring import recurring_bp
from routes.budgets import budgets_bp
from routes.goals import goals_bp
from routes.api.accounts import api_accounts_bp
from routes.api.recurring import api_recurring_bp
from routes.api.transfers import api_transfers_bp
from routes.api.budgets import api_budgets_bp
from routes.api.savings_goals import api_goals_bp
from routes.api.export import api_export_bp
from routes.reports import reports_bp
from routes.api.dashboards import api_dashboards_bp
from routes.api.reports_data import api_reports_data_bp

# ── Sprint 17 routes ─────────────────────────────────────────────────────────
from routes.exchange_rates import exchange_rates_bp
from routes.api.exchange_rates import api_exchange_rates_bp
from routes.api.notifications import api_notifications_bp
from routes.api.ai_advisor import api_ai_advisor_bp
from routes.api.loans import api_loans_bp
from routes.loans import loans_bp
from routes.api.users import api_users_bp

# ── Sprint 41 route (Release 9 — hidden challenge page, intentionally unlinked) ─
from routes.scoreboard import scoreboard_bp

# ── Sprint 42 (Release 9 — scoreboard progress/leaderboard, intentionally
#     vulnerable in character — VULN-082) ─────────────────────────────────
from routes.api.scoreboard import api_scoreboard_bp

# ── Sprint 46 (Release 9 addendum — CTF organizer control panel, hidden,
#     genuinely safe/parameterized like utils/flag_engine.py) ─────────────
from routes.ctf_admin import ctf_admin_bp
from routes.api.ctf_admin import api_ctf_admin_bp

# ── Register blueprints ───────────────────────────────────────────────────────
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(transactions_bp, url_prefix='/transactions')
app.register_blueprint(categories_bp, url_prefix='/categories')
app.register_blueprint(accounts_bp, url_prefix='/accounts')
app.register_blueprint(recurring_bp, url_prefix='/recurring')
app.register_blueprint(budgets_bp, url_prefix='/budgets')
app.register_blueprint(goals_bp, url_prefix='/goals')

app.register_blueprint(api_transactions_bp, url_prefix='/api/transactions')
app.register_blueprint(api_categories_bp, url_prefix='/api/categories')
app.register_blueprint(api_accounts_bp, url_prefix='/api/accounts')
app.register_blueprint(api_recurring_bp, url_prefix='/api/recurring')
app.register_blueprint(api_transfers_bp, url_prefix='/api/transfers')
app.register_blueprint(api_budgets_bp, url_prefix='/api/budgets')
app.register_blueprint(api_goals_bp, url_prefix='/api/goals')
app.register_blueprint(api_export_bp, url_prefix='/api/export')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(api_dashboards_bp, url_prefix='/api/dashboards')
app.register_blueprint(api_reports_data_bp, url_prefix='/api/reports-data')
app.register_blueprint(exchange_rates_bp, url_prefix='/exchange-rates')
app.register_blueprint(api_exchange_rates_bp, url_prefix='/api/exchange-rates')
app.register_blueprint(api_notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(api_ai_advisor_bp, url_prefix='/api/ai-advisor')
app.register_blueprint(api_loans_bp, url_prefix='/api/loans')
app.register_blueprint(api_users_bp, url_prefix='/api/users')
app.register_blueprint(loans_bp, url_prefix='/loans')
app.register_blueprint(scoreboard_bp)
app.register_blueprint(api_scoreboard_bp, url_prefix='/api/scoreboard')
app.register_blueprint(ctf_admin_bp)
app.register_blueprint(api_ctf_admin_bp, url_prefix='/api/ctf-admin')

# VULNERABILITY: Debug mode enabled, exposing sensitive information
# VULNERABILITY: No security headers
# VULNERABILITY: No CSRF protection implemented

# ── Error handlers (minimal, leaks information) ───────────────────────────────
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors - VULN: Leaks error details"""
    return render_template('404.html', error=error), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - VULN: Leaks stack traces"""
    return render_template('500.html', error=error), 500

# ── Context processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    # Sprint 43: a per-session canary, planted app-wide so any stored/
    # reflected XSS payload (anywhere in the app, not just /scoreboard) can
    # exfiltrate it to /api/scoreboard/xss-capture as proof of genuine
    # script execution — a passive HTML injection without real execution
    # could never read a JS-only variable like this one.
    if 'user_id' in session and 'xss_canary' not in session:
        session['xss_canary'] = secrets.token_hex(12)

    return {
        'app_name': app.config['APP_NAME'],
        'app_version': app.config['APP_VERSION'],
        'xss_canary': session.get('xss_canary'),
    }

# ── APScheduler (Sprint 3) ────────────────────────────────────────────────────
from scheduler import init_scheduler
init_scheduler(app)

if __name__ == '__main__':
    # VULNERABILITY: Running with debug=True in production
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True  # VULN: Always debug mode
    )
