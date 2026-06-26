$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Push-Location $ProjectRoot
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check_resources.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $ResourceDir = Join-Path $ProjectRoot "mpxccp\resources"
    $IconPath = Join-Path $ResourceDir "icons\app.png"
    $EntryPoint = Join-Path $ProjectRoot "mpxccp\main.py"

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --name "MPXCCP" `
        --windowed `
        --icon $IconPath `
        --add-data "$ResourceDir;mpxccp\resources" `
        $EntryPoint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
