<?php
// Runs after the API-upgrade fixture in SQLite memory.
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','direction'=>'forward'];$before=$snapshot();$failed=false;
try{configsentinel_capacity_upgrade($p,true);}catch(RuntimeException $e){$failed=$e->getMessage()==='test_failure';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_capacity_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue');$db->table('application_deployment_queues')->delete();
$a=configsentinel_capacity_upgrade($p);$after=$snapshot();$b=configsentinel_capacity_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence');
$p['direction']='rollback';$a=configsentinel_capacity_upgrade($p);$after=$snapshot();$b=configsentinel_capacity_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['forward'=>'PASS','failure_rollback'=>'PASS','queue_guard'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','scope'=>'synthetic sqlite']),PHP_EOL;
