from adapters.mqtt_adapter import MqttAdapter
from adapters.rest_adapter import RestAdapter
from adapters.shell_adapter import SHELL_INTENTS, ShellAdapter
from custom_commands_store import load_custom_commands
from datetime import datetime
from error_store import ErrorStore
from highbay_stock_service import get_highbay_stock_payload
from hue_lights_service import set_room_lights
from nlu.intent_parser import parse_intent
import json
import os
import re
from text_normalization import normalize_phrase
from text_normalization import normalize_phrase_relaxed
from urllib import request as urllib_request
from adapters.matter_adapter import MatterAdapter
class CommandDispatcher:
	def __init__(self, error_store: ErrorStore | None = None) -> None:
		self.rest_adapter = RestAdapter()
		self.mqtt_adapter = MqttAdapter()
		self.shell_adapter = ShellAdapter()
		self.matter_adapter = MatterAdapter()
		self.error_store = error_store or ErrorStore()

	def resolve_intent(self, stt_text: str) -> tuple[str, str | None]:
		if self._find_custom_command(stt_text):
			return "custom_command", None
		return parse_intent(stt_text)

	def dispatch(self, stt_text: str) -> dict:
		custom_response = self._dispatch_custom_command(stt_text)
		if custom_response is not None:
			return custom_response

		intent, entity = parse_intent(stt_text)

		INTENT_MAP = {
			"good_morning": 			lambda: dispatch_good_morning(self.error_store),
			"what_happened_today": 		lambda: dispatch_what_happened_today(self.error_store),
			"commands_executed_today": 	lambda: dispatch_commands_executed_today(self.error_store),
			"identify_error": 			lambda: dispatch_identify_error(self.error_store),
			"download_logs": 			lambda: dispatch_download_logs(self.error_store),
		}
		
		if intent in INTENT_MAP:
			return INTENT_MAP[intent]()

		if intent == "show_last_errors":
			limit = int(entity) if (entity and entity.isdigit()) else 5
			return dispatch_show_last_errors(self.error_store, limit)

		if intent in {"turn_on_device", "turn_off_device"}:
			return dispatch_light_command(self.error_store, stt_text, intent)
		
		if intent in SHELL_INTENTS:
			return dispatch_shell_command(self.error_store, intent, entity)
		
		response = {
    		"intent": intent,
    		"entity": entity,
    		"command": "No adapter command mapped",
            "tts_text": "I could not map this request to a device action yet.",
		}
		self.error_store.add_command_event(intent, stt_text, response["command"], False)
		return response


	def _extract_room_from_text(text: str) -> str:
		normalized = normalize_phrase(text)
		room_keywords = {
			"kitchen": ["kitchen", "kueche", "kuche"],
			"bathroom": ["bathroom", "bad"],
			"iot": ["iot"],
			"multimedia": ["multimedia", "media", "living room", "wohnzimmer"],
		}

		for room, keywords in room_keywords.items():
			if any(keyword in normalized for keyword in keywords):
				return room

		# Default to multimedia room when no explicit room is spoken.
		return "multimedia"

	def _find_custom_command(self, stt_text: str) -> dict | None:
		normalized_input = normalize_phrase(stt_text)
		relaxed_input = normalize_phrase_relaxed(stt_text)
		for command in load_custom_commands():
			trigger = command.get("trigger", "")
			if normalize_phrase(trigger) == normalized_input:
				return command
			if normalize_phrase_relaxed(trigger) == relaxed_input:
				return command
		return None

	def _render_template(self, template: str, payload: dict) -> str:
		def resolve_path(obj: dict, path: str):
			current = obj
			for part in path.split("."):
				if isinstance(current, dict) and part in current:
					current = current[part]
				else:
					return ""
			return current

		def replacer(match):
			key = match.group(1).strip()
			value = resolve_path(payload, key)
			if value is None:
				return ""
			return str(value)

		return re.sub(r"\{\s*([a-zA-Z0-9_.-]+)\s*\}", replacer, template)

	def _execute_custom_rest(self, action_target: str) -> dict:
		raw = action_target.strip()
		parts = raw.split(maxsplit=1)
		method = "GET"
		url = raw
		if len(parts) == 2 and parts[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
			method = parts[0].upper()
			url = parts[1].strip()

		if method == "GET" and (url == "/api/factory/highbay-stock" or url.endswith("/api/factory/highbay-stock")):
			return get_highbay_stock_payload()

		if url.startswith("/"):
			base_url = os.getenv("ASSISTANT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
			url = f"{base_url}{url}"

		req = urllib_request.Request(url=url, method=method)
		with urllib_request.urlopen(req, timeout=6) as resp:  # nosec B310
			body = resp.read().decode("utf-8", errors="ignore").strip()
			content_type = (resp.headers.get("Content-Type") or "").lower()

		if body:
			should_try_json = "application/json" in content_type or body.startswith("{") or body.startswith("[")
			if should_try_json:
				try:
					parsed = json.loads(body)
					if isinstance(parsed, list):
						return parsed[0] if parsed else {}
					if isinstance(parsed, dict):
						return parsed
				except json.JSONDecodeError:
					pass

		return {"status": body or "ok"}

	def _dispatch_custom_command(self, stt_text: str) -> dict | None:
		command = self._find_custom_command(stt_text)
		if command is None:
			return None

		action_type = command.get("actionType", "REST")
		action_target = command.get("actionTarget", "")
		response_template = command.get("responseTemplate", "Command executed.")

		if action_type == "MQTT":
			payload = {
				"device_name": "MQTT device",
				"status": f"command queued ({action_target})",
			}
			tts_text = self._render_template(response_template, payload).strip() or f"MQTT command queued: {action_target}"
			response = {
				"intent": "custom_command",
				"entity": None,
				"command": f"MQTT: {action_target}",
				"tts_text": tts_text,
			}
			self.error_store.add_command_event("custom_command", stt_text, response["command"], True)
			return response

		try:
			payload = self._execute_custom_rest(action_target)
			tts_text = self._render_template(response_template, payload).strip() or "Command executed successfully."
			response = {
				"intent": "custom_command",
				"entity": None,
				"command": f"REST: {action_target}",
				"tts_text": tts_text,
			}
			self.error_store.add_command_event("custom_command", stt_text, response["command"], True)
			return response
		except Exception as exc:
			payload = {
				"device_name": "Unknown device",
				"status": str(exc),
			}
			tts_text = self._render_template(response_template, payload).strip() or "Failed to execute custom REST command."
			response = {
				"intent": "custom_command",
				"entity": None,
				"command": f"REST: {action_target}",
				"tts_text": tts_text,
			}
			self.error_store.add_command_event("custom_command", stt_text, response["command"], False)
			return response

def dispatch_good_morning(error_store: ErrorStore) -> dict:
	now_str = datetime.now().strftime("%H:%M")
	recent_errors = error_store.list_recent_errors(hours=4)

	if recent_errors:
		sample_errors = recent_errors[:3]
		error_summary = ", ".join(
			f"{item['device']} ({item['reason']})" for item in sample_errors
		)
		tts_text = (
			f"Good Morning Daniil, the time is {now_str}. "
			f"There are several errors in the past hours: {error_summary}."
		)
	else:
		tts_text = f"Good Morning Daniil, the time is {now_str}. There are no errors in the past hours."

	response = {
		"intent": "good_morning",
		"entity": None,
		"command": "SQLITE: greeting + recent errors summary",
		"tts_text": tts_text,
	}
	error_store.add_command_event("good_morning", "N/A", response["command"], True)
	return response

def dispatch_commands_executed_today(error_store: ErrorStore) -> dict:
	command_count = error_store.count_today_commands()
	command_word = "command" if command_count == 1 else "commands"
	response = {
		"intent": "commands_executed_today",
		"entity": None,
		"command": "SQLITE: count today's commands",
		"tts_text": f"{command_count} {command_word} were executed today.",
	}
	error_store.add_command_event("commands_executed_today", "N/A", response["command"], True)
	return response

def dispatch_what_happened_today(error_store: ErrorStore) -> dict:
	today_errors = error_store.list_today_errors()
	command_count = error_store.count_today_commands()
	command_word = "command" if command_count == 1 else "commands"
	error_word = "error" if len(today_errors) == 1 else "errors"
	if today_errors:
		tts_text = (
			f"Today I processed {command_count} {command_word} and detected {len(today_errors)} {error_word}. "
			f"Latest error: {today_errors[0]['device']} - {today_errors[0]['reason']}."
		)
	else:
		tts_text = f"Today I processed {command_count} {command_word} and detected no errors."

	response = {
		"intent": "what_happened_today",
		"entity": None,
		"command": "SQLITE: daily summary query",
		"tts_text": tts_text,
	}
	error_store.add_command_event("what_happened_today", "N/A", response["command"], True)
	return response

def dispatch_show_last_errors(error_store: ErrorStore, limit: int = 5) -> dict:
	errors = error_store.list_last_errors(limit)
	if not errors:
		tts_text = "There are no errors in the backlog."
	else:
		latest = errors[0]
		tts_text = (
			f"I found {len(errors)} recent errors. "
			f"Latest: {latest['device']} with reason {latest['reason']}."
		)

	response = {
		"intent": "show_last_errors",
		"entity": str(limit),
		"command": f"SQLITE: SELECT last {limit} errors",
		"tts_text": tts_text,
	}
	error_store.add_command_event("show_last_errors", f"limit={limit}", response["command"], True)
	return response

def dispatch_identify_error(error_store: ErrorStore) -> dict:
	rest_result = RestAdapter().execute("identify_error", None)
	mqtt_result = MqttAdapter().execute("identify_error", None)

	error_device = next(
		(device for device in rest_result.payload.get("devices", []) if device.get("status") == "error"),
		None,
	)

	if error_device:
		error_reason = error_device.get("reason", "Unknown reason")
		error_event = error_store.add_error(
			device_name=error_device["name"],
			reason=error_reason,
			source_intent="identify_error",
		)
		tts_text = (
			f"Device {error_device['name']} reports an error: {error_reason}. "
			"Saved in backlog."
		)
	else:
		tts_text = "No device errors found."

	command_text = f"{rest_result.command} | {mqtt_result.command}"
	response = {
		"intent": "identify_error",
		"entity": None,
		"command": command_text,
		"tts_text": tts_text,
	}
	if error_device:
		response["error_event"] = error_event
	error_store.add_command_event("identify_error", "N/A", response["command"], True)
	return response

def dispatch_download_logs(error_store: ErrorStore) -> dict:
	response = {
		"intent": "download_logs",
		"entity": None,
		"command": "GET /api/errors/export",
		"tts_text": "Logs are Downloaded",
	}
	error_store.add_command_event("download_logs", "N/A", response["command"], True)
	return response


def dispatch_light_command(error_store: ErrorStore, stt_text: str, intent: str) -> dict:
	state = "ON" if intent == "turn_on_device" else "OFF"
	normalized = normalize_phrase(stt_text)
	if any(keyword in normalized for keyword in ["kitchen", "kueche", "kuche"]):
		room = "kitchen"
	elif any(keyword in normalized for keyword in ["bathroom", "bad"]):
		room = "bathroom"
	elif "iot" in normalized:
		room = "iot"
	else:
		room = "multimedia"

	try:
		result = set_room_lights(room, state)
		tts_text = result.get("status") or f"The {room} lights are {state}."
		response = {
			"intent": intent,
			"entity": room,
			"command": f"REST POST /api/building/room-lights/{room}/{state.lower()}",
			"tts_text": tts_text,
		}
		error_store.add_command_event(intent, stt_text, response["command"], True)
		return response
	except Exception as exc:
		response = {
			"intent": intent,
			"entity": room,
			"command": f"REST POST /api/building/room-lights/{room}/{state.lower()}",
			"tts_text": f"I could not switch the {room} lights {state.lower()}. {exc}",
		}
		error_store.add_command_event(intent, stt_text, response["command"], False)
		return response

def dispatch_shell_command(error_store: ErrorStore, intent: str, entity: str | None) -> dict:
	shell_result = ShellAdapter().execute(intent, entity)
	if shell_result.payload.get("success"):
		if intent == "open_spotify":
			tts_text = "Here, enjoy your Music"
		elif intent == "open_teams":
			tts_text = "Here you go"
		elif intent == "open_outlook":
			tts_text = "Dont Forget to check you Emails"
		else:
			output = shell_result.payload.get("output") or "Command completed successfully"
			tts_text = f"Command {intent} executed. {output}"
	else:
		error = shell_result.payload.get("error") or "Unknown execution error"
		tts_text = f"Command {intent} failed. {error}"

	response = {
		"intent": intent,
		"entity": entity,
		"command": shell_result.command,
		"tts_text": tts_text,
	}
	error_store.add_command_event(
		intent,
		f"entity={entity}",
		response["command"],
		bool(shell_result.payload.get("success")),
	)
	return response

