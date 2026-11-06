$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$custom = "ghcr.io/riccardograssi/photoprism:hub"
docker build -f (Join-Path $root "src\Dockerfile") -t $custom $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker push $custom
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output $custom
