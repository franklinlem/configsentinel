<?php
// Runs after the web-upgrade fixture inside Coolify's in-memory SQLite clone.
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:745d45e4dca060fc3fd2101feee8a9bc789c802e462ec0172c1def48a98a6830'];
$snapshot=static fn()=>json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$before=$snapshot();$failed=false;
try{configsentinel_api_upgrade($p,true);}catch(RuntimeException $e){$failed=$e->getMessage()==='test_failure';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback');
$bad=$p;$bad['new_image']='bad';$failed=false;try{configsentinel_api_upgrade($bad);}catch(RuntimeException $e){$failed=$e->getMessage()==='scope_rejected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('digest');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;
try{configsentinel_api_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue');$db->table('application_deployment_queues')->delete();
$first=configsentinel_api_upgrade($p);$after=$snapshot();$second=configsentinel_api_upgrade($p);
if(!$first['changed']||$second['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence');
echo json_encode(['rollback'=>'PASS','invalid_digest'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','scope'=>'synthetic sqlite in memory']),PHP_EOL;
