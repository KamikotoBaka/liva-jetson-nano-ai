import subprocess


class PiperTTS:
	def __init__(self, executable: str = "piper", model_path: str | None = None) -> None:
		self.executable = executable
		self.model_path = model_path

	def command_preview(self, text: str) -> str:
		if self.model_path:
			return f'{self.executable} --model "{self.model_path}" --output-raw | aplay'
		return f"{self.executable} --model <model.onnx> --output-raw | aplay"

	def synthesize(self, text: str) -> str:
		if not self.model_path:
			return self.command_preview(text)

		command = [self.executable, "--model", self.model_path, "--output_file", "output.wav"]
		subprocess.run(command, input=text, text=True, check=True)
		return "Generated output.wav"
