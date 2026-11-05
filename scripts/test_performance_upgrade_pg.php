<?php
// Runs after schema-2 fixture in isolated PostgreSQL.
$p=['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:f8fdc1ffe8b4f8cf1a1480a6d3d69d95e332cf90f2c1589c99459046f158c39f'];
$before=$snapshot();$perfInject=true;DB::listen(function($q)use(&$perfInject){if($perfInject&&str_starts_with(strtolower($q->sql),'update "environment_variables"')){$perfInject=false;throw new RuntimeException('perf_injected');}});
$failed=false;try{configsentinel_performance_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='perf_injected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('api_rollback_failed');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_performance_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('api_queue_guard_failed');$db->table('application_deployment_queues')->delete();
$a=configsentinel_performance_upgrade($p);$after=$snapshot();$b=configsentinel_performance_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('api_idempotence_failed');
$p['direction']='rollback';$p['new_image']='ghcr.io/franklinlem/configsentinel-api@sha256:3ffaecb7c7f3db5883c1b56a661e6ce7629288cb8eeaf87722bdb3cf4f13fedb';
$a=configsentinel_performance_upgrade($p);$after=$snapshot();$b=configsentinel_performance_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['scope'=>'synthetic PostgreSQL only','rollback'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','schema_preserved'=>$schema,'credentials_disclosed'=>false]),PHP_EOL;
