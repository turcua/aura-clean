-- Aura Financial Tracker - Secure Database Schema
-- Sprint 14: Export/Import + Reports + Multi-Dashboard System
--
-- Security contrast with vulnerable-version/database/init-vulnerable-sprint8.sql
-- and init-vulnerable-sprint9b.sql:
--   - Same FK shape (dashboards.user_id -> users.id, dashboard_widgets.dashboard_id
--     -> dashboards.id, both ON DELETE CASCADE), but ownership is additionally
--     enforced at the query layer (see models/dashboard.py, models/dashboard_widget.py)
--     since dashboard_widgets has no user_id column of its own — every widget
--     query must JOIN back to dashboards to check ownership.
--   - widget_type, time_period, and chart_type get CHECK constraints (defense in
--     depth on top of application-layer whitelist validation) — vulnerable's
--     schema leaves these as free-text VARCHAR with no enum enforcement at all.
--   - chart_type/filter_config/custom_title are part of this table from day one
--     rather than a follow-up ALTER (vulnerable added them in a separate 9b
--     migration after ownership issues were already baked in).

USE aura_secure;

CREATE TABLE IF NOT EXISTS dashboards (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_active   BOOLEAN DEFAULT FALSE,
    sort_order  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    dashboard_id  INT NOT NULL,
    widget_type   VARCHAR(50) NOT NULL,
    is_enabled    BOOLEAN DEFAULT TRUE,
    is_minimized  BOOLEAN DEFAULT FALSE,
    time_period   VARCHAR(10) DEFAULT '1M',
    position      INT DEFAULT 0,
    chart_type    VARCHAR(20)  DEFAULT NULL,
    filter_config JSON         DEFAULT NULL,
    custom_title  VARCHAR(150) DEFAULT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE,
    CHECK (widget_type IN (
        'income_expense_bar', 'expense_donut', 'recent_transactions',
        'savings_goals_progress', 'budget_vs_actual', 'potential_to_save',
        'category_heatmap', 'top_categories_trend', 'fixed_vs_variable',
        'obligations_monthly', 'extra_repayments_ytd', 'debt_payments_metric'
    )),
    CHECK (time_period IN ('1M', '3M', '6M', '1Y', 'ALL')),
    CHECK (chart_type IS NULL OR chart_type IN ('bar', 'line', 'donut'))
);
