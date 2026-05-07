from adapters.base_adapter import AdapterExecutionResult, BaseAdapter
import json
import os
from urllib import request as urllib_request
from urllib import error as urllib_error


class MatterAdapter(BaseAdapter):
    """
    Matter adapter for controlling Matter devices through a Matter controller.
    
    Supports:
    - Home Assistant Matter integration
    - OpenHAB with Matter support  
    - Any Matter controller with a REST API
    
    Environment variables:
    - MATTER_CONTROLLER_URL: Base URL for Matter controller (default: http://127.0.0.1:8008)
    - MATTER_API_TOKEN: Optional auth token for controller
    """
    
    def __init__(self, controller_url: str | None = None, api_token: str | None = None) -> None:
        self.controller_url = (controller_url or os.getenv("MATTER_CONTROLLER_URL", "http://127.0.0.1:8008")).rstrip("/")
        self.api_token = api_token or os.getenv("MATTER_API_TOKEN", "")
    
    def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict | None:
        """Generic HTTP request handler for Matter controller."""
        url = f"{self.controller_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib_request.Request(url=url, data=body, headers=headers, method=method)
        
        try:
            with urllib_request.urlopen(req, timeout=5) as resp:
                response_data = resp.read().decode("utf-8")
                return json.loads(response_data) if response_data else {}
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            return None
    
    def discover_devices(self) -> list[dict]:
        """Discover available Matter devices from controller."""
        # Try Home Assistant format first
        devices = self._make_request("GET", "/api/matter/devices")
        if devices and isinstance(devices, list):
            return devices
        
        # Try OpenHAB format
        devices = self._make_request("GET", "/rest/things?metadata=matter")
        if devices and isinstance(devices, list):
            return devices
        
        return []
    
    def find_device_by_type(self, device_type: str) -> dict | None:
        """Find device by type: light, switch, thermostat, etc."""
        try:
            devices = self.discover_devices()
            for device in devices:
                dtype = device.get("type", "").lower()
                name = device.get("name", "").lower()
                
                if device_type.lower() in dtype or device_type.lower() in name:
                    return device
        except Exception:
            pass
        return None
    
    def execute(self, intent: str, entity: str | None = None) -> AdapterExecutionResult:
        """Execute Matter commands based on intent."""
        
        if intent == "turn_on_device":
            return self._execute_turn_on(entity)
        elif intent == "turn_off_device":
            return self._execute_turn_off(entity)
        elif intent == "set_brightness":
            return self._execute_set_brightness(entity)
        elif intent == "set_temperature":
            return self._execute_set_temperature(entity)
        
        command = f"Matter: Unknown intent {intent}"
        return AdapterExecutionResult(
            command=command,
            payload={"status": "unknown_intent", "message": f"Intent '{intent}' not mapped for Matter"}
        )
    
    def _execute_turn_on(self, entity: str | None = None) -> AdapterExecutionResult:
        """Turn on a Matter device."""
        device = self.find_device_by_type("light") if not entity else self._find_device_by_name(entity)
        
        if not device:
            return AdapterExecutionResult(
                command="Matter: turn_on (no device found)",
                payload={"status": "error", "reason": "No device found"}
            )
        
        device_id = device.get("id") or device.get("uid", "unknown")
        endpoint = f"/api/matter/devices/{device_id}/on"
        
        result = self._make_request("POST", endpoint, {"command": "ON"})
        
        return AdapterExecutionResult(
            command=f"Matter: turn_on {device.get('name', 'device')}",
            payload={"status": "ok", "device": device.get("name", "device"), "action": "turned on"}
        )
    
    def _execute_turn_off(self, entity: str | None = None) -> AdapterExecutionResult:
        """Turn off a Matter device."""
        device = self.find_device_by_type("light") if not entity else self._find_device_by_name(entity)
        
        if not device:
            return AdapterExecutionResult(
                command="Matter: turn_off (no device found)",
                payload={"status": "error", "reason": "No device found"}
            )
        
        device_id = device.get("id") or device.get("uid", "unknown")
        endpoint = f"/api/matter/devices/{device_id}/off"
        
        result = self._make_request("POST", endpoint, {"command": "OFF"})
        
        return AdapterExecutionResult(
            command=f"Matter: turn_off {device.get('name', 'device')}",
            payload={"status": "ok", "device": device.get("name", "device"), "action": "turned off"}
        )
    
    def _execute_set_brightness(self, entity: str | None = None) -> AdapterExecutionResult:
        """Set brightness on a Matter light device (0-100)."""
        device = self.find_device_by_type("light") if not entity else self._find_device_by_name(entity)
        
        # Extract brightness level from entity if present
        brightness = 50
        if entity and any(char.isdigit() for char in entity):
            try:
                brightness = int(''.join(filter(str.isdigit, entity)))
                brightness = max(0, min(100, brightness))
            except (ValueError, TypeError):
                pass
        
        if not device:
            return AdapterExecutionResult(
                command="Matter: set_brightness (no device found)",
                payload={"status": "error", "reason": "No device found"}
            )
        
        device_id = device.get("id") or device.get("uid", "unknown")
        endpoint = f"/api/matter/devices/{device_id}/brightness"
        
        result = self._make_request("POST", endpoint, {"brightness": brightness})
        
        return AdapterExecutionResult(
            command=f"Matter: set_brightness {device.get('name', 'device')} to {brightness}%",
            payload={"status": "ok", "device": device.get("name", "device"), "brightness": brightness}
        )
    
    def _execute_set_temperature(self, entity: str | None = None) -> AdapterExecutionResult:
        """Set temperature on a Matter thermostat device."""
        device = self.find_device_by_type("thermostat") if not entity else self._find_device_by_name(entity)
        
        # Extract temperature from entity if present
        temperature = 21
        if entity and any(char.isdigit() for char in entity):
            try:
                temperature = int(''.join(filter(str.isdigit, entity)))
            except (ValueError, TypeError):
                pass
        
        if not device:
            return AdapterExecutionResult(
                command="Matter: set_temperature (no device found)",
                payload={"status": "error", "reason": "No device found"}
            )
        
        device_id = device.get("id") or device.get("uid", "unknown")
        endpoint = f"/api/matter/devices/{device_id}/temperature"
        
        result = self._make_request("POST", endpoint, {"temperature": temperature})
        
        return AdapterExecutionResult(
            command=f"Matter: set_temperature {device.get('name', 'device')} to {temperature}°C",
            payload={"status": "ok", "device": device.get("name", "device"), "temperature": temperature}
        )
    
    def _find_device_by_name(self, name: str) -> dict | None:
        """Find device by name in discovered devices."""
        try:
            devices = self.discover_devices()
            name_lower = name.lower()
            for device in devices:
                if name_lower in device.get("name", "").lower():
                    return device
        except Exception:
            pass
        return None