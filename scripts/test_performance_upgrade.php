<?php
// Runs after schema-2 fixture inside Coolify's in-memory SQLite clone.
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:f8fdc1ffe8b4f8cf1a1480a6d3d69d95e332cf90f2c1589c99459046f158c39f'];
$snapshot=static fn()=>json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);$before=$snapshot();$failed=false;
try{configsentinel_performance_upgrade($p,true);}catch(RuntimeException $e){$failed=$e->getMessage()==='test_failure';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('rollback');
$bad=$p;$bad['new_image']='bad';$failed=false;try{configsentinel_performance_upgrade($bad);}catch(RuntimeException $e){$failed=$e->getMessage()==='scope_rejected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('digest');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;
try{configsentinel_performance_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('queue');$db->table('application_deployment_queues')->delete();
$first=configsentinel_performance_upgrade($p);$after=$snapshot();$second=configsentinel_performance_upgrade($p);
if(!$first['changed']||$second['changed']||$snapshot()!==$after)throw new RuntimeException('idempotence');
$p['direction']='rollback';$p['new_image']='ghcr.io/franklinlem/configsentinel-api@sha256:3ffaecb7c7f3db5883c1b56a661e6ce7629288cb8eeaf87722bdb3cf4f13fedb';
$first=configsentinel_performance_upgrade($p);$after=$snapshot();$second=configsentinel_performance_upgrade($p);
if(!$first['changed']||$second['changed']||$snapshot()!==$after)throw new RuntimeException('fallback');
echo json_encode(['rollback'=>'PASS','invalid_digest'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','fallback'=>'PASS','scope'=>'synthetic sqlite in memory']),PHP_EOL;
