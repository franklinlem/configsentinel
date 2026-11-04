<?php
// Loaded after the original helper and Coolify bootstrap in an in-memory SQLite probe.
ob_start(); require '/tmp/configsentinel-probe.php'; ob_end_clean();
require '/tmp/configsentinel-web-upgrade.php';
use Illuminate\Support\Facades\DB;
$db=DB::connection();
if ($db->getDatabaseName() !== ':memory:') throw new RuntimeException('scope');
$db->statement('CREATE TABLE application_deployment_queues (id integer primary key, application_id integer, status text)');
$p=['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','new_image'=>'ghcr.io/franklinlem/configsentinel-web@sha256:e28a1b50c5242cf615e0531399daea63c93e7989370cdfa912c1243784f65bba'];
$snapshot=static fn()=>json_encode([$db->table('applications')->get(),$db->table('environment_variables')->get()]);
$before=$snapshot();$failed=false;
try {configsentinel_web_upgrade($p,true);} catch(RuntimeException $e) {$failed=$e->getMessage()==='test_failure';}
if (!$failed || $snapshot()!==$before) throw new RuntimeException('rollback');
$bad=$p;$bad['new_image']='sha256:invalid';$rejected=false;
try {configsentinel_web_upgrade($bad);} catch(RuntimeException $e) {$rejected=$e->getMessage()==='scope_rejected';}
if (!$rejected || $snapshot()!==$before) throw new RuntimeException('invalid_digest');
$db->table('application_deployment_queues')->insert(['id'=>1,'application_id'=>1,'status'=>'queued']);$rejected=false;
try {configsentinel_web_upgrade($p);} catch(RuntimeException $e) {$rejected=$e->getMessage()==='deployment_in_progress';}
if (!$rejected || $snapshot()!==$before) throw new RuntimeException('queue_guard');
$db->table('application_deployment_queues')->delete();
$first=configsentinel_web_upgrade($p);$after=$snapshot();$second=configsentinel_web_upgrade($p);
if (!$first['changed'] || $second['changed'] || $snapshot()!==$after) throw new RuntimeException('idempotence');
echo json_encode(['rollback'=>'PASS','invalid_digest'=>'PASS','queue_guard'=>'PASS','update'=>'PASS','idempotence'=>'PASS','scope'=>'synthetic sqlite in memory','no_values_logged'=>true]),PHP_EOL;
