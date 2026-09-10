USE aura_vulnerable;

-- Same schema change as secure-version's Sprint 51 migration (see
-- database/init-secure-sprint51-recurring-loan-link.sql). This column
-- addition itself is not part of this app's intentional vulnerability set.
ALTER TABLE recurring_transactions ADD COLUMN loan_id INT NULL,
    ADD FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL;

SELECT 'Vulnerable Sprint 51 schema (recurring_transactions.loan_id) created successfully!' AS status;
