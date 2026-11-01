<?php
// Run inside installed Coolify. Read-only DB transaction; parser SSH is intercepted.
namespace App\Models {
    function instant_remote_process($commands, $server, ...$options) {
        if (count($commands) !== 0) {
            throw new \RuntimeException('Probe forbids parser remote commands');
        }
        return null;
    }
}
namespace {
    require '/var/www/html/vendor/autoload.php';
    $app = require '/var/www/html/bootstrap/app.php';
    $app->make(\Illuminate\Contracts\Console\Kernel::class)->bootstrap();
    $input = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
    if (! preg_match('/^configsentinel-prechecks-[a-f0-9]{10}$/', $input['project'])) {
        throw new \RuntimeException('Isolated project name required');
    }
    if ($input['workdir'] !== '/home/franklin/.config/'.$input['project'] || count($input['images']) !== 4) throw new \RuntimeException('Unexpected probe scope');
    foreach ($input['images'] as $image) {
        if (!preg_match('~^ghcr\.io/franklinlem/configsentinel-(api|web|db)@sha256:[a-f0-9]{64}$~', $image)) throw new \RuntimeException('Unexpected image reference');
    }
    \Illuminate\Support\Facades\DB::beginTransaction();
    \Illuminate\Support\Facades\DB::statement('SET TRANSACTION READ ONLY');
    try {
        $active = \App\Models\Application::where('uuid', 'oi6lvzwzomwtbbgzf5uzofuh')->firstOrFail();
        $before = $active->getAttributes();
        if (! $active->settings->is_raw_compose_deployment_enabled || $active->settings->is_build_server_enabled) {
            throw new \RuntimeException('Unexpected active deployment mode');
        }
        $probe = clone $active;
        $probe->uuid = $input['project'];
        $probe->docker_compose_raw = $input['compose'];
        // Exact installed method; its only remote-call site is intercepted above.
        $probe->oldRawParser();
        $parsed = \Symfony\Component\Yaml\Yaml::parse($probe->docker_compose_raw);
        $workdir = $input['workdir'];
        $command = 'docker compose --project-directory '.$workdir.' --project-name '.$input['project'].' up -d --pull never --no-build';
        $injected = injectDockerComposeFlags($command, $workdir.'/compose.yaml', $workdir.'/.env');
        $jobClass = new \ReflectionClass(\App\Jobs\ApplicationDeploymentJob::class);
        $job = $jobClass->newInstanceWithoutConstructor();
        $validate = $jobClass->getMethod('validateShellSafeCommand');
        $build = "docker image inspect --format '{{.Id}}' ".implode(' ', $input['images']);
        $validate->invoke($job, $build, 'docker_compose_custom_build_command');
        $validate->invoke($job, $command, 'docker_compose_custom_start_command');
        $redirectionRejected = false;
        try { $validate->invoke($job, 'docker image inspect example >/dev/null', 'probe'); }
        catch (\RuntimeException $e) { $redirectionRejected = true; }
        if (! $redirectionRejected) throw new \RuntimeException('Unexpected command policy');
        $queue = new class extends \App\Models\ApplicationDeploymentQueue {
            public array $probeMessages = [];
            public function addLogEntry(string $message, string $type = 'stdout', bool $hidden = false, ?string $command = null, int $batch = 1): void {
                $this->probeMessages[] = $message;
            }
        };
        foreach (['docker_compose_custom_build_command' => $build, 'use_build_server' => false, 'application_deployment_queue' => $queue] as $key => $value) {
            $jobClass->getProperty($key)->setValue($job, $value);
        }
        $jobClass->getMethod('pull_docker_compose_images')->invoke($job);
        if (count($queue->probeMessages) !== 1 || !str_contains($queue->probeMessages[0], 'Skipping the image pull')) throw new \RuntimeException('Automatic pull was not skipped');
        $after = $active->fresh()->getAttributes();
        $fields = ['uuid', 'git_branch', 'git_commit_sha', 'docker_compose_raw', 'docker_compose_location', 'docker_compose_custom_start_command', 'docker_compose_custom_build_command'];
        $unchanged = true;
        foreach ($fields as $field) {
            if (($before[$field] ?? null) !== ($after[$field] ?? null)) $unchanged = false;
        }
        if (! $unchanged) {
            throw new \RuntimeException('Active application metadata changed concurrently');
        }
        echo json_encode([
            'version' => getenv('COOLIFY_VERSION'),
            'raw_compose' => true,
            'build_server' => false,
            'installed_application_class_sha256' => hash('sha256', (new \ReflectionClass($active))->getFileName() ? file_get_contents((new \ReflectionClass($active))->getFileName()) : ''),
            'compose' => $probe->docker_compose_raw,
            'injected_start_command' => $injected,
            'services' => array_keys($parsed['services']),
            'custom_build_command' => $build,
            'custom_commands_validated_by_installed_job' => true,
            'shell_redirection_rejected' => $redirectionRejected,
            'installed_automatic_pull_skip_method_exercised' => true,
            'deployment_log_writes_intercepted' => true,
            'active_metadata_unchanged' => true,
            'database_transaction_readonly' => true,
            'remote_parser_commands_blocked' => true,
            'full_deployment_job_executed' => false,
        ], JSON_PRETTY_PRINT), PHP_EOL;
    } catch (\Throwable $e) {
        echo json_encode(['probe_error' => get_class($e), 'message' => $e->getMessage()]), PHP_EOL;
        exit(2);
    } finally {
        \Illuminate\Support\Facades\DB::rollBack();
    }
}
