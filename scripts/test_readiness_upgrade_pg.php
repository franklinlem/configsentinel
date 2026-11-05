<?php
$p=['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:89e789ffb0eba2b2567d741cddf06648ffb1837604bcf4e28d75a4db65601124'];
$before=$snapshot();$readyInject=true;DB::listen(function($q)use(&$readyInject){if($readyInject&&str_starts_with(strtolower($q->sql),'update "environment_variables"')){$readyInject=false;throw new RuntimeException('ready_injected');}});
$failed=false;try{configsentinel_readiness_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='ready_injected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback_failed');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_readiness_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue_guard_failed');$db->table('application_deployment_queues')->delete();
$a=configsentinel_readiness_upgrade($p);$after=$snapshot();$b=configsentinel_readiness_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence_failed');
$p['direction']='rollback';$p['new_image']='ghcr.io/franklinlem/configsentinel-api@sha256:f8fdc1ffe8b4f8cf1a1480a6d3d69d95e332cf90f2c1589c99459046f158c39f';
$a=configsentinel_readiness_upgrade($p);$after=$snapshot();$b=configsentinel_readiness_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['scope'=>'synthetic PostgreSQL only','rollback'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','schema_preserved'=>$schema,'credentials_disclosed'=>false]),PHP_EOL;
