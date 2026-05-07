from __future__ import annotations

import os
from datetime import datetime
from urllib import request as urllib_request

ROOM_TO_ITEM = {
    "multimedia": "iMultimedia_Hue_Lampen_Schalter",
    "kitchen": "iKueche_Hue_Lampen_Schalter",
    "bathroom": "iBad_Hue_Lampen_Schalter",
    "iot": "iIoT_Hue_Lampen_Schalter",
}


def _resolve_item_name_for_room(room: str) -> str:
    normalized_room = str(room).strip().lower()
    if normalized_room not in ROOM_TO_ITEM:
        raise RuntimeError(f"Unsupported room: {room}")

    env_key = f"OPENHAB_{normalized_room.upper()}_LIGHT_ITEM"
    return os.getenv(env_key, ROOM_TO_ITEM[normalized_room]).strip()


def set_room_lights(room: str, state: str) -> dict:
    normalized_room = str(room).strip().lower()
    if normalized_room not in ROOM_TO_ITEM:
        raise RuntimeError(f"Unsupported room: {room}")

    normalized_state = str(state).strip().upper()
    if normalized_state not in {"ON", "OFF"}:
        raise RuntimeError("Light state must be ON or OFF")

    base_url = os.getenv("OPENHAB_BASE_URL", "http://192.168.0.5:8080").rstrip("/")
    item_name = _resolve_item_name_for_room(normalized_room)
    endpoint = f"{base_url}/rest/items/{item_name}"

    body = normalized_state.encode("utf-8")
    req = urllib_request.Request(
        url=endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "text/plain"},
    )

    try:
        with urllib_request.urlopen(req, timeout=5) as response:  # nosec B310
            status_code = response.getcode()
    except Exception as exc:
        raise RuntimeError(f"Failed to control {normalized_room} lights: {exc}") from exc

    room_label = normalized_room.capitalize()
    return {
        "ok": True,
        "room": normalized_room,
        "state": normalized_state,
        "status": f"The {room_label} Lights are {normalized_state}.",
        "endpoint": endpoint,
        "httpStatus": status_code,
        "changedAt": datetime.now().isoformat(),
    }


def set_multimedia_room_lights(state: str) -> dict:
    return set_room_lights("multimedia", state)
