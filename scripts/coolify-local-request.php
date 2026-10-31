<?php
// Execute Coolify's authenticated controllers over SSH without enabling its public API.
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$input=json_decode(file_get_contents($argv[1]),true,512,JSON_THROW_ON_ERROR);
$routes=[
 'project'=>[App\Http\Controllers\Api\ProjectController::class,'create_project'],
 'environment'=>[App\Http\Controllers\Api\ProjectController::class,'create_environment'],
 'application'=>[App\Http\Controllers\Api\ApplicationsController::class,'create_private_gh_app_application'],
 'update'=>[App\Http\Controllers\Api\ApplicationsController::class,'update_by_uuid'],
 'envs'=>[App\Http\Controllers\Api\ApplicationsController::class,'create_bulk_envs'],
 'deploy'=>[App\Http\Controllers\Api\DeployController::class,'deploy_by_uuid'],
];
if(!isset($routes[$input['action']]))throw new RuntimeException('Unknown action');
$token=App\Models\PersonalAccessToken::findOrFail(explode('|',file_get_contents('/tmp/configsentinel-api-token'))[0]);
$user=App\Models\User::findOrFail(0)->withAccessToken($token);
Illuminate\Support\Facades\Auth::setUser($user);
session()->put('currentTeam',App\Models\Team::findOrFail(0));
$r=Illuminate\Http\Request::create('/api/v1/operator','POST',$input['body']??[]);
$r->setJson(new Symfony\Component\HttpFoundation\InputBag($input['body']??[]));
$r->headers->set('Accept','application/json');$r->headers->set('Content-Type','application/json');
$r->setUserResolver(fn()=>$user);
$route=new Illuminate\Routing\Route('POST','api/v1/operator/{uuid?}',fn()=>null);$route->bind($r);
foreach(($input['params']??[]) as $k=>$v)$route->setParameter($k,$v);
$r->setRouteResolver(fn()=>$route);
$app->instance('request',$r);
[$class,$method]=$routes[$input['action']];
$response=$app->make($class)->$method($r);
if($input['action']==='envs'){echo json_encode(['status'=>$response->getStatusCode()]);}else{echo $response->getContent();}
if($response->getStatusCode()>=400)exit(1);
