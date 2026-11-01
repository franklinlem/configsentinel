<?php
require '/var/www/html/vendor/autoload.php';$app=require '/var/www/html/bootstrap/app.php';$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$db=Illuminate\Support\Facades\DB::connection();
if(!preg_match('/^j5_(entry|buffer)_[a-f0-9]{12}$/',$db->getDatabaseName())||$db->getDriverName()!=='pgsql'||$db->getConfig('host')!==getenv('DB_HOST')||!str_starts_with(getenv('DB_HOST'),'configsentinel-j5-diagnostic-'))throw new RuntimeException('wrong_database_scope');
if(!hash_equals((string)getenv('APP_KEY'),(string)config('app.key')))throw new RuntimeException('wrong_encryption_scope');
$statements=[
'CREATE TABLE applications (id bigint PRIMARY KEY, uuid text, name text, git_branch text, git_commit_sha text, docker_compose_location text, docker_compose_custom_build_command text, docker_compose_custom_start_command text, deleted_at timestamptz, created_at timestamptz, updated_at timestamptz)',
'CREATE TABLE servers (id bigint primary key, deleted_at timestamptz)',
'CREATE TABLE standalone_dockers (id bigint primary key)',
'CREATE TABLE additional_destinations (server_id bigint, standalone_docker_id bigint, application_id bigint)',
'CREATE TABLE application_deployment_queues (id bigint primary key, application_id bigint, status text)',
'CREATE TABLE application_settings (id bigint primary key, application_id bigint, is_raw_compose_deployment_enabled boolean, is_build_server_enabled boolean, is_auto_deploy_enabled boolean, created_at timestamptz, updated_at timestamptz)',
'CREATE TABLE environment_variables (id bigserial primary key, uuid text, resourceable_type text, resourceable_id bigint, key text, value text, is_preview boolean default false, is_literal boolean default false, is_runtime boolean default true, is_buildtime boolean default true, is_multiline boolean default false, is_shown_once boolean default false, is_shared boolean default false, is_required boolean default false, version varchar(255) NOT NULL DEFAULT \'4.0.0-beta.239\', uses_legacy_escaping boolean NOT NULL DEFAULT false, preserve_compose_null boolean NOT NULL DEFAULT false, created_at timestamptz, updated_at timestamptz)'];
foreach($statements as $statement)$db->statement($statement);
$db->table('applications')->insert(['id'=>1,'uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','name'=>'synthetic-only','git_branch'=>'main','git_commit_sha'=>'5819b7fce93c10cceabbe59fde5fac4f647b707c','docker_compose_location'=>'/deploy/compose.coolify.yml']);
$db->table('application_settings')->insert(['id'=>1,'application_id'=>1,'is_raw_compose_deployment_enabled'=>true,'is_build_server_enabled'=>false,'is_auto_deploy_enabled'=>false]);
$db->table('environment_variables')->insert(['uuid'=>(string)Illuminate\Support\Str::uuid(),'resourceable_type'=>App\Models\Application::class,'resourceable_id'=>1,'key'=>'POSTGRES_PASSWORD','value'=>encrypt('synthetic-password-only'),'is_preview'=>false]);
echo json_encode(['database'=>'synthetic PostgreSQL 15','scope_verified'=>true,'synthetic_key_only'=>true,'fixture_created'=>true]);
