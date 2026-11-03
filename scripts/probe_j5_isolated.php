<?php
// Run only inside installed Coolify; its SQLite database is private in-memory.
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
use Illuminate\Support\Facades\DB;
DB::purge('configsentinel_j5_isolated');
config(['database.connections.configsentinel_j5_isolated'=>['driver'=>'sqlite','database'=>':memory:','prefix'=>'','foreign_key_constraints'=>true]]);
DB::setDefaultConnection('configsentinel_j5_isolated');
$db=DB::connection();if($db->getDatabaseName()!==':memory:')throw new RuntimeException('not_isolated');
$db->statement('CREATE TABLE applications (id integer primary key, uuid text, name text, git_branch text, git_commit_sha text, docker_compose_location text, docker_compose_custom_build_command text, docker_compose_custom_start_command text, deleted_at text, created_at text, updated_at text)');
$db->statement('CREATE TABLE servers (id integer primary key, deleted_at text)');
$db->statement('CREATE TABLE standalone_dockers (id integer primary key)');
$db->statement('CREATE TABLE additional_destinations (server_id integer, standalone_docker_id integer, application_id integer)');
$db->statement('CREATE TABLE application_settings (id integer primary key, application_id integer, is_raw_compose_deployment_enabled integer, is_build_server_enabled integer, is_auto_deploy_enabled integer, created_at text, updated_at text)');
$db->statement('CREATE TABLE environment_variables (id integer primary key autoincrement, uuid text, resourceable_type text, resourceable_id integer, key text, value text, is_preview integer default 0, is_literal integer default 0, is_runtime integer default 1, is_buildtime integer default 1, is_multiline integer default 0, is_shown_once integer default 0, is_shared integer default 0, is_required integer default 0, version text, created_at text, updated_at text)');
$db->table('applications')->insert(['id'=>1,'uuid'=>'configsentinel-j5-isolated','name'=>'synthetic-only','git_branch'=>'main','git_commit_sha'=>'5819b7fce93c10cceabbe59fde5fac4f647b707c','docker_compose_location'=>'/deploy/compose.coolify.yml']);
$db->table('application_settings')->insert(['id'=>1,'application_id'=>1,'is_raw_compose_deployment_enabled'=>1,'is_build_server_enabled'=>0,'is_auto_deploy_enabled'=>0]);
$password="synthetic-\$-hash#-quote'";
$db->table('environment_variables')->insert(['uuid'=>(string)Illuminate\Support\Str::uuid(),'resourceable_type'=>App\Models\Application::class,'resourceable_id'=>1,'key'=>'POSTGRES_PASSWORD','value'=>encrypt($password),'is_preview'=>0]);
$api='ghcr.io/franklinlem/configsentinel-api@sha256:ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4';$fallback='ghcr.io/franklinlem/configsentinel-api@sha256:cacace0b74ddb9bdef72109436035c59305e4c6bb02c063fe0788ce069cffc66';$web='ghcr.io/franklinlem/configsentinel-web@sha256:e7604db734053aed8834c0c4025001fcafab1026e50bca1f8b02aee1fb6cd8d3';$pg='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','commit'=>'36baf66f4656f86d157cd070202323db9465c5f4','branch'=>'plan/active-homologation-rc2','compose'=>'/deploy/compose.active-homologation.yml','custom_build'=>"docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($image)=>explode('@',$image,2)[1],[$api,$web,$pg])),'custom_start'=>'docker compose --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build','env'=>['POSTGRES_PASSWORD'=>$password,'RUNTIME_DB_PASSWORD'=>str_repeat('1',64),'MIGRATOR_DB_PASSWORD'=>str_repeat('2',64),'CONFIGSENTINEL_API_IMAGE'=>$api,'CONFIGSENTINEL_MIGRATION_IMAGE'=>$api,'CONFIGSENTINEL_WEB_IMAGE'=>$web,'CONFIGSENTINEL_DB_IMAGE'=>$pg]];
$before=json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$rollback=false;
try{configsentinel_j5_apply($p,true);}catch(Throwable $e){$rollback=$e->getMessage()==='test_failure';}
if(!$rollback || $before!==json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]))throw new RuntimeException('rollback_failed');
$one=configsentinel_j5_apply($p);$after=json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$two=configsentinel_j5_apply($p);
if(!$one['changed'] || $two['changed'] || $after!==json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]))throw new RuntimeException('idempotency_failed');
$bad=$p;$bad['env']['CONFIGSENTINEL_API_IMAGE']='ghcr.io/franklinlem/configsentinel-api@sha256:'.str_repeat('a',64);$rejected=false;
try{configsentinel_j5_apply($bad);}catch(RuntimeException $e){$rejected=$e->getMessage()==='invalid_input';}
if(!$rejected || $after!==json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]))throw new RuntimeException('invalid_digest_not_rejected');
foreach($p['env'] as $key=>$value){$row=$db->table('environment_variables')->where('key',$key)->first();if(!$row || decrypt($row->value)!==$value)throw new RuntimeException('encrypted_roundtrip_failed');}
$rendered=[];foreach($p['env'] as $key=>$value)$rendered[$key]=escapeComposeEnvFileValue($value,false);
echo json_encode(['version'=>1,'status'=>'ok','data'=>['sqlite_in_memory'=>true,'fake_values_only'=>true,'fault_rolled_back_all_writes'=>true,'idempotent'=>true,'invalid_digest_rejected'=>true,'eloquent_encryption_roundtrip'=>true,'installed_serializer_ran'=>true,'serialized_synthetic_values'=>$rendered,'env_count'=>count($p['env']),'commit'=>$one['commit']],'error'=>null]),PHP_EOL;
