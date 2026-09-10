USE aura_secure;

-- Sprint 51 (ENH-12): optionally link a recurring transaction to a loan, so
-- the scheduler can generate it using the loan's current computed
-- installment instead of a static stored amount. NULL for every recurring
-- transaction not linked to a loan (the overwhelming majority) — no
-- behavior change for those. ON DELETE SET NULL matches the existing
-- transactions.loan_id / accounts.loan_id pattern from Sprint 28: deleting
-- a loan unlinks recurring transactions tagged to it rather than deleting
-- them.
ALTER TABLE recurring_transactions ADD COLUMN loan_id INT NULL,
    ADD FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL;

SELECT 'Secure Sprint 51 schema (recurring_transactions.loan_id) created successfully!' AS status;
