<?php
// Runs after API-upgrade fixture in isolated PostgreSQL.
$p=['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','direction'=>'forward'];$before=$snapshot();$injectCapacity=true;
DB::listen(function($q)use(&$injectCapacity){if($injectCapacity&&str_starts_with(strtolower($q->sql),'update "environment_variables"')){$injectCapacity=false;throw new RuntimeException('capacity_injected');}});
$failed=false;try{configsentinel_capacity_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='capacity_injected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_capacity_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue');$db->table('application_deployment_queues')->delete();
$a=configsentinel_capacity_upgrade($p);$after=$snapshot();$b=configsentinel_capacity_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence');
$p['direction']='rollback';$a=configsentinel_capacity_upgrade($p);$after=$snapshot();$b=configsentinel_capacity_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['forward'=>'PASS','failure_rollback'=>'PASS','queue_guard'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','scope'=>'synthetic PostgreSQL','schema_preserved'=>$schema]),PHP_EOL;
