import os
import json
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


class FasterWhisperSTT:
	def __init__(self, model_size: str = "base", device: str = "cpu") -> None:
		self.model_size = model_size
		self.device = device
		self.compute_type = "float16" if device == "cuda" else "int8"
		self.download_root = Path(__file__).resolve().parent.parent / "models" / "faster-whisper"
		self._model = None

		# Windows often cannot create symlinks in the default HF cache.
		# Suppress the warning and use a project-local model cache instead.
		os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

	def _load_model(self):
		if self._model is not None:
			return self._model

		try:
			from faster_whisper import WhisperModel
		except ImportError:
			return None

		self.download_root.mkdir(parents=True, exist_ok=True)
		self._model = WhisperModel(
			self.model_size,
			device=self.device,
			compute_type=self.compute_type,
			download_root=str(self.download_root),
		)
		return self._model

	def preload(self) -> None:
		model = self._load_model()
		if model is None:
			raise RuntimeError("faster-whisper is not installed")

	def transcribe_audio(self, audio_path: str) -> str:
		model = self._load_model()
		if model is None:
			raise RuntimeError("faster-whisper is not installed")

		segments, _ = model.transcribe(audio_path)
		return " ".join(segment.text.strip() for segment in segments).strip()

	def transcribe_text(self, text: str) -> str:
		return text.strip()


class WhisperCppSTT:
	def __init__(self, base_url: str, model_size: str = "base", device: str = "cpu") -> None:
		self.base_url = base_url.rstrip("/")
		self.model_size = model_size
		self.device = device

	def preload(self) -> None:
		if not self.base_url:
			raise RuntimeError("WHISPER_URL is not configured")

	def transcribe_audio(self, audio_path: str) -> str:
		if not self.base_url:
			raise RuntimeError("WHISPER_URL is not configured")

		with open(audio_path, "rb") as audio_file:
			audio_bytes = audio_file.read()

		# Prefer whisper.cpp server endpoint first, then OpenAI-compatible fallback.
		for endpoint in ("/inference", "/v1/audio/transcriptions"):
			result = self._post_audio(endpoint, audio_bytes, Path(audio_path).name)
			if result:
				return result

		raise RuntimeError("Whisper service returned no transcription")

	def transcribe_text(self, text: str) -> str:
		return text.strip()

	def _post_audio(self, endpoint: str, audio_bytes: bytes, filename: str) -> str | None:
		boundary = "----liva-boundary-7d3f4b9c"
		parts = [
			f"--{boundary}\r\n".encode("utf-8"),
			b'Content-Disposition: form-data; name="file"; filename="',
			filename.encode("utf-8", errors="ignore"),
			b'"\r\n',
			b"Content-Type: application/octet-stream\r\n\r\n",
			audio_bytes,
			b"\r\n",
		]

		if endpoint == "/v1/audio/transcriptions":
			parts.extend(
				[
					f"--{boundary}\r\n".encode("utf-8"),
					b'Content-Disposition: form-data; name="model"\r\n\r\n',
					b"whisper-1\r\n",
				]
			)

		parts.append(f"--{boundary}--\r\n".encode("utf-8"))
		payload = b"".join(parts)

		req = urllib_request.Request(
			url=f"{self.base_url}{endpoint}",
			data=payload,
			headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
			method="POST",
		)

		try:
			with urllib_request.urlopen(req, timeout=45) as response:
				body = response.read().decode("utf-8", errors="ignore")
			text = self._extract_transcript(body)
			if text:
				return text.strip()
		except (urllib_error.URLError, TimeoutError, ValueError):
			# Multipart attempt failed — fall through to possible raw attempt.
			body = ""

		# Fallback: some whisper servers expect raw WAV bytes (no multipart)
		if endpoint == "/inference":
			try:
				req2 = urllib_request.Request(
					url=f"{self.base_url}{endpoint}",
					data=audio_bytes,
					headers={"Content-Type": "audio/wav"},
					method="POST",
				)
				with urllib_request.urlopen(req2, timeout=45) as response:
					body2 = response.read().decode("utf-8", errors="ignore")
					text2 = self._extract_transcript(body2)
					if text2:
						return text2.strip()
			except (urllib_error.URLError, TimeoutError, ValueError):
				return None

		return None

	def _extract_transcript(self, body: str) -> str | None:
		cleaned = body.strip()
		if not cleaned:
			return None

		try:
			parsed = json.loads(cleaned)
		except json.JSONDecodeError:
			return cleaned

		if isinstance(parsed, dict):
			for key in ("text", "transcription", "result", "output"):
				value = parsed.get(key)
				if isinstance(value, str) and value.strip():
					return value

			data = parsed.get("data")
			if isinstance(data, dict):
				value = data.get("text")
				if isinstance(value, str) and value.strip():
					return value

		return None
