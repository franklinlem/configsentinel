<?php
// Must run inside the existing isolated Coolify/PostgreSQL fixture only.
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
use Illuminate\Support\Facades\DB;
$db=DB::connection();
if ($db->getDriverName()!=='pgsql' || $db->getDatabaseName()!=='j5_synthetic' || getenv('J5_SYNTHETIC_ONLY')!=='1' || !str_starts_with($db->getConfig('host'),'configsentinel-j5-phase1-')) throw new RuntimeException('wrong_scope');
$schema='web_review_'.bin2hex(random_bytes(4));
$db->statement('CREATE SCHEMA '.$schema);$db->statement('SET search_path TO '.$schema);$db->unprepared(file_get_contents('/tmp/j5/schema.sql'));
$api='ghcr.io/franklinlem/configsentinel-api@sha256:ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4';
$old='ghcr.io/franklinlem/configsentinel-web@sha256:e7604db734053aed8834c0c4025001fcafab1026e50bca1f8b02aee1fb6cd8d3';
$new='ghcr.io/franklinlem/configsentinel-web@sha256:e28a1b50c5242cf615e0531399daea63c93e7989370cdfa912c1243784f65bba';
$pg='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
$build="docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($x)=>explode('@',$x,2)[1],[$api,$old,$pg]));
$start='docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
$db->table('applications')->insert(['id'=>1,'uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','name'=>'synthetic','git_branch'=>'plan/active-homologation-rc2','git_commit_sha'=>'36baf66f4656f86d157cd070202323db9465c5f4','docker_compose_location'=>'/deploy/compose.active-homologation.yml','docker_compose_custom_build_command'=>$build,'docker_compose_custom_start_command'=>$start]);
$db->table('application_settings')->insert(['id'=>1,'application_id'=>1,'is_raw_compose_deployment_enabled'=>true,'is_build_server_enabled'=>false,'is_auto_deploy_enabled'=>false]);
$values=['CONFIGSENTINEL_API_IMAGE'=>$api,'CONFIGSENTINEL_MIGRATION_IMAGE'=>$api,'CONFIGSENTINEL_DB_IMAGE'=>$pg,'CONFIGSENTINEL_WEB_IMAGE'=>$old,'POSTGRES_PASSWORD'=>'fake-password','RUNTIME_DB_PASSWORD'=>str_repeat('a',64),'MIGRATOR_DB_PASSWORD'=>str_repeat('b',64)];
foreach($values as $k=>$v)$db->table('environment_variables')->insert(['uuid'=>(string)Illuminate\Support\Str::uuid(),'resourceable_type'=>App\Models\Application::class,'resourceable_id'=>1,'key'=>$k,'value'=>encrypt($v),'is_preview'=>false,'is_literal'=>true,'is_runtime'=>true,'is_buildtime'=>false,'is_shown_once'=>true]);
$p=['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','new_image'=>$new];
$snapshot=static fn()=>serialize([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$before=$snapshot();
$inject=true;DB::listen(function($q)use(&$inject){if($inject&&str_starts_with(strtolower($q->sql),'update "environment_variables"')){$inject=false;throw new RuntimeException('injected');}});
$failed=false;try{configsentinel_web_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='injected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback_failed');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_web_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue_guard_failed');$db->table('application_deployment_queues')->delete();
$a=configsentinel_web_upgrade($p);$after=$snapshot();$b=configsentinel_web_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence_failed');
echo json_encode(['scope'=>'synthetic PostgreSQL only','rollback'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','schema_preserved'=>$schema,'credentials_disclosed'=>false]),PHP_EOL;
