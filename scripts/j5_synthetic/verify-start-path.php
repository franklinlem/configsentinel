<?php
// Pure path/command probe inside a synthetic Coolify CLI container.
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$target='oi6lvzwzomwtbbgzf5uzofuh';
$start='docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name '.$target.' up -d --pull never --no-build';
$jobClass=new ReflectionClass(App\Jobs\ApplicationDeploymentJob::class);
$job=$jobClass->newInstanceWithoutConstructor();
$jobClass->getMethod('validateShellSafeCommand')->invoke($job,$start,'docker_compose_custom_start_command');
$workdir='/artifacts/configsentinel-synthetic';
$rewritten=(string)str($start)->replaceFirst('compose','compose --project-directory '.$workdir);
$injected=injectDockerComposeFlags($rewritten,'/host-only/compose.yaml','/host-only/.env');
if($injected!==$rewritten || str_contains($injected,'/host-only/') || substr_count($injected,'--env-file')!==1 || strlen($start)>255 || !str_contains($injected,' --pull never --no-build')) throw new RuntimeException('start_path_probe_failed');
echo json_encode(['result'=>'PASS','installed_job_validator_accepted'=>true,'installed_flag_injector_preserved_relative_paths'=>true,'project_directory_is_workdir'=>true,'no_host_only_paths'=>true,'env_flags'=>1,'command_length'=>strlen($start),'pull_never_no_build'=>true,'synthetic_only'=>true]),PHP_EOL;
