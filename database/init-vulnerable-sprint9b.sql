-- Sprint 9b: Widget Settings — chart type, category/account filters, custom title
-- Adds three configuration columns to dashboard_widgets.
-- Requires a full docker rebuild: docker compose down -v && docker compose up -d

ALTER TABLE dashboard_widgets
    ADD COLUMN chart_type    VARCHAR(20)  DEFAULT NULL,
    ADD COLUMN filter_config JSON         DEFAULT NULL,
    ADD COLUMN custom_title  VARCHAR(150) DEFAULT NULL;
