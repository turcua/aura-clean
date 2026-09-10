USE aura_vulnerable;

-- Same schema change as secure-version's Sprint 51 migration (see
-- database/init-secure-sprint51-payment-type.sql).
ALTER TABLE transactions ADD COLUMN payment_type VARCHAR(20) NULL;

SELECT 'Vulnerable Sprint 51 schema (transactions.payment_type) created successfully!' AS status;
