USE aura_vulnerable;

-- Soft-delete for loan_events — same schema change as secure-version's
-- Sprint 49 migration (see database/init-secure-sprint49-loan-soft-delete.sql).
-- This column addition itself is not part of this app's intentional
-- vulnerability set; the vulnerable SQL/IDOR behavior around it lives in
-- models/loan.py's LoanEvent class, unchanged in kind by this migration.
ALTER TABLE loan_events ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL;

SELECT 'Vulnerable Sprint 49 schema (loan_events soft-delete) created successfully!' AS status;
