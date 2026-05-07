# Voice Assistant Project Documentation

This document explains the project structure **file by file**:
- what each file stands for,
- what it currently does,
- and what its intended responsibility should be.

---

## 1) High-Level Architecture

The system is split into two parts:

1. **Python backend** (project root)
   - STT abstraction (`stt/`)
   - Intent detection (`nlu/`)
   - Dispatcher (`dispatcher.py`)
  - Device adapters (`adapters/`) for REST, MQTT, and Shell
   - TTS abstraction (`tts/`)
   - API entrypoint (`main.py`)

2. **React frontend** (`vite-project/`)
   - UI for command creation, command execution, microphone input, and output fields.

Current runtime flow:
1. User enters text or uses microphone in UI.
2. Frontend tries to match a saved command phrase.
3. If matched: execute mapped action text directly in UI.
4. If not matched: call backend `POST /api/process`.
5. Backend parses intent and dispatches REST/MQTT adapter actions.
6. Backend returns STT text, action command text, and TTS response text.

Shell-command flow (new):
1. User says e.g. `Reload apache server`.
2. NLU maps it to intent `restart_apache`.
3. Dispatcher calls `ShellAdapter`.
4. Shell adapter executes only a strict whitelist command for current OS.
5. Backend returns command output + TTS response.

---

## 2) Root-Level Files

### `main.py`
**Stands for:** backend API entrypoint (ASGI app).

**Current role:**
- Creates FastAPI app.
- Adds CORS for `http://localhost:5173`.
- Defines:
  - `GET /health`
  - `POST /api/process`
- Uses:
  - `FasterWhisperSTT` (`stt/whisper_stt.py`)
  - `CommandDispatcher` (`dispatcher.py`)
  - `PiperTTS` (`tts/piper_tts.py`)

**Should do:**
- Remain the orchestration/API boundary only.
- Keep business logic in dispatcher/services, not in endpoints.

---

### `dispatcher.py`
**Stands for:** intent-to-action router.

**Current role:**
- Calls `parse_intent` from NLU.
- For `identify_error`:
  - executes REST adapter
  - executes MQTT adapter
  - builds final TTS message from adapter payload
- Returns unified dictionary with `intent`, `command`, `tts_text`.

**Should do:**
- Be the central decision engine for all intents.
- Add additional intent branches as your command set grows.

---

### `requirements.txt`
**Stands for:** Python dependencies for backend.

**Current role:**
- Includes `fastapi`, `uvicorn`, `pydantic`, `faster-whisper`, `paho-mqtt`, `httpx`.

**Should do:**
- Stay the single source of backend package requirements.

---

### `package.json` (root)
**Stands for:** root Node dependency manifest.

**Current role:**
- Contains `axios` dependency.

**Should do:**
- Either be used intentionally for root-level tooling/scripts, or be removed if unused.

---

### `package-lock.json` (root)
**Stands for:** exact lockfile for root `package.json` dependencies.

**Current role:**
- Locks `axios` version tree.

**Should do:**
- Be committed if root `package.json` is used.

---

## 3) Backend Modules

### `adapters/base_adapter.py`
**Stands for:** adapter interface contract.

**Current role:**
- Defines `AdapterExecutionResult` dataclass (`command`, `payload`).
- Defines abstract `BaseAdapter.execute()` method.

**Should do:**
- Remain common adapter API that all protocol adapters implement.

---

### `adapters/rest_adapter.py`
**Stands for:** REST protocol adapter.

**Current role:**
- For `identify_error` returns simulated REST command and simulated devices payload.
- For unknown intent returns generic devices command.

**Should do:**
- Replace simulated payload with real HTTP calls (`httpx`), retries, timeout handling.

---

### `adapters/mqtt_adapter.py`
**Stands for:** MQTT protocol adapter.

**Current role:**
- Returns simulated MQTT subscribe command + simulated error message payload.

**Should do:**
- Connect to real broker (`paho-mqtt`) and consume real topic messages.

---

### `adapters/shell_adapter.py`
**Stands for:** secure OS command adapter.

**Current role:**
- Detects OS (`windows` or `linux`).
- Loads whitelist from `config/devices.yaml` (`shell_commands.windows` / `shell_commands.linux`).
- Falls back to internal safe defaults if config is missing/invalid.
- Executes only whitelisted commands with `subprocess.run` and timeout.
- Returns structured payload: `success`, `output`, `error`, `returncode`.

**Should do:**
- Stay the only path for system command execution.
- Keep whitelist minimal and explicit.
- Use environment-specific service names when deploying to a new machine.

---

### `nlu/intent_parser.py`
**Stands for:** rule-based intent classifier.

**Current role:**
- Regex-based intent detection:
  - `identify_error`
  - `restart_apache`
  - `stop_apache`
  - `restart_nginx`
  - `system_status`
  - `check_disk`
  - `check_memory`
  - `turn_on_device`
  - `turn_off_device`
  - fallback `unknown`

**Should do:**
- Continue as lightweight NLU, or be replaced by richer intent/entity extraction if needed.

---

### `stt/whisper_stt.py`
**Stands for:** STT service wrapper.

**Current role:**
- Lazy-loads `faster_whisper.WhisperModel`.
- `transcribe_audio(audio_path)` for real audio transcription.
- `transcribe_text(text)` pass-through helper for typed MVP flow.

**Should do:**
- Be the only STT abstraction point (easy to swap models later).

---

### `tts/piper_tts.py`
**Stands for:** TTS service wrapper.

**Current role:**
- `command_preview()` creates piper command preview string.
- `synthesize()` runs piper command when `model_path` is configured.

**Should do:**
- Centralize all text-to-speech execution and output-file strategy.

---

### `config/devices.yaml`
**Stands for:** declarative device configuration.

**Current role:**
- Contains OS-specific shell command whitelist under `shell_commands`.
- Defines allowed intent-to-command mappings for `linux` and `windows`.

**Should do:**
- Keep shell whitelist minimal and audited.
- Extend with device metadata (name, id, protocol, endpoint/topic, capabilities) when integrating real devices.

---

## 4) Frontend (`vite-project/`)

### `vite-project/src/App.jsx`
**Stands for:** main application UI and interaction logic.

**Current role:**
- Command menu:
  - create command phrase + action mapping
  - delete mappings
  - persist mappings in `localStorage`
- Theme toggle:
  - white/black mode
  - persisted in `localStorage`
- Execution:
  - typed command processing
  - microphone input using Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
  - fallback to backend `/api/process` when no saved mapping matches
- Displays three output fields:
  - STT result
  - action command
  - TTS text

**Should do:**
- Stay as UI orchestration layer; avoid protocol/business logic duplication.

---

### `vite-project/src/App.css`
**Stands for:** component-level style system for app UI.

**Current role:**
- Defines card layout, forms, button styles, command list styles.
- Defines black theme variable overrides via `.theme-black`.
- Handles wrapping for long command/action text.

**Should do:**
- Keep all page component styling centralized and readable.

---

### `vite-project/src/index.css`
**Stands for:** global/base styles.

**Current role:**
- Defines global background/text CSS variables.
- Switches body theme via `body[data-theme='black']`.
- Styles `body` and `#root` base layout.

**Should do:**
- Keep only global styles and theme primitives.

---

### `vite-project/src/main.jsx`
**Stands for:** React bootstrap file.

**Current role:**
- Mounts `<App />` into `#root`.
- Wraps app in `StrictMode`.

**Should do:**
- Stay minimal bootstrap entrypoint.

---

### `vite-project/vite.config.js`
**Stands for:** Vite build/dev server configuration.

**Current role:**
- Enables React plugin.
- Proxies `/api` and `/health` to backend on `127.0.0.1:8000`.

**Should do:**
- Keep all frontend dev-server proxy configuration in one place.

---

### `vite-project/package.json`
**Stands for:** frontend dependency/scripts manifest.

**Current role:**
- Scripts: `dev`, `build`, `lint`, `preview`.
- Dependencies: `react`, `react-dom`.
- Dev dependencies: Vite + ESLint toolchain.

**Should do:**
- Remain authoritative for frontend tooling and scripts.

---

### `vite-project/package-lock.json`
**Stands for:** locked frontend dependency tree.

**Current role:**
- Exact versions for reproducible installs.

**Should do:**
- Stay committed and updated with dependency changes.

---

### `vite-project/index.html`
**Stands for:** HTML shell for Vite app.

**Current role:**
- Defines root mounting element and script entry to `src/main.jsx`.

**Should do:**
- Stay minimal static shell.

---

### `vite-project/eslint.config.js`
**Stands for:** linting rules for frontend JS/JSX.

**Current role:**
- Uses recommended JS + React hooks + React refresh rules.
- Ignores `dist`.
- Includes no-unused-vars rule.

**Should do:**
- Keep code quality and consistency enforcement.

---

### `vite-project/README.md`
**Stands for:** default Vite template README.

**Current role:**
- Still contains generic template notes.

**Should do:**
- Be replaced with project-specific frontend setup and usage details.

---

### `vite-project/.gitignore`
**Stands for:** ignore rules for frontend workspace artifacts.

**Current role:**
- Ignores logs, build output, `node_modules`, editor files.

**Should do:**
- Continue preventing local/generated noise in version control.

---

### `vite-project/public/vite.svg`
**Stands for:** static asset from Vite template.

**Current role:**
- Used as favicon in `index.html`.

**Should do:**
- Optional; can be replaced with project icon.

---

### `vite-project/src/assets/react.svg`
**Stands for:** default React logo asset from template.

**Current role:**
- Not used by current UI.

**Should do:**
- Remove if unused, or replace with project assets.

---

## 5) Existing Project Docs

### `docs/Modules.txt`
**Stands for:** initial architecture and run notes (German).

**Current role:**
- Contains module overview, example flow, quick start, and troubleshooting.

**Should do:**
- Continue as concise operational note.
- Can link to this markdown doc for deeper file-level explanation.

---

### `docs/Architecture.drawio`
**Stands for:** visual architecture diagram source.

**Current role:**
- Stores editable diagram in Draw.io format.

**Should do:**
- Stay synchronized with real runtime architecture.

---

## 6) Generated/Build Folders (Not Hand-Authored)

### `__pycache__/` (multiple backend folders)
- Python bytecode cache generated automatically.

### `vite-project/dist/`
- Production frontend build output from `npm run build`.

### `node_modules/` (root and `vite-project/`)
- Installed npm packages.

These folders should not be treated as source code documentation targets.

---

## 7) Recommended Next Documentation Improvements

1. Add `docs/API.md` with explicit request/response examples for:
   - `GET /health`
   - `POST /api/process`

2. Add `docs/DEV_SETUP.md` with:
   - Python environment setup
   - backend start commands
   - frontend start commands
   - microphone browser support notes

3. Replace `vite-project/README.md` template content with project-specific instructions.
