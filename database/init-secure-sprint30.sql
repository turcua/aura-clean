USE aura_secure;

-- Sprint 20 gave the widget_type CHECK constraint a stable explicit name
-- (chk_widget_type), so this migration can just drop and recreate it
-- directly — no need for the dynamic constraint-name lookup Sprint 20
-- itself needed to work around an auto-generated name.
ALTER TABLE dashboard_widgets DROP CHECK chk_widget_type;

ALTER TABLE dashboard_widgets
  ADD CONSTRAINT chk_widget_type CHECK (widget_type IN (
    'income_expense_bar', 'expense_donut', 'recent_transactions',
    'savings_goals_progress', 'budget_vs_actual', 'potential_to_save',
    'category_heatmap', 'top_categories_trend', 'fixed_vs_variable',
    'obligations_monthly', 'extra_repayments_ytd', 'debt_payments_metric',
    'spending_trend', 'yoy_category_comparison', 'loan_summary'
  ));

SELECT 'Secure Sprint 30 schema updated successfully!' AS status;
