USE aura_secure;

ALTER TABLE dashboard_widgets ADD COLUMN chart_colors JSON DEFAULT NULL;

SELECT 'Secure Sprint 20 chart_colors column added successfully!' AS status;
