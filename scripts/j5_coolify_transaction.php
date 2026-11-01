<?php
// Loaded by a controlled caller after Laravel bootstrap. Does not deploy or enqueue.
// Values enter as structured data and are never included in returned results/errors.
function configsentinel_j5_apply(array $p, bool $injectFailure = false): array {
    foreach (['mode','uuid','commit','compose','branch','custom_build','custom_start','env'] as $field) if (!array_key_exists($field,$p)) throw new RuntimeException('invalid_input');
    if (!is_array($p['env']) || !is_string($p['mode']) || !is_string($p['uuid'])) throw new RuntimeException('invalid_input');
    $keys = ['POSTGRES_PASSWORD','RUNTIME_DB_PASSWORD','MIGRATOR_DB_PASSWORD','CONFIGSENTINEL_API_IMAGE','CONFIGSENTINEL_MIGRATION_IMAGE','CONFIGSENTINEL_WEB_IMAGE','CONFIGSENTINEL_DB_IMAGE'];
    $allowedTarget = $p['mode'] === 'isolated' && Illuminate\Support\Facades\DB::connection()->getDatabaseName() === ':memory:' && $p['uuid'] === 'configsentinel-j5-isolated';
    $allowedTarget = $allowedTarget || ($p['mode'] === 'active' && $p['uuid'] === 'oi6lvzwzomwtbbgzf5uzofuh');
    if (! $allowedTarget || count($p['env']) !== count($keys) || array_diff($keys,array_keys($p['env'])) || array_diff(array_keys($p['env']),$keys)) throw new RuntimeException('scope_rejected');
    if ($p['commit'] !== '36baf66f4656f86d157cd070202323db9465c5f4' || $p['compose'] !== '/deploy/compose.active-homologation.yml' || $p['branch'] !== 'plan/active-homologation-rc2') throw new RuntimeException('scope_rejected');
    $api='ghcr.io/franklinlem/configsentinel-api@sha256:ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4';
    $fallback='ghcr.io/franklinlem/configsentinel-api@sha256:cacace0b74ddb9bdef72109436035c59305e4c6bb02c063fe0788ce069cffc66';
    $web='ghcr.io/franklinlem/configsentinel-web@sha256:e7604db734053aed8834c0c4025001fcafab1026e50bca1f8b02aee1fb6cd8d3';
    $db='ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
    if ($p['env']['CONFIGSENTINEL_API_IMAGE'] !== $api || $p['env']['CONFIGSENTINEL_MIGRATION_IMAGE'] !== $api || $p['env']['CONFIGSENTINEL_WEB_IMAGE'] !== $web || $p['env']['CONFIGSENTINEL_DB_IMAGE'] !== $db) throw new RuntimeException('invalid_input');
    $build="docker image inspect --format '{{.Id}}' ".implode(' ',[$api,$fallback,$web,$db]);
    $start='docker compose --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
    if ($p['custom_build'] !== $build || $p['custom_start'] !== $start) throw new RuntimeException('scope_rejected');
    if ($injectFailure && $p['mode'] !== 'isolated') throw new RuntimeException('scope_rejected');
    foreach ($p['env'] as $v) if (!is_string($v) || $v === '' || trim($v) !== $v || str_contains($v,"\n") || str_contains($v,"\r")) throw new RuntimeException('invalid_input');
    foreach (['RUNTIME_DB_PASSWORD','MIGRATOR_DB_PASSWORD'] as $key) if (!preg_match('/^[a-f0-9]{64}$/',$p['env'][$key])) throw new RuntimeException('invalid_input');
    if ($p['env']['RUNTIME_DB_PASSWORD'] === $p['env']['MIGRATOR_DB_PASSWORD']) throw new RuntimeException('invalid_input');
    return Illuminate\Support\Facades\DB::transaction(function () use ($p, $injectFailure) {
        $a=App\Models\Application::where('uuid',$p['uuid'])->lockForUpdate()->firstOrFail();
        if ($p['mode'] === 'active' && App\Models\ApplicationDeploymentQueue::where('application_id',$a->id)->whereIn('status',['queued','in_progress'])->exists()) throw new RuntimeException('state_drift');
        $settings=$a->settings;
        if (!$settings || !$settings->is_raw_compose_deployment_enabled || $settings->is_build_server_enabled || $settings->is_auto_deploy_enabled) throw new RuntimeException('state_drift');
        $old = $a->git_commit_sha === '5819b7fce93c10cceabbe59fde5fac4f647b707c' && $a->git_branch === 'main' && $a->docker_compose_location === '/deploy/compose.coolify.yml';
        $desired = $a->git_commit_sha === $p['commit'] && $a->git_branch === $p['branch'] && $a->docker_compose_location === $p['compose'] && $a->docker_compose_custom_build_command === $p['custom_build'] && $a->docker_compose_custom_start_command === $p['custom_start'];
        if (!$old && !$desired) throw new RuntimeException('state_drift');
        foreach ($p['env'] as $key=>$value) {
            if ($a->environment_variables()->where('key',$key)->count() > 1) throw new RuntimeException('state_drift');
            $v=$a->environment_variables()->where('key',$key)->first();
            if ($desired && (!$v || $v->value !== $value || !$v->is_literal || !$v->is_runtime || $v->is_buildtime || !$v->is_shown_once)) throw new RuntimeException('state_drift');
        }
        if ($desired) {
            if (ob_get_level() && ob_get_length() !== 0) throw new RuntimeException('internal_error');
            return ['uuid'=>$p['uuid'],'commit'=>$p['commit'],'changed'=>false,'protected_envs_verified'=>count($p['env'])];
        }
        // Protect the existing database password from accidental rotation.
        $current=$a->environment_variables()->where('key','POSTGRES_PASSWORD')->firstOrFail();
        if ($current->value !== $p['env']['POSTGRES_PASSWORD']) throw new RuntimeException('state_drift');
        foreach ($p['env'] as $key=>$value) {
            $v=$a->environment_variables()->where('key',$key)->first();
            if (!$v) {$v=new App\Models\EnvironmentVariable();$v->uuid=(string) Illuminate\Support\Str::uuid();$v->resourceable_type=App\Models\Application::class;$v->resourceable_id=$a->id;$v->key=$key;$v->is_preview=false;}
            $v->value=$value;$v->is_literal=true;$v->is_runtime=true;$v->is_buildtime=false;$v->is_multiline=false;$v->is_shown_once=true;$v->is_shared=false;$v->version=config('constants.coolify.version');$v->saveQuietly();
        }
        if ($injectFailure) throw new RuntimeException('test_failure');
        $a->git_branch=$p['branch'];$a->git_commit_sha=$p['commit'];$a->docker_compose_location=$p['compose'];$a->docker_compose_custom_build_command=$p['custom_build'];$a->docker_compose_custom_start_command=$p['custom_start'];$a->saveQuietly();
        $a->refresh();foreach($p['env'] as $key=>$value){$v=$a->environment_variables()->where('key',$key)->firstOrFail();if($v->value!==$value||!$v->is_literal||!$v->is_runtime||$v->is_buildtime||!$v->is_shown_once)throw new RuntimeException('transaction_failed');}
        if (ob_get_level() && ob_get_length() !== 0) throw new RuntimeException('internal_error');
        return ['uuid'=>$p['uuid'],'commit'=>$p['commit'],'changed'=>true,'protected_envs_verified'=>count($p['env'])];
    });
}
