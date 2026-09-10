-- Aura Financial Tracker - Secure Version
-- Sprint 53 (UI-02): dashboard stat card display order
-- Comma-separated key list, e.g. "income,expenses,balance,budget" — first
-- server-persisted user UI preference in either version (theme and
-- sidebar-collapsed state are both localStorage-only).
ALTER TABLE users ADD COLUMN stat_card_order VARCHAR(100) NULL;
