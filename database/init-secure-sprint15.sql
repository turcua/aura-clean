-- Aura Financial Tracker - Secure Database Schema
-- Sprint 15: Security Hardening & Audit
--
-- Adds account-lockout expiry. Sprint 1 already tracked failed_login_attempts
-- and locked the account permanently once Config.MAX_LOGIN_ATTEMPTS was hit
-- ("contact support", with no support channel) — Config.LOGIN_TIMEOUT_MINUTES
-- existed but was never actually read anywhere. locked_until lets
-- User.authenticate() auto-unlock the account once that timeout has passed,
-- instead of a permanent lockout.

USE aura_secure;

ALTER TABLE users
    ADD COLUMN locked_until TIMESTAMP NULL DEFAULT NULL;
