<?php
// Test copy only. Exact PHP token transformation, never edits operational source.
$source=file_get_contents($argv[1]);
$oldUuid="'oi6lvzwzomwtbbgzf5uzofuh'";
$newUuid="'configsentinel-j5-isolated'";
$oldStart="'docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build'";
$newStart="'docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name configsentinel-j5-isolated up -d --pull never --no-build'";
$oldPrevious="'docker compose --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build'";
$newPrevious="'docker compose --project-name configsentinel-j5-isolated up -d --pull never --no-build'";
$counts=['uuid'=>0,'start'=>0,'previous_start'=>0];$output='';
foreach(token_get_all($source,TOKEN_PARSE) as $token){
    if(!is_array($token)){$output.=$token;continue;}
    [$type,$text]=$token;
    if($type===T_CONSTANT_ENCAPSED_STRING && $text===$oldUuid){$text=$newUuid;$counts['uuid']++;}
    if($type===T_CONSTANT_ENCAPSED_STRING && $text===$oldStart){$text=$newStart;$counts['start']++;}
    if($type===T_CONSTANT_ENCAPSED_STRING && $text===$oldPrevious){$text=$newPrevious;$counts['previous_start']++;}
    $output.=$text;
}
if($counts!==['uuid'=>1,'start'=>1,'previous_start'=>1])throw new RuntimeException('unexpected_guard_source');
if(file_exists($argv[2]) && file_get_contents($argv[2])!==$output)throw new RuntimeException('test_copy_drift');
if(!file_exists($argv[2]))file_put_contents($argv[2],$output,LOCK_EX);
echo json_encode(['guard_literals_changed'=>$counts,'original_sha256'=>hash('sha256',$source),'copy_sha256'=>hash('sha256',$output)]),PHP_EOL;
