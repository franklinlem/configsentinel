ALTER TABLE agents ADD COLUMN queue_capacity integer CHECK (queue_capacity BETWEEN 1 AND 100000);
INSERT INTO schema_migrations(version) VALUES(2);
