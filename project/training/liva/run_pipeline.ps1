$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $root
$venvPy = Join-Path $root ".venv-liva-train\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "Training venv not found. Run: .\training\liva\setup_train_env.ps1"
    exit 1
}

$positiveRaw = Join-Path $PSScriptRoot "data\positive_raw"
$negativeRaw = Join-Path $PSScriptRoot "data\negative_raw"
$prepared = Join-Path $PSScriptRoot "data\prepared"
$verifierOut = Join-Path $projectRoot "models\liva_verifier.pkl"

& $venvPy (Join-Path $PSScriptRoot "prepare_dataset.py") `
    --positive $positiveRaw `
    --negative $negativeRaw `
    --out $prepared `
    --test-ratio 0.2

& $venvPy (Join-Path $PSScriptRoot "train_liva_verifier.py") `
    --positive (Join-Path $prepared "positive_train") `
    --negative (Join-Path $prepared "negative_train") `
    --output $verifierOut `
    --base-model alexa `
    --threshold 0.25

Write-Host "Done. Generated verifier: $verifierOut"
Write-Host "Note: This is a verifier (.pkl), not a full custom wakeword ONNX model."
