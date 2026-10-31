\set ON_ERROR_STOP on
-- Only execute as the dedicated database administrator, never the API.
\getenv runtime_password CONFIGSENTINEL_RUNTIME_PASSWORD
\getenv migrator_password CONFIGSENTINEL_MIGRATOR_PASSWORD
DO $$ BEGIN
 IF current_database() <> 'configsentinel' THEN
  RAISE EXCEPTION 'Dedicated configsentinel database required';
 END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='configsentinel_owner') THEN
  CREATE ROLE configsentinel_owner NOLOGIN;
 END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='configsentinel_migrator') THEN
  CREATE ROLE configsentinel_migrator LOGIN NOINHERIT;
 END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='configsentinel_runtime') THEN
  CREATE ROLE configsentinel_runtime LOGIN NOINHERIT;
 END IF;
END $$;
ALTER ROLE configsentinel_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE configsentinel_migrator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'migrator_password';
ALTER ROLE configsentinel_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'runtime_password';
GRANT configsentinel_owner TO configsentinel_migrator;
REVOKE configsentinel_owner, configsentinel_migrator FROM configsentinel_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO configsentinel_owner;
REVOKE ALL ON DATABASE configsentinel FROM PUBLIC;
GRANT CONNECT ON DATABASE configsentinel TO configsentinel_runtime, configsentinel_migrator;
-- Adopt existing application tables without replacing them or changing schema 1.
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['schema_migrations','organizations','users','projects','memberships','environments','servers','agents','agent_tokens','user_sessions','change_events','file_observations','acknowledgements','audit_logs'] LOOP
  IF to_regclass('public.'||name) IS NOT NULL THEN
   EXECUTE format('ALTER TABLE public.%I OWNER TO configsentinel_owner',name);
  END IF;
 END LOOP;
END $$;
