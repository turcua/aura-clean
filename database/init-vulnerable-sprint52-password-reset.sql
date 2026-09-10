USE aura_vulnerable;

-- Same schema change as secure-version's Sprint 52 migration (see
-- database/init-secure-sprint52-password-reset.sql). The column addition
-- itself is not part of this app's intentional vulnerability set — the
-- weak/predictable token VALUE generated at request time is where this
-- version's intentional vulnerability lives (models/user.py), not the schema.
ALTER TABLE users
    ADD COLUMN reset_token VARCHAR(255) NULL,
    ADD COLUMN reset_token_expires TIMESTAMP NULL;

SELECT 'Vulnerable Sprint 52 schema (users password-reset columns) created successfully!' AS status;
