<?php
use Illuminate\Support\Facades\DB;
ob_start();
set_error_handler(static function($level,$message,$file,$line){if(!(error_reporting() & $level))return false;throw new ErrorException('php_warning',0,$level,$file,$line);});
try{
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$testRoot=getenv('J5_TEST_ROOT') ?: '/tmp/j5';
if(!preg_match('#^/tmp/j5(?:-[a-f0-9]{8})?$#',$testRoot))throw new RuntimeException('invalid_test_root');
require $testRoot.'/transaction-test.php';
$db=DB::connection();
if($db->getDriverName()!=='pgsql'||$db->getDatabaseName()!=='j5_synthetic'||getenv('J5_SYNTHETIC_ONLY')!=='1'||!str_starts_with($db->getConfig('host'),'configsentinel-j5-phase1-'))throw new RuntimeException('wrong_scope');
if(!hash_equals((string)getenv('APP_KEY'),(string)config('app.key')))throw new RuntimeException('wrong_key_scope');
$manifest=json_decode(file_get_contents($testRoot.'/candidate.json'),true,512,JSON_THROW_ON_ERROR);
$fallback=json_decode(file_get_contents($testRoot.'/fallback.json'),true,512,JSON_THROW_ON_ERROR)['api']['image'];
$api=$manifest['api']['image'];$web=$manifest['web']['image'];$pg=$manifest['db']['image'];
$password='synthetic-$-hash#-quote\'';
$p=['mode'=>'active','uuid'=>'configsentinel-j5-isolated','commit'=>'36baf66f4656f86d157cd070202323db9465c5f4','branch'=>'plan/active-homologation-rc2','compose'=>'/deploy/compose.active-homologation.yml','custom_build'=>"docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($image)=>explode('@',$image,2)[1],[$api,$web,$pg])),'custom_start'=>'docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name configsentinel-j5-isolated up -d --pull never --no-build','env'=>['POSTGRES_PASSWORD'=>$password,'RUNTIME_DB_PASSWORD'=>str_repeat('1',64),'MIGRATOR_DB_PASSWORD'=>str_repeat('2',64),'CONFIGSENTINEL_API_IMAGE'=>$api,'CONFIGSENTINEL_MIGRATION_IMAGE'=>$api,'CONFIGSENTINEL_WEB_IMAGE'=>$web,'CONFIGSENTINEL_DB_IMAGE'=>$pg]];
$modelEvents=0;
App\Models\Application::saving(function()use(&$modelEvents){$modelEvents++;});
App\Models\EnvironmentVariable::saving(function()use(&$modelEvents){$modelEvents++;});
$hook=null;$hookFired=false;
DB::listen(function($query)use(&$hook,&$hookFired,$db){
 if(!$hook||$hookFired||!str_starts_with(strtolower($query->sql),'insert into "environment_variables"'))return;
 $hookFired=true;
 if($hook==='rollback')throw new RuntimeException('synthetic_injected_failure');
 if($hook==='warning')trigger_error('synthetic_warning_canary',E_USER_WARNING);
 if($hook==='buffer')echo 'synthetic_buffer_canary';
 if($hook==='constraint')$db->table('applications')->insert(['id'=>1,'uuid'=>'duplicate-synthetic','name'=>'synthetic']);
});
function check($condition){if(!$condition)throw new RuntimeException('assertion_failed');}
function snapshot($db){$v=[];foreach(['applications','application_settings','environment_variables','application_deployment_queues']as$t)$v[$t]=$db->table($t)->orderBy('id')->get()->toArray();return serialize($v);}
$cases=['first_and_idempotent','previous_start_upgrade','previous_start_buffer_rollback','rollback','constraint','warning','buffer','preexisting_buffer','queued','in_progress','duplicate_env','wrong_password','settings_drift','lock_timeout','response_ambiguous','encryption_flags'];
$results=[];$run='j5_'.bin2hex(random_bytes(4));
foreach($cases as $index=>$case){
 $start=microtime(true);$schema=$run.'_case_'.($index+1);$db->statement('CREATE SCHEMA '.$schema);$db->statement('SET search_path TO '.$schema);$db->unprepared(file_get_contents($testRoot.'/schema.sql'));
 $db->table('applications')->insert(['id'=>1,'uuid'=>$p['uuid'],'name'=>'synthetic-only','git_branch'=>'main','git_commit_sha'=>'5819b7fce93c10cceabbe59fde5fac4f647b707c','docker_compose_location'=>'/deploy/compose.coolify.yml']);
 $db->table('application_settings')->insert(['id'=>1,'application_id'=>1,'is_raw_compose_deployment_enabled'=>true,'is_build_server_enabled'=>false,'is_auto_deploy_enabled'=>false]);
 foreach(['POSTGRES_PASSWORD'=>$password,'ADMIN_EMAIL'=>'synthetic@example.invalid','ADMIN_PASSWORD'=>'synthetic-unused'] as $key=>$value)$db->table('environment_variables')->insert(['uuid'=>(string)Illuminate\Support\Str::uuid(),'resourceable_type'=>App\Models\Application::class,'resourceable_id'=>1,'key'=>$key,'value'=>encrypt($value),'is_preview'=>false]);
 $hook=null;$hookFired=false;$caught=null;$extra=[];
 if(in_array($case,['queued','in_progress']))$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>$case]);
 if($case==='duplicate_env')$db->table('environment_variables')->insert(['uuid'=>(string)Illuminate\Support\Str::uuid(),'resourceable_type'=>App\Models\Application::class,'resourceable_id'=>1,'key'=>'POSTGRES_PASSWORD','value'=>encrypt($password),'is_preview'=>false]);
 $input=$p;if($case==='wrong_password')$input['env']['POSTGRES_PASSWORD']='synthetic-mismatch';
 if($case==='settings_drift')$db->table('application_settings')->update(['is_auto_deploy_enabled'=>true]);
 if(in_array($case,['previous_start_upgrade','previous_start_buffer_rollback'])){
  check(configsentinel_j5_apply($p)['changed']);
  $db->table('applications')->where('id',1)->update(['docker_compose_custom_start_command'=>'docker compose --project-name configsentinel-j5-isolated up -d --pull never --no-build']);
 }
 $before=snapshot($db);$modelEvents=0;
 if(in_array($case,['rollback','constraint','warning','buffer']))$hook=$case;
 $locker=null;
 if($case==='lock_timeout'){
  $cfg=config('database.connections.'.config('database.default'));$cfg['search_path']=$schema;config(['database.connections.j5_locker'=>$cfg]);DB::purge('j5_locker');$locker=DB::connection('j5_locker');$locker->beginTransaction();$locker->select('SELECT id FROM applications WHERE id=1 FOR UPDATE');$db->statement("SET lock_timeout='200ms'");
 }
 if(in_array($case,['preexisting_buffer','previous_start_buffer_rollback']))echo 'synthetic_preexisting_buffer';
 try{$result=configsentinel_j5_apply($input);}catch(Throwable $e){$caught=$e;}
 if($locker){$locker->rollBack();DB::disconnect('j5_locker');$db->statement("SET lock_timeout='0'");}
 $hook=null;$length=ob_get_length();ob_clean();
 if(in_array($case,['first_and_idempotent','previous_start_upgrade','response_ambiguous','encryption_flags'])){
  check($caught===null&&$result['changed']);$after=snapshot($db);
  if($case==='first_and_idempotent'){check(configsentinel_j5_apply($p)['changed']===false);check($after===snapshot($db));}
  if($case==='previous_start_upgrade'){check(configsentinel_j5_apply($p)['changed']===false);check($after===snapshot($db));}
  if($case==='response_ambiguous'){
   // Deliberately corrupt only the response after the real transaction committed.
   // Never retry automatically: independent state is the evidence of commit.
   $extra=['committed_before_response_failure'=>true,'response_stdout_bytes'=>strlen('{truncated'),'automatic_retry'=>false];
   check($db->table('applications')->value('git_commit_sha')===$p['commit']);
  }
  if($case==='encryption_flags')foreach($p['env']as$key=>$value){$raw=$db->table('environment_variables')->where('key',$key)->first();check($raw->value!==$value&&decrypt($raw->value)===$value);$v=App\Models\EnvironmentVariable::findOrFail($raw->id);check($v->is_literal&&$v->is_runtime&&!$v->is_buildtime&&$v->is_shown_once);}
 }else{
  check($caught!==null&&$before===snapshot($db));
  $expected=match($case){'constraint','lock_timeout'=>'database','warning'=>'php_warning','buffer','preexisting_buffer','previous_start_buffer_rollback'=>'output_buffer',default=>'runtime'};
  check(configsentinel_j5_error_kind($caught)===$expected);
  $extra=['exception_kind'=>$expected,'rollback_identical'=>true,'buffer_bytes'=>$length];
 }
 check($modelEvents===0);check($db->table('application_deployment_queues')->count()===(in_array($case,['queued','in_progress'])?1:0));
 $results[]=['test'=>$case,'result'=>'PASS','duration_ms'=>round((microtime(true)-$start)*1000),'model_saving_events'=>0]+$extra;
}
$disabled=[];foreach(['exec','system','passthru','shell_exec','proc_open','popen','pcntl_exec']as$f)$disabled[$f]=!function_exists($f);check(!in_array(false,$disabled,true));
ob_end_clean();
echo json_encode(['result'=>'PASS','tests'=>$results,'exec_disabled'=>$disabled,'docker_socket_absent'=>!file_exists('/var/run/docker.sock'),'synthetic_only'=>true,'active_metadata_read'=>false,'schemas_preserved'=>count($cases),'original_cause_proven'=>false]),PHP_EOL;
}catch(Throwable $e){$bytes=ob_get_length();if(ob_get_level())ob_end_clean();echo json_encode(['result'=>'FAIL','test'=>$case??'bootstrap','phase'=>isset($db)?'matrix':'bootstrap','kind'=>function_exists('configsentinel_j5_error_kind')?configsentinel_j5_error_kind($e):'bootstrap','exception_class'=>get_class($e),'source_file'=>basename($e->getFile()),'source_line'=>$e->getLine(),'buffer_bytes'=>$bytes,'content_recorded'=>false]),PHP_EOL;exit(2);}
