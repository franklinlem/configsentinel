<?php
// Controlled web-only metadata upgrade. No deploy; callers must validate the
// signed manifest and installed image before invoking this transaction.
function configsentinel_web_upgrade(array $p, bool $injectFailure = false): array {
    $uuid = $p['uuid'] ?? '';
    $mode = $p['mode'] ?? '';
    $allowed = ($mode === 'active' && $uuid === 'oi6lvzwzomwtbbgzf5uzofuh') ||
        ($mode === 'isolated' && $uuid === 'configsentinel-j5-isolated' && Illuminate\Support\Facades\DB::connection()->getDatabaseName() === ':memory:');
    $old = 'ghcr.io/franklinlem/configsentinel-web@sha256:e7604db734053aed8834c0c4025001fcafab1026e50bca1f8b02aee1fb6cd8d3';
    $new = 'ghcr.io/franklinlem/configsentinel-web@sha256:e28a1b50c5242cf615e0531399daea63c93e7989370cdfa912c1243784f65bba';
    $api = 'ghcr.io/franklinlem/configsentinel-api@sha256:ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4';
    $db = 'ghcr.io/franklinlem/configsentinel-db@sha256:ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447';
    if (!$allowed || ($p['new_image'] ?? null) !== $new || ($injectFailure && $mode !== 'isolated')) throw new RuntimeException('scope_rejected');
    $build = static fn($web) => "docker image inspect --format '{{.Id}}' ".implode(' ', array_map(static fn($x) => explode('@', $x, 2)[1], [$api, $web, $db]));
    $start = 'docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build';
    return Illuminate\Support\Facades\DB::transaction(function () use ($uuid, $old, $new, $api, $db, $build, $start, $injectFailure) {
        $a = App\Models\Application::where('uuid', $uuid)->lockForUpdate()->firstOrFail();
        if (App\Models\ApplicationDeploymentQueue::where('application_id', $a->id)->whereIn('status', ['queued','in_progress'])->exists()) throw new RuntimeException('deployment_in_progress');
        $s = $a->settings;
        if (!$s || !$s->is_raw_compose_deployment_enabled || $s->is_build_server_enabled || $s->is_auto_deploy_enabled ||
            $a->git_commit_sha !== '36baf66f4656f86d157cd070202323db9465c5f4' || $a->git_branch !== 'plan/active-homologation-rc2' ||
            $a->docker_compose_location !== '/deploy/compose.active-homologation.yml' || $a->docker_compose_custom_start_command !== $start) throw new RuntimeException('state_drift');
        $expected = ['CONFIGSENTINEL_API_IMAGE'=>$api, 'CONFIGSENTINEL_MIGRATION_IMAGE'=>$api, 'CONFIGSENTINEL_DB_IMAGE'=>$db];
        foreach ($expected as $key=>$value) {
            if ($a->environment_variables()->where('key',$key)->count() !== 1) throw new RuntimeException('state_drift');
            $v=$a->environment_variables()->where('key',$key)->firstOrFail();
            if ($v->value !== $value || !$v->is_literal || !$v->is_runtime || $v->is_buildtime || !$v->is_shown_once) throw new RuntimeException('state_drift');
        }
        foreach (['POSTGRES_PASSWORD','RUNTIME_DB_PASSWORD','MIGRATOR_DB_PASSWORD'] as $key) {
            if ($a->environment_variables()->where('key',$key)->count() !== 1) throw new RuntimeException('state_drift');
            $v=$a->environment_variables()->where('key',$key)->firstOrFail();
            if (!$v->value || !$v->is_literal || !$v->is_runtime || $v->is_buildtime || !$v->is_shown_once) throw new RuntimeException('state_drift');
        }
        if ($a->environment_variables()->where('key','CONFIGSENTINEL_WEB_IMAGE')->count() !== 1) throw new RuntimeException('state_drift');
        $v=$a->environment_variables()->where('key','CONFIGSENTINEL_WEB_IMAGE')->firstOrFail();
        if (!$v->is_literal || !$v->is_runtime || $v->is_buildtime || !$v->is_shown_once) throw new RuntimeException('state_drift');
        if ($v->value === $new && $a->docker_compose_custom_build_command === $build($new)) return ['changed'=>false];
        if ($v->value !== $old || $a->docker_compose_custom_build_command !== $build($old)) throw new RuntimeException('state_drift');
        $v->value=$new; $v->saveQuietly();
        if ($injectFailure) throw new RuntimeException('test_failure');
        $a->docker_compose_custom_build_command=$build($new); $a->saveQuietly();
        $a->refresh(); $v->refresh();
        if ($v->value !== $new || $a->docker_compose_custom_build_command !== $build($new)) throw new RuntimeException('transaction_failed');
        return ['changed'=>true];
    });
}
