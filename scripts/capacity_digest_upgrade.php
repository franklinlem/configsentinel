<?php
// Schema-2 promotion/rollback transaction. Caller verifies attestations and
// backup gates. This changes only reviewed image references; never deploys.
function configsentinel_capacity_upgrade(array $p, bool $injectFailure=false): array {
    $uuid=$p['uuid']??'';$mode=$p['mode']??'';$direction=$p['direction']??'';
    $allowed=($mode==='active' && $uuid==='oi6lvzwzomwtbbgzf5uzofuh') || ($mode==='isolated' && $uuid==='configsentinel-j5-isolated' && Illuminate\Support\Facades\DB::connection()->getDatabaseName()===':memory:');
    if(!$allowed || !in_array($direction,['forward','rollback'],true) || ($injectFailure && $mode!=='isolated')) throw new RuntimeException('scope_rejected');
    $oldApi='ghcr.io/franklinlem/configsentinel-api@sha256:745d45e4dca060fc3fd2101feee8a9bc789c802e462ec0172c1def48a98a6830';
    $newApi='ghcr.io/franklinlem/configsentinel-api@sha256:3ffaecb7c7f3db5883c1b56a661e6ce7629288cb8eeaf87722bdb3cf4f13fedb';
    $fallback='ghcr.io/franklinlem/configsentinel-api@sha256:c51e92c3cdb4b0ec7f64f79423a1684f4905cebf8753ae0670b21abbf95b1581';
    $oldWeb='ghcr.io/franklinlem/configsentinel-web@sha256:e28a1b50c5242cf615e0531399daea63c93e7989370cdfa912c1243784f65bba';
    $newWeb='ghcr.io/franklinlem/configsentinel-web@sha256:64c4e53b1784d01cef1e35c5c1d34e5aa05174c64d2b01903e93b8e7fa95c44b';
    $db='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
    $build=static fn($api,$web)=>"docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($x)=>explode('@',$x,2)[1],[$api,$web,$db]));
    $start='docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
    return Illuminate\Support\Facades\DB::transaction(function()use($uuid,$direction,$oldApi,$newApi,$fallback,$oldWeb,$newWeb,$db,$build,$start,$injectFailure){
        $a=App\Models\Application::where('uuid',$uuid)->lockForUpdate()->firstOrFail();
        if(App\Models\ApplicationDeploymentQueue::where('application_id',$a->id)->whereIn('status',['queued','in_progress'])->exists())throw new RuntimeException('deployment_in_progress');
        $s=$a->settings;
        if(!$s || !$s->is_raw_compose_deployment_enabled || $s->is_build_server_enabled || $s->is_auto_deploy_enabled || $a->git_commit_sha!=='36baf66f4656f86d157cd070202323db9465c5f4' || $a->git_branch!=='plan/active-homologation-rc2' || $a->docker_compose_location!=='/deploy/compose.active-homologation.yml' || $a->docker_compose_custom_start_command!==$start)throw new RuntimeException('state_drift');
        $v=[];
        foreach(['CONFIGSENTINEL_API_IMAGE','CONFIGSENTINEL_MIGRATION_IMAGE','CONFIGSENTINEL_WEB_IMAGE','CONFIGSENTINEL_DB_IMAGE','POSTGRES_PASSWORD','RUNTIME_DB_PASSWORD','MIGRATOR_DB_PASSWORD'] as $key){
            if($a->environment_variables()->where('key',$key)->count()!==1)throw new RuntimeException('state_drift');
            $row=$a->environment_variables()->where('key',$key)->firstOrFail();
            if(!$row->value || !$row->is_literal || !$row->is_runtime || $row->is_buildtime || !$row->is_shown_once)throw new RuntimeException('state_drift');$v[$key]=$row;
        }
        if($v['CONFIGSENTINEL_DB_IMAGE']->value!==$db)throw new RuntimeException('state_drift');
        $api=$v['CONFIGSENTINEL_API_IMAGE'];$mig=$v['CONFIGSENTINEL_MIGRATION_IMAGE'];$web=$v['CONFIGSENTINEL_WEB_IMAGE'];
        $targetApi=$direction==='forward'?$newApi:$fallback;$targetWeb=$newWeb;
        if($api->value===$targetApi && $mig->value===$targetApi && $web->value===$targetWeb && $a->docker_compose_custom_build_command===$build($targetApi,$targetWeb))return ['changed'=>false];
        $sourceApi=$direction==='forward'?$oldApi:$newApi;$sourceWeb=$direction==='forward'?$oldWeb:$newWeb;
        if($api->value!==$sourceApi || $mig->value!==$sourceApi || $web->value!==$sourceWeb || $a->docker_compose_custom_build_command!==$build($sourceApi,$sourceWeb))throw new RuntimeException('state_drift');
        $api->value=$targetApi;$api->saveQuietly();if($injectFailure)throw new RuntimeException('test_failure');
        $mig->value=$targetApi;$mig->saveQuietly();$web->value=$targetWeb;$web->saveQuietly();$a->docker_compose_custom_build_command=$build($targetApi,$targetWeb);$a->saveQuietly();
        $api->refresh();$mig->refresh();$web->refresh();$a->refresh();
        if($api->value!==$targetApi || $mig->value!==$targetApi || $web->value!==$targetWeb || $a->docker_compose_custom_build_command!==$build($targetApi,$targetWeb))throw new RuntimeException('transaction_failed');
        return ['changed'=>true];
    });
}
