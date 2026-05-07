from pathlib import Path

import numpy as np
import yaml


class OpenWakeWordService:
    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "config" / "wakeword.yaml"
        self.target_wakeword = "liva"
        self.threshold = 0.5
        self.custom_model_path: Path | None = None
        self.model = None
        self.available = False
        self.reason = "openWakeWord is not initialized"
        self.active_label: str | None = None

        self._load_config()
        self._init_model()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            return

        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
        except (yaml.YAMLError, OSError):
            return

        self.target_wakeword = str(config.get("target_wakeword", self.target_wakeword)).strip().lower()
        self.threshold = float(config.get("threshold", self.threshold))

        custom_path = config.get("custom_model_path")
        if isinstance(custom_path, str) and custom_path.strip():
            resolved = Path(custom_path)
            if not resolved.is_absolute():
                resolved = (self.config_path.parent.parent / resolved).resolve()
            self.custom_model_path = resolved

    @staticmethod
    def _normalize_label(value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")

    def _discover_labels(self) -> list[str]:
        if self.model is None:
            return []

        labels: list[str] = []
        models_attr = getattr(self.model, "models", None)
        if isinstance(models_attr, dict):
            labels.extend(models_attr.keys())

        wakewords_attr = getattr(self.model, "wakewords", None)
        if isinstance(wakewords_attr, list):
            labels.extend(str(item) for item in wakewords_attr)

        unique = []
        for label in labels:
            if label not in unique:
                unique.append(label)
        return unique

    def _init_model(self) -> None:
        try:
            import openwakeword  # type: ignore[import-not-found]
            from openwakeword import utils as openwakeword_utils  # type: ignore[import-not-found]
            from openwakeword.model import Model  # type: ignore[import-not-found]
        except Exception:
            self.available = False
            self.reason = "openWakeWord package is not installed"
            return

        # Some environments install the Python package without bundled model files.
        # If the expected asset directory is missing, download official models first.
        if not self.custom_model_path:
            try:
                resources_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
                required_files = [
                    resources_dir / "embedding_model.onnx",
                    resources_dir / "melspectrogram.onnx",
                    resources_dir / "alexa_v0.1.onnx",
                ]
                if any(not file_path.exists() for file_path in required_files):
                    openwakeword_utils.download_models(target_directory=str(resources_dir))
            except Exception as exc:
                self.available = False
                self.reason = f"openWakeWord model download failed: {exc}"
                return

        kwargs = {}
        kwargs["inference_framework"] = "onnx"
        if self.custom_model_path:
            if self.custom_model_path.exists():
                kwargs["wakeword_models"] = [str(self.custom_model_path)]
            else:
                self.available = False
                self.reason = f"Custom wakeword model not found: {self.custom_model_path}"
                return

        try:
            self.model = Model(**kwargs)
        except Exception as exc:
            self.available = False
            self.reason = f"openWakeWord model init failed: {exc}"
            return

        labels = self._discover_labels()

        if self.custom_model_path:
            self.active_label = self.custom_model_path.stem
            self.available = True
            self.reason = "ok"
            return

        normalized_target = self._normalize_label(self.target_wakeword)
        for label in labels:
            if self._normalize_label(label) == normalized_target:
                self.active_label = label
                self.available = True
                self.reason = "ok"
                return

        self.available = False
        self.reason = (
            f"Wake word '{self.target_wakeword}' is not in loaded openWakeWord models. "
            f"Provide custom_model_path in config/wakeword.yaml."
        )

    def status(self) -> dict:
        return {
            "available": self.available,
            "wakeword": self.target_wakeword,
            "activeLabel": self.active_label,
            "threshold": self.threshold,
            "reason": self.reason,
        }

    @staticmethod
    def _resample_to_16k(samples: np.ndarray, sample_rate: int) -> np.ndarray:
        if sample_rate == 16000:
            return samples

        duration = len(samples) / float(sample_rate)
        if duration <= 0:
            return np.array([], dtype=np.float32)

        target_len = int(duration * 16000)
        if target_len <= 1:
            return np.array([], dtype=np.float32)

        x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
        return np.interp(x_new, x_old, samples).astype(np.float32)

    def detect_from_samples(self, samples: list[float], sample_rate: int) -> dict:
        if not self.available or self.model is None or not self.active_label:
            status = self.status()
            return {
                "available": status["available"],
                "detected": False,
                "score": 0.0,
                "threshold": status["threshold"],
                "wakeword": status["wakeword"],
                "reason": status["reason"],
            }

        data = np.asarray(samples, dtype=np.float32)
        if data.size == 0:
            return {
                "available": True,
                "detected": False,
                "score": 0.0,
                "threshold": self.threshold,
                "wakeword": self.target_wakeword,
                "reason": "No audio samples provided",
            }

        if data.ndim > 1:
            data = data.mean(axis=1)

        data = np.clip(data, -1.0, 1.0)
        data = self._resample_to_16k(data, sample_rate)
        if data.size == 0:
            return {
                "available": True,
                "detected": False,
                "score": 0.0,
                "threshold": self.threshold,
                "wakeword": self.target_wakeword,
                "reason": "Audio too short",
            }

        pcm = (data * 32767.0).astype(np.int16)
        chunk_size = 1280
        max_score = 0.0

        for i in range(0, len(pcm), chunk_size):
            chunk = pcm[i : i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode="constant")

            prediction = self.model.predict(chunk)
            if isinstance(prediction, dict):
                score = float(prediction.get(self.active_label, 0.0))
                max_score = max(max_score, score)

        return {
            "available": True,
            "detected": max_score >= self.threshold,
            "score": max_score,
            "threshold": self.threshold,
            "wakeword": self.target_wakeword,
            "reason": "ok",
        }
