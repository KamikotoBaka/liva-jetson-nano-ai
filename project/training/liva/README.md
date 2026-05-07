# LIVA Wakeword Training Toolkit (Windows)

This folder gives you a practical path to train a **LIVA** detector artifact for this project.

## What you get

- `setup_train_env.ps1`: creates a dedicated training venv (`.venv-liva-train`) with required packages.
- `prepare_dataset.py`: validates WAV clips and creates train/test splits.
- `train_liva_verifier.py`: trains an openWakeWord **verifier** model (`.pkl`) from your clips.
- `run_pipeline.ps1`: runs prepare + train in one command.

## Important note

- A `.pkl` verifier is not the same as a full custom wakeword `.onnx` model.
- Your backend currently expects `custom_model_path: models/liva.onnx` for full custom wakeword mode.
- Use this verifier pipeline as a practical intermediate step while you prepare/obtain a full ONNX wakeword model for `LIVA`.

## 1) Install Python 3.11 (if missing)

Recommended command:

```powershell
winget install --id Python.Python.3.11 -e
```

## 2) Create training environment

From project root:

```powershell
.\training\liva\setup_train_env.ps1
```

## 3) Add your recordings

Place WAV files into:

- `training/liva/data/positive_raw`: clips that contain only "LIVA"
- `training/liva/data/negative_raw`: speech/noise that does not contain "LIVA"

Audio format required:

- mono
- 16-bit PCM
- 16000 Hz
- `.wav`

Recommended counts:

- positive: at least 100
- negative: at least 300

## 4) Run the pipeline

```powershell
.\training\liva\run_pipeline.ps1
```

Output:

- `models/liva_verifier.pkl`

## 5) Full ONNX model for backend wake mode

When you have a full custom wakeword model, place it at:

- `models/liva.onnx`

Your config is already set to:

```yaml
custom_model_path: models/liva.onnx
```

Then restart backend and check:

- `GET /api/wakeword/status`

You should see `available: true` once the ONNX model is valid.
