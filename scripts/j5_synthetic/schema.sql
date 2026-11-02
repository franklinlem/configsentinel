-- Synthetic subset, not claimed to reproduce installed metadata DDL.
CREATE TABLE applications (
 id bigint PRIMARY KEY, uuid text NOT NULL UNIQUE, name text NOT NULL,
 git_branch text, git_commit_sha text, docker_compose_location text,
 docker_compose_custom_build_command text, docker_compose_custom_start_command text,
 deleted_at timestamptz, created_at timestamptz, updated_at timestamptz
);
CREATE TABLE servers (id bigint PRIMARY KEY, deleted_at timestamptz);
CREATE TABLE standalone_dockers (id bigint PRIMARY KEY);
CREATE TABLE additional_destinations (
 server_id bigint REFERENCES servers(id), standalone_docker_id bigint REFERENCES standalone_dockers(id),
 application_id bigint REFERENCES applications(id), UNIQUE(server_id,standalone_docker_id,application_id)
);
CREATE TABLE application_deployment_queues (
 id bigint PRIMARY KEY, application_id bigint NOT NULL REFERENCES applications(id),
 status text NOT NULL CHECK(status IN ('queued','in_progress','finished','failed'))
);
CREATE TABLE application_settings (
 id bigint PRIMARY KEY, application_id bigint NOT NULL UNIQUE REFERENCES applications(id),
 is_raw_compose_deployment_enabled boolean NOT NULL,
 is_build_server_enabled boolean NOT NULL, is_auto_deploy_enabled boolean NOT NULL,
 created_at timestamptz, updated_at timestamptz
);
CREATE TABLE environment_variables (
 id bigserial PRIMARY KEY, uuid text NOT NULL UNIQUE, resourceable_type text NOT NULL,
 resourceable_id bigint NOT NULL, key text NOT NULL CHECK(length(key)>0), value text,
 is_preview boolean DEFAULT false, is_literal boolean DEFAULT false, is_runtime boolean DEFAULT true,
 is_buildtime boolean DEFAULT true, is_multiline boolean DEFAULT false, is_shown_once boolean DEFAULT false,
 is_shared boolean DEFAULT false, is_required boolean DEFAULT false,
 version varchar(255) NOT NULL DEFAULT '4.0.0-beta.239', uses_legacy_escaping boolean NOT NULL DEFAULT false,
 preserve_compose_null boolean NOT NULL DEFAULT false, created_at timestamptz, updated_at timestamptz
);
-- Polymorphic resourceable_id intentionally has no invented applications FK.
-- No invented env-key UNIQUE: helper must detect duplicate keys itself.
