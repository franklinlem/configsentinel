<?php
// Scoped transaction for the heartbeat API and its reviewed rollback image.
function configsentinel_heartbeat_upgrade(array $p, bool $injectFailure=false): array {
    $mode=$p['mode']??''; $uuid=$p['uuid']??'';
    $allowed=($mode==='active' && $uuid==='oi6lvzwzomwtbbgzf5uzofuh') || ($mode==='isolated' && $uuid==='configsentinel-j5-isolated' && Illuminate\Support\Facades\DB::connection()->getDatabaseName()===':memory:');
    $old='ghcr.io/franklinlem/configsentinel-api@sha256:89e789ffb0eba2b2567d741cddf06648ffb1837604bcf4e28d75a4db65601124';
    $new='ghcr.io/franklinlem/configsentinel-api@sha256:6f9f7f358f6fdde668e36db31d1e1bbad9a77bffdfc89518917ba358ae975395';
    $web='ghcr.io/franklinlem/configsentinel-web@sha256:64c4e53b1784d01cef1e35c5c1d34e5aa05174c64d2b01903e93b8e7fa95c44b';
    $db='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
    $direction=$p['direction']??'forward';
    if (!in_array($direction,['forward','rollback'],true)) throw new RuntimeException('scope_rejected');
    $source=$direction==='forward'?$old:$new; $target=$direction==='forward'?$new:$old;
    if (!$allowed || ($p['new_image']??null)!==$target || ($injectFailure && $mode!=='isolated')) throw new RuntimeException('scope_rejected');
    $build=static fn($api)=>"docker image inspect --format '{{.Id}}' ".implode(' ',array_map(static fn($x)=>explode('@',$x,2)[1],[$api,$web,$db]));
    $start='docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
    return Illuminate\Support\Facades\DB::transaction(function()use($uuid,$source,$target,$web,$db,$build,$start,$injectFailure){
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
        if($api->value===$target && $migrate->value===$target && $a->docker_compose_custom_build_command===$build($target)) return ['changed'=>false];
        if($api->value!==$source || $migrate->value!==$source || $a->docker_compose_custom_build_command!==$build($source)) throw new RuntimeException('state_drift');
        $api->value=$target;$api->saveQuietly();if($injectFailure) throw new RuntimeException('test_failure');
        $migrate->value=$target;$migrate->saveQuietly();$a->docker_compose_custom_build_command=$build($target);$a->saveQuietly();
        $api->refresh();$migrate->refresh();$a->refresh();
        if($api->value!==$target || $migrate->value!==$target || $a->docker_compose_custom_build_command!==$build($target)) throw new RuntimeException('transaction_failed');
        return ['changed'=>true];
    });
}
