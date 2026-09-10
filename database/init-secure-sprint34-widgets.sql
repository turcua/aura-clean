USE aura_secure;

-- Ad-hoc fix (not originally scoped for a numbered sprint): the
-- chk_widget_type CHECK constraint (defense-in-depth on top of the
-- application-layer WIDGET_TITLES whitelist, see models/dashboard_widget.py)
-- was never updated when 5 new Loan Intelligence / Dashboard widget types
-- were added this release — loans_overview, loan_trajectory,
-- debt_reduction_impact, interest_overview, and budget_accounts all passed
-- the Python-layer check but were then rejected by this stale DB constraint,
-- surfacing as "Invalid widget type, or dashboard not found" only in
-- environments where this migration (originally applied in Sprint 30,
-- init-secure-sprint30.sql) had actually been applied — i.e. k8s, but not
-- necessarily docker-compose if that volume predates it.
ALTER TABLE dashboard_widgets DROP CHECK chk_widget_type;

ALTER TABLE dashboard_widgets
  ADD CONSTRAINT chk_widget_type CHECK (widget_type IN (
    'income_expense_bar', 'expense_donut', 'recent_transactions',
    'savings_goals_progress', 'budget_vs_actual', 'potential_to_save',
    'category_heatmap', 'top_categories_trend', 'fixed_vs_variable',
    'obligations_monthly', 'extra_repayments_ytd', 'debt_payments_metric',
    'spending_trend', 'yoy_category_comparison', 'loan_summary',
    'loans_overview', 'loan_trajectory', 'debt_reduction_impact',
    'interest_overview', 'budget_accounts'
  ));

SELECT 'Secure Sprint 34 (widget types) schema updated successfully!' AS status;
