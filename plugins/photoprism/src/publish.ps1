$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$hub = "ghcr.io/riccardograssi/photoprism:hub"
$web = "ghcr.io/riccardograssi/photoprism:hub-web"
docker build -f (Join-Path $root "src\Dockerfile") -t $hub $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker push $hub
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker build -f (Join-Path $root "src\web\Dockerfile") -t $web $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker push $web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output $hub
Write-Output $web
