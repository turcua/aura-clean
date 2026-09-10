USE aura_secure;

-- The widget_type CHECK constraint on dashboard_widgets was created in
-- Sprint 14 without an explicit name, so MySQL auto-generated one. Since
-- that name can't be safely hard-coded (and MySQL has no ALTER ... MODIFY
-- CHECK), look it up dynamically, drop it, and recreate it under an
-- explicit name so future migrations don't have to repeat this.
SET @cname = (
  SELECT tc.CONSTRAINT_NAME
  FROM information_schema.TABLE_CONSTRAINTS tc
  JOIN information_schema.CHECK_CONSTRAINTS cc
    ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
  WHERE tc.TABLE_SCHEMA = 'aura_secure'
    AND tc.TABLE_NAME = 'dashboard_widgets'
    AND tc.CONSTRAINT_TYPE = 'CHECK'
    AND cc.CHECK_CLAUSE LIKE '%widget_type%'
  LIMIT 1
);

SET @drop_sql = CONCAT('ALTER TABLE dashboard_widgets DROP CHECK ', @cname);
PREPARE stmt FROM @drop_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE dashboard_widgets
  ADD CONSTRAINT chk_widget_type CHECK (widget_type IN (
    'income_expense_bar', 'expense_donut', 'recent_transactions',
    'savings_goals_progress', 'budget_vs_actual', 'potential_to_save',
    'category_heatmap', 'top_categories_trend', 'fixed_vs_variable',
    'obligations_monthly', 'extra_repayments_ytd', 'debt_payments_metric',
    'spending_trend', 'yoy_category_comparison'
  ));

SELECT 'Secure Sprint 20 schema created successfully!' AS status;
