"""
Aura Financial Tracker - Secure Version
Main Application File
Sprint 1: Water Breathing - First Form
"""

from flask import Flask, render_template, session, redirect, url_for, jsonify
from flask_mysqldb import MySQL
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from prometheus_flask_exporter import PrometheusMetrics
from config import Config
from extensions import limiter
from logging_config import configure_json_logging
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

configure_json_logging(app)  # Sprint 16 (OBS-001): structured JSON logs on stdout

# Initialize MySQL
mysql = MySQL(app)

app.extensions['mysql'] = mysql

# Sprint 15: CSRF protection (Flask-WTF) + rate limiting (Flask-Limiter)
# CSRFProtect checks every state-changing request (anything but GET/HEAD/OPTIONS/
# TRACE) for a valid token — traditional forms carry it as a hidden csrf_token
# field; the JS fetch() layer carries it as an X-CSRFToken header (injected
# automatically by the patched fetch() in theme-switcher.js, read from the
# <meta name="csrf-token"> tag base.html renders on every page).
csrf = CSRFProtect(app)
limiter.init_app(app)

# Sprint 16 (K8S-003): /metrics endpoint for Prometheus — request count and
# latency histograms, auto-instrumented for every route. Intentionally left
# unauthenticated (the Prometheus-scraping norm); access is restricted at the
# network layer instead (only aura-monitoring's Prometheus pod can reach it
# in-cluster — see k8s/base/monitoring/03-prometheus.yaml), not at the app layer.
metrics = PrometheusMetrics(app, path='/metrics')


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """
    JSON error for API/fetch requests — a raw Flask-WTF HTML error page would
    break every fetch().then(r => r.json()) call site the same way an
    HTML-redirect-on-401 would (see api_login_required in routes/main.py).
    """
    return jsonify({'success': False, 'message': 'CSRF token missing or invalid — please refresh the page and try again'}), 400


@app.after_request
def set_security_headers(response):
    """
    Post-Sprint-16 security audit fix: real HTTP response headers, not just
    the <meta http-equiv> tags in base.html. This matters because:
    - X-Frame-Options has NO EFFECT as a meta tag in any real browser — it
      must be an HTTP header, so the app previously had zero clickjacking
      protection despite base.html appearing to set it.
    - A meta-tag CSP can't set frame-ancestors (the actual CSP anti-framing
      directive) or apply to non-HTML responses (/health, /metrics, the
      /api/export/* file downloads) — this header-based CSP covers all of them.
    - HSTS/Referrer-Policy/Permissions-Policy have no meta-tag equivalent at all.
    HSTS is only sent when the app isn't running in local HTTP dev mode —
    sending it over plain HTTP is meaningless and, on a real domain, can
    lock browsers into HTTPS-only prematurely.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        # img-src (Sprint 52, ENH-04): without this, img-src falls back to
        # default-src 'self', which blocks data: URIs — the 2FA setup QR
        # code is rendered as an inline base64 PNG (routes/auth.py's
        # _qr_data_uri()) specifically to avoid a separate image-serving
        # route/session-state, so it needs data: explicitly allowed here.
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.route('/health')
def health():
    """
    Sprint 16 (OBS-002): liveness/readiness target for Kubernetes probes
    (see k8s/base/secure/02-app.yaml). Checks DB connectivity with a trivial
    query; returns 503 (not 200) if the database is unreachable so Kubernetes
    stops routing traffic to this pod and, for the liveness probe, eventually
    restarts it.
    """
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

# Import routes
from routes.auth import auth_bp
from routes.main import main_bp
from routes.categories import categories_bp
from routes.transactions import transactions_bp
from routes.accounts import accounts_bp
from routes.recurring import recurring_bp
from routes.budgets import budgets_bp
from routes.goals import goals_bp
from routes.reports import reports_bp
from routes.exchange_rates import exchange_rates_bp
from routes.loans import loans_bp
from routes.api.categories import api_categories_bp
from routes.api.transactions import api_transactions_bp
from routes.api.accounts import api_accounts_bp
from routes.api.recurring import api_recurring_bp
from routes.api.transfers import api_transfers_bp
from routes.api.budgets import api_budgets_bp
from routes.api.savings_goals import api_goals_bp
from routes.api.dashboards import api_dashboards_bp
from routes.api.reports_data import api_reports_data_bp
from routes.api.export import api_export_bp
from routes.api.exchange_rates import api_exchange_rates_bp
from routes.api.currencies import api_currencies_bp
from routes.api.notifications import api_notifications_bp
from routes.api.ai_advisor import api_ai_advisor_bp
from routes.api.loans import api_loans_bp
from routes.api.users import api_users_bp
from routes.api.admin import api_admin_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(categories_bp, url_prefix='/categories')
app.register_blueprint(transactions_bp, url_prefix='/transactions')
app.register_blueprint(accounts_bp, url_prefix='/accounts')
app.register_blueprint(recurring_bp, url_prefix='/recurring')
app.register_blueprint(budgets_bp, url_prefix='/budgets')
app.register_blueprint(goals_bp, url_prefix='/goals')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(exchange_rates_bp, url_prefix='/exchange-rates')
app.register_blueprint(loans_bp, url_prefix='/loans')
app.register_blueprint(api_categories_bp, url_prefix='/api/categories')
app.register_blueprint(api_transactions_bp, url_prefix='/api/transactions')
app.register_blueprint(api_accounts_bp, url_prefix='/api/accounts')
app.register_blueprint(api_recurring_bp, url_prefix='/api/recurring')
app.register_blueprint(api_transfers_bp, url_prefix='/api/transfers')
app.register_blueprint(api_budgets_bp, url_prefix='/api/budgets')
app.register_blueprint(api_goals_bp, url_prefix='/api/goals')
app.register_blueprint(api_dashboards_bp, url_prefix='/api/dashboards')
app.register_blueprint(api_reports_data_bp, url_prefix='/api/reports-data')
app.register_blueprint(api_export_bp, url_prefix='/api/export')
app.register_blueprint(api_exchange_rates_bp, url_prefix='/api/exchange-rates')
app.register_blueprint(api_currencies_bp, url_prefix='/api/currencies')
app.register_blueprint(api_notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(api_ai_advisor_bp, url_prefix='/api/ai-advisor')
app.register_blueprint(api_loans_bp, url_prefix='/api/loans')
app.register_blueprint(api_users_bp, url_prefix='/api/users')
app.register_blueprint(api_admin_bp, url_prefix='/api/admin')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# Context processor for global variables
@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    return {
        'app_name': app.config['APP_NAME'],
        'app_version': app.config['APP_VERSION']
    }

# APScheduler — hourly recurring transaction generation (Sprint 12)
from scheduler import init_scheduler
init_scheduler(app)

if __name__ == '__main__':
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
