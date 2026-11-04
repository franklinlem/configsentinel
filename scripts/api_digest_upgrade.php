<?php
// Narrow transaction for the reviewed API and migrator images; does not deploy.
function configsentinel_api_upgrade(array $p, bool $injectFailure=false): array {
    $mode=$p['mode']??''; $uuid=$p['uuid']??'';
    $allowed=($mode==='active' && $uuid==='oi6lvzwzomwtbbgzf5uzofuh') || ($mode==='isolated' && $uuid==='configsentinel-j5-isolated' && Illuminate\Support\Facades\DB::connection()->getDatabaseName()===':memory:');
    $old='ghcr.io/franklinlem/configsentinel-api@sha256:ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4';
    $new='ghcr.io/franklinlem/configsentinel-api@sha256:745d45e4dca060fc3fd2101feee8a9bc789c802e462ec0172c1def48a98a6830';
    $web='ghcr.io/franklinlem/configsentinel-web@sha256:e28a1b50c5242cf615e0531399daea63c93e7989370cdfa912c1243784f65bba';
    $db='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
    if (!$allowed || ($p['new_image']??null)!==$new || ($injectFailure && $mode!=='isolated')) throw new RuntimeException('scope_rejected');
    $build=static fn($api)=>"docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($x)=>explode('@',$x,2)[1],[$api,$web,$db]));
    $start='docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
    return Illuminate\Support\Facades\DB::transaction(function()use($uuid,$old,$new,$web,$db,$build,$start,$injectFailure){
        $a=App\Models\Application::where('uuid',$uuid)->lockForUpdate()->firstOrFail();
        if(App\Models\ApplicationDeploymentQueue::where('application_id',$a->id)->whereIn('status',['queued','in_progress'])->exists()) throw new RuntimeException('deployment_in_progress');
        $s=$a->settings;
        if(!$s || !$s->is_raw_compose_deployment_enabled || $s->is_build_server_enabled || $s->is_auto_deploy_enabled || $a->git_commit_sha!=='36baf66f4656f86d157cd070202323db9465c5f4' || $a->git_branch!=='plan/active-homologation-rc2' || $a->docker_compose_location!=='/deploy/compose.active-homologation.yml' || $a->docker_compose_custom_start_command!==$start) throw new RuntimeException('state_drift');
        $values=[];
        foreach(['CONFIGSENTINEL_API_IMAGE','CONFIGSENTINEL_MIGRATION_IMAGE','CONFIGSENTINEL_WEB_IMAGE','CONFIGSENTINEL_DB_IMAGE','POSTGRES_PASSWORD','RUNTIME_DB_PASSWORD','MIGRATOR_DB_PASSWORD'] as $key){
            if($a->environment_variables()->where('key',$key)->count()!==1) throw new RuntimeException('state_drift');
            $v=$a->environment_variables()->where('key',$key)->firstOrFail();
            if(!$v->value || !$v->is_literal || !$v->is_runtime || $v->is_buildtime || !$v->is_shown_once) throw new RuntimeException('state_drift');
            $values[$key]=$v;
        }
        if($values['CONFIGSENTINEL_WEB_IMAGE']->value!==$web || $values['CONFIGSENTINEL_DB_IMAGE']->value!==$db) throw new RuntimeException('state_drift');
        $api=$values['CONFIGSENTINEL_API_IMAGE'];$migrate=$values['CONFIGSENTINEL_MIGRATION_IMAGE'];
        if($api->value===$new && $migrate->value===$new && $a->docker_compose_custom_build_command===$build($new)) return ['changed'=>false];
        if($api->value!==$old || $migrate->value!==$old || $a->docker_compose_custom_build_command!==$build($old)) throw new RuntimeException('state_drift');
        $api->value=$new;$api->saveQuietly();if($injectFailure) throw new RuntimeException('test_failure');
        $migrate->value=$new;$migrate->saveQuietly();$a->docker_compose_custom_build_command=$build($new);$a->saveQuietly();
        $api->refresh();$migrate->refresh();$a->refresh();
        if($api->value!==$new || $migrate->value!==$new || $a->docker_compose_custom_build_command!==$build($new)) throw new RuntimeException('transaction_failed');
        return ['changed'=>true];
    });
}
