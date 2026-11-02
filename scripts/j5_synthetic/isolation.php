<?php
// No Laravel bootstrap and no fixture writes before this gate.
$targets=json_decode(file_get_contents('/tmp/j5/negative-targets.json'),true,512,JSON_THROW_ON_ERROR);
$results=[];
foreach($targets as $index=>$target){
    $errno=0;$error='';$socket=@stream_socket_client('tcp://'.$target['ip'].':'.$target['port'],$errno,$error,0.25);
    $connected=is_resource($socket);if($connected)fclose($socket);
    $results[]=['target_class'=>$target['class'],'index'=>$index,'connected'=>$connected,'errno'=>$errno];
}
$socket=@stream_socket_client('tcp://'.getenv('DB_HOST').':5432',$errno,$error,2);
$positive=is_resource($socket);if($positive)fclose($socket);
$dnsBlocked=gethostbyname('example.com')==='example.com';
$pass=$positive && $dnsBlocked && !in_array(true,array_column($results,'connected'),true);
echo json_encode(['pass'=>$pass,'synthetic_db_reachable'=>$positive,'external_dns_blocked'=>$dnsBlocked,'negative_attempts'=>$results,'docker_socket_absent'=>!file_exists('/var/run/docker.sock')]),PHP_EOL;
exit($pass?0:3);
