-- Aura Financial Tracker - Vulnerable Database Schema
-- Sprint 8: Flame Breathing - Eighth Form
-- Multi-Dashboard System with Configurable Widgets
-- Intentional vulnerabilities preserved by design

USE aura_vulnerable;

-- ============================================================================
-- ENH-005: Multi-Dashboard System
-- dashboards: named dashboard containers per user
-- VULNERABILITY: No row-level ownership check — IDOR via dashboard_id
-- VULNERABILITY: sort_order accepts any integer — no bounds validation
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboards (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_active   BOOLEAN DEFAULT FALSE,
    sort_order  INT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================================
-- ENH-005: Dashboard Widgets
-- One row per widget slot — type, state (minimized/enabled), per-widget period
-- VULNERABILITY: widget_type is a free-text VARCHAR — no enum enforcement
-- VULNERABILITY: time_period not validated — accepts any string
-- VULNERABILITY: is_minimized / is_enabled toggled without ownership check (IDOR)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    dashboard_id INT NOT NULL,
    widget_type  VARCHAR(50) NOT NULL,
    is_enabled   BOOLEAN DEFAULT TRUE,
    is_minimized BOOLEAN DEFAULT FALSE,
    time_period  VARCHAR(10) DEFAULT '1M',
    position     INT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE
);
