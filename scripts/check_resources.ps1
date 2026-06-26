$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Push-Location $ProjectRoot
try {
    if ($args.Count -gt 0) {
        & $Python -m mpxccp.integration.packaging.resource_check $args[0]
    }
    else {
        & $Python -m mpxccp.integration.packaging.resource_check
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
