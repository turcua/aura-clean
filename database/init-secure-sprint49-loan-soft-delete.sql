USE aura_secure;

-- Soft-delete for loan_events: deleting a bank snapshot (or any other event)
-- no longer erases it outright. A non-NULL deleted_at excludes the row from
-- LoanEvent.get_by_loan() (and therefore from every projection/timeline that
-- reads it) while keeping it recoverable via LoanEvent.restore() with no
-- time limit, closing a real gap found 2026-08-12: deleting the wrong
-- snapshot meant re-uploading and re-parsing the bank chart PDF from
-- scratch to get back to the prior state.
ALTER TABLE loan_events ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL;

SELECT 'Secure Sprint 49 schema (loan_events soft-delete) created successfully!' AS status;
