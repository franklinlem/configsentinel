<?php
// CLI entrypoint: code supplied separately from JSON stdin; stdout is one envelope.
// Only invoke against active target after a separate explicit window authorization.
ob_start();
set_error_handler(static function ($level, $message, $file, $line) {
    if (!(error_reporting() & $level)) return false;
    throw new ErrorException('php_warning', 0, $level, $file, $line);
});
try {
    require '/var/www/html/vendor/autoload.php';
    $app=require '/var/www/html/bootstrap/app.php';
    $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
    $payload=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
    if (!is_array($payload)) throw new RuntimeException('invalid_input');
    $result=configsentinel_j5_apply($payload);
    if (ob_get_length() !== 0) throw new RuntimeException('internal_error');
    ob_end_clean();
    echo json_encode(['version'=>1,'status'=>'ok','data'=>$result,'error'=>null],JSON_THROW_ON_ERROR),PHP_EOL;
    exit(0);
} catch (Throwable $e) {
    if (ob_get_level()) ob_end_clean();
    $allowed=['invalid_input','scope_rejected','state_drift','transaction_failed','internal_error'];
    $category=in_array($e->getMessage(),$allowed,true) ? $e->getMessage() : 'internal_error';
    echo json_encode(['version'=>1,'status'=>'error','data'=>null,'error'=>$category]),PHP_EOL;
    exit(2);
}
