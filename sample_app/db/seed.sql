-- Sample data for the database tests. Load the same file into every database.

CREATE TABLE battery_units (
    unit_id      text PRIMARY KEY,
    site         text NOT NULL,
    capacity_mwh numeric NOT NULL
);

CREATE TABLE schema_migrations (
    version text PRIMARY KEY
);

INSERT INTO battery_units VALUES
    ('UPS-001', 'site-a', 2.5),
    ('UPS-002', 'site-a', 2.5),
    ('UPS-003', 'site-b', 5.0);

INSERT INTO schema_migrations VALUES ('2026_01_create_units'), ('2026_02_add_capacity');

-- The QA login can read but not change anything.
CREATE ROLE qa_reader LOGIN PASSWORD 'local-test-only';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qa_reader;
