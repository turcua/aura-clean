USE aura_vulnerable;

ALTER TABLE dashboard_widgets ADD COLUMN chart_colors JSON DEFAULT NULL;

SELECT 'Vulnerable Sprint 20 chart_colors column added successfully!' AS status;
