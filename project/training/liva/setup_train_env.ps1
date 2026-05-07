$ErrorActionPreference = "Stop"

Write-Host "Checking Python 3.11 availability..."
$py311 = py -3.11 -c "import sys; print(sys.version)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.11 not found."
    Write-Host "Install command (recommended):"
    Write-Host "  winget install --id Python.Python.3.11 -e"
    exit 1
}

$root = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $root ".venv-liva-train"

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath"
    py -3.11 -m venv $venvPath
}

$py = Join-Path $venvPath "Scripts\python.exe"

& $py -m pip install --upgrade pip
& $py -m pip install openwakeword onnxruntime numpy scipy scikit-learn pyyaml

Write-Host "Training environment ready."
Write-Host "Python executable: $py"
