<?php
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:6f9f7f358f6fdde668e36db31d1e1bbad9a77bffdfc89518917ba358ae975395'];
$snapshot=static fn()=>json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$before=$snapshot();$failed=false;
try{configsentinel_heartbeat_upgrade($p,true);}catch(RuntimeException $e){$failed=$e->getMessage()==='test_failure';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback');
$bad=$p;$bad['new_image']='bad';$failed=false;try{configsentinel_heartbeat_upgrade($bad);}catch(RuntimeException $e){$failed=$e->getMessage()==='scope_rejected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('digest');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;
try{configsentinel_heartbeat_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue');$db->table('application_deployment_queues')->delete();
$first=configsentinel_heartbeat_upgrade($p);$after=$snapshot();$second=configsentinel_heartbeat_upgrade($p);
if(!$first['changed']||$second['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence');
$p['direction']='rollback';$p['new_image']='ghcr.io/franklinlem/configsentinel-api@sha256:89e789ffb0eba2b2567d741cddf06648ffb1837604bcf4e28d75a4db65601124';
$first=configsentinel_heartbeat_upgrade($p);$after=$snapshot();$second=configsentinel_heartbeat_upgrade($p);
if(!$first['changed']||$second['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['rollback'=>'PASS','invalid_digest'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','scope'=>'synthetic sqlite in memory']),PHP_EOL;
