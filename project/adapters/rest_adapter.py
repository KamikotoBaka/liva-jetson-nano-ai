from adapters.base_adapter import AdapterExecutionResult, BaseAdapter


class RestAdapter(BaseAdapter):
	def __init__(self, base_url: str = "http://localhost:8080") -> None:
		self.base_url = base_url.rstrip("/")

	def execute(self, intent: str, entity: str | None = None) -> AdapterExecutionResult:
		if intent == "identify_error":
			endpoint = "/api/devices/status"
			command = f"GET {self.base_url}{endpoint}"
			payload = {
				"devices": [
					{
						"name": "Living room lamp",
						"status": "error",
						"reason": "Connection interrupted",
					},
					{
						"name": "Kitchen sensor",
						"status": "ok",
					},
				]
			}
			return AdapterExecutionResult(command=command, payload=payload)

		command = f"GET {self.base_url}/api/devices"
		return AdapterExecutionResult(command=command, payload={"devices": []})
