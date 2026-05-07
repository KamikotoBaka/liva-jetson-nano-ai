from __future__ import annotations

import json
from pathlib import Path
from text_normalization import normalize_phrase

CUSTOM_COMMANDS_PATH = Path(__file__).resolve().parent / "data" / "custom_commands.json"
ALLOWED_ACTION_TYPES = {"REST", "MQTT"}
DEFAULT_CUSTOM_COMMANDS = [
    {
        "trigger": "Check the warehouse",
        "category": "Factory",
        "actionType": "REST",
        "actionTarget": "GET /api/factory/highbay-stock",
        "responseTemplate": "High-bay has {stock.occupiedSlots} of {stock.totalSlots} slots occupied. Free: {stock.freeSlots}. Occupied locations: {stock.occupiedLocations}",
    },
    {
        "trigger": "Order blue workpiece",
        "category": "Factory",
        "actionType": "REST",
        "actionTarget": "GET /api/factory/order-workpiece/BLUE",
        "responseTemplate": "I Ordered a blue workpiece.",
    },
    {
        "trigger": "Order red workpiece",
        "category": "Factory",
        "actionType": "REST",
        "actionTarget": "GET /api/factory/order-workpiece/RED",
        "responseTemplate": "I Ordered a red workpiece.",
    },
    {
        "trigger": "Order white workpiece",
        "category": "Factory",
        "actionType": "REST",
        "actionTarget": "GET /api/factory/order-workpiece/WHITE",
        "responseTemplate": "I Ordered a white workpiece.",
    },
    {
        "trigger": "Turn on multimedia room lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/multimedia-lights/ON",
        "responseTemplate": "The Multimedia Lights are On.",
    },
    {
        "trigger": "Turn off multimedia room lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/multimedia-lights/OFF",
        "responseTemplate": "The Multimedia Lights are Off.",
    },
    {
        "trigger": "Turn on kitchen lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/kitchen-lights/ON",
        "responseTemplate": "The Kitchen Lights are On.",
    },
    {
        "trigger": "Turn off kitchen lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/kitchen-lights/OFF",
        "responseTemplate": "The Kitchen Lights are Off.",
    },
    {
        "trigger": "Turn on bathroom lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/bathroom-lights/ON",
        "responseTemplate": "The Bathroom Lights are On.",
    },
    {
        "trigger": "Turn off bathroom lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/bathroom-lights/OFF",
        "responseTemplate": "The Bathroom Lights are Off.",
    },
    {
        "trigger": "Turn on iot room lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/iot-lights/ON",
        "responseTemplate": "The IoT Room Lights are On.",
    },
    {
        "trigger": "Turn off iot room lights",
        "category": "Building",
        "actionType": "REST",
        "actionTarget": "GET /api/building/iot-lights/OFF",
        "responseTemplate": "The IoT Room Lights are Off.",
    },
    {
        "trigger": "Check temperature and air quality",
        "category": "Factory",
        "actionType": "REST",
        "actionTarget": "GET /api/factory/bme680-data",
        "responseTemplate": "Current temperature is {data.temperature} degrees. Air quality index is {data.airQuality}.",
    },
]


def sanitize_command(item: dict) -> dict:
    action_type = str(item.get("actionType", "REST")).upper()
    if action_type not in ALLOWED_ACTION_TYPES:
        action_type = "REST"

    return {
        "trigger": str(item.get("trigger", "")).strip(),
        "category": str(item.get("category", "General")).strip() or "General",
        "actionType": action_type,
        "actionTarget": str(item.get("actionTarget", "")).strip(),
        "responseTemplate": str(item.get("responseTemplate", "")).strip()
        or "Command executed.",
    }


def sanitize_commands(items: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    seen: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            continue

        command = sanitize_command(raw)
        if not command["trigger"] or not command["actionTarget"]:
            continue

        key = normalize_phrase(command["trigger"])
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(command)

    return cleaned


def merge_default_commands(items: list[dict]) -> list[dict]:
    merged = list(items)
    existing = {normalize_phrase(item.get("trigger", "")) for item in merged}

    for default_item in sanitize_commands(DEFAULT_CUSTOM_COMMANDS):
        key = normalize_phrase(default_item.get("trigger", ""))
        if key in existing:
            continue
        merged.append(default_item)
        existing.add(key)

    return merged


def load_custom_commands(path: Path | None = None) -> list[dict]:
    active_path = path or CUSTOM_COMMANDS_PATH
    if not active_path.exists():
        defaults = merge_default_commands([])
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
        return defaults

    try:
        raw = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw, list):
        return []

    return merge_default_commands(sanitize_commands(raw))


def save_custom_commands(items: list[dict], path: Path | None = None) -> list[dict]:
    active_path = path or CUSTOM_COMMANDS_PATH
    active_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = merge_default_commands(sanitize_commands(items))
    active_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    return cleaned
