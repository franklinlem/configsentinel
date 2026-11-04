<?php
// Runs after the web-upgrade fixture in isolated PostgreSQL.
$p=['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','new_image'=>'ghcr.io/franklinlem/configsentinel-api@sha256:745d45e4dca060fc3fd2101feee8a9bc789c802e462ec0172c1def48a98a6830'];
$before=$snapshot();$apiInject=true;DB::listen(function($q)use(&$apiInject){if($apiInject&&str_starts_with(strtolower($q->sql),'update "environment_variables"')){$apiInject=false;throw new RuntimeException('api_injected');}});
$failed=false;try{configsentinel_api_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='api_injected';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('api_rollback_failed');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$failed=false;try{configsentinel_api_upgrade($p);}catch(RuntimeException $e){$failed=$e->getMessage()==='deployment_in_progress';}
if(!$failed||$snapshot()!==$before)throw new RuntimeException('api_queue_guard_failed');$db->table('application_deployment_queues')->delete();
$a=configsentinel_api_upgrade($p);$after=$snapshot();$b=configsentinel_api_upgrade($p);
if(!$a['changed']||$b['changed']||$snapshot()!==$after)throw new RuntimeException('api_idempotence_failed');
echo json_encode(['scope'=>'synthetic PostgreSQL only','rollback'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','schema_preserved'=>$schema,'credentials_disclosed'=>false]),PHP_EOL;
