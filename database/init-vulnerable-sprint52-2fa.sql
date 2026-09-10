USE aura_vulnerable;

-- Same schema change as secure-version's Sprint 52 migration (see
-- database/init-secure-sprint52-2fa.sql). The column addition itself is not
-- part of this app's intentional vulnerability set — the missing
-- rate-limiting on TOTP verification attempts (routes/auth.py) is where
-- this version's intentional vulnerability lives, not the schema.
ALTER TABLE users
    ADD COLUMN totp_secret VARCHAR(32) NULL,
    ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;

SELECT 'Vulnerable Sprint 52 schema (users 2FA columns) created successfully!' AS status;
