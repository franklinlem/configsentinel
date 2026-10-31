-- Executed as owner only after migration. Explicit grants prevent future tables
-- from accidentally inheriting write access. No DDL, TRUNCATE or audit mutation.
GRANT USAGE ON SCHEMA public TO configsentinel_runtime;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM configsentinel_runtime;
GRANT SELECT ON schema_migrations, organizations, users, projects, memberships,
 environments, servers, agents, agent_tokens, user_sessions, change_events,
 file_observations, acknowledgements, audit_logs TO configsentinel_runtime;
GRANT INSERT ON organizations, users, projects, memberships, environments,
 servers, agents, agent_tokens, user_sessions, change_events,
 file_observations, acknowledgements, audit_logs TO configsentinel_runtime;
GRANT UPDATE (password_hash) ON users TO configsentinel_runtime;
GRANT UPDATE ON agents, agent_tokens, user_sessions, file_observations TO configsentinel_runtime;
GRANT DELETE ON change_events, user_sessions TO configsentinel_runtime;
