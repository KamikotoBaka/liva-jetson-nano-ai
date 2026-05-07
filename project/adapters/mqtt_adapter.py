from adapters.base_adapter import AdapterExecutionResult, BaseAdapter


class MqttAdapter(BaseAdapter):
	def __init__(self, broker: str = "localhost", port: int = 1883) -> None:
		self.broker = broker
		self.port = port

	def execute(self, intent: str, entity: str | None = None) -> AdapterExecutionResult:
		topic = "devices/+/error" if intent == "identify_error" else "devices/+/status"
		command = f"MQTT subscribe mqtt://{self.broker}:{self.port}/{topic}"
		payload = {
			"topic": "devices/living-room-lamp/error",
			"message": {
				"device": "Living room lamp",
				"status": "error",
				"reason": "Connection interrupted",
			},
		}
		return AdapterExecutionResult(command=command, payload=payload)
