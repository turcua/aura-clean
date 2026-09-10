USE aura_secure;

-- Sprint 51 (ENH-13): distinguishes extra payments from scheduled (recurring)
-- payments among loan-tagged transactions, so both can be shown together in
-- a ledger without corrupting Loan.get_extra_payments() (which the
-- projection engine reads). NULL for every non-loan-tagged transaction —
-- no behavior change for those. get_extra_payments()'s new filter treats
-- NULL the same as 'extra' (see the method's own docstring for why), so
-- this column's value only matters for rows that already have loan_id set.
ALTER TABLE transactions ADD COLUMN payment_type VARCHAR(20) NULL;

SELECT 'Secure Sprint 51 schema (transactions.payment_type) created successfully!' AS status;
