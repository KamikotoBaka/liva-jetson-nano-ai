from __future__ import annotations

import json
import os
from datetime import datetime
from threading import Lock

import paho.mqtt.client as mqtt


class HighBayStockService:
    def __init__(self) -> None:
        self.host = os.getenv("FISCHER_MQTT_HOST", "localhost")
        self.port = int(os.getenv("FISCHER_MQTT_PORT", "18830"))
        self.topic = os.getenv("FISCHER_MQTT_STOCK_TOPIC", "f/i/stock")

        self._connected = False
        self._last_error: str | None = None
        self._latest_payload: dict | None = None
        self._last_message_at: str | None = None
        self._lock = Lock()

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        with self._lock:
            self._connected = reason_code == 0
            if reason_code != 0:
                self._last_error = f"MQTT connect failed with code {reason_code}"
                return
            self._last_error = None

        client.subscribe(self.topic)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        with self._lock:
            self._connected = False
            if reason_code != 0:
                self._last_error = f"MQTT disconnected with code {reason_code}"

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                return
        except Exception:
            return

        with self._lock:
            self._latest_payload = payload
            self._last_message_at = datetime.now().isoformat()

    def start(self) -> None:
        try:
            self._client.connect(self.host, self.port, keepalive=60)
            self._client.loop_start()
            with self._lock:
                self._last_error = None
        except Exception as exc:
            with self._lock:
                self._connected = False
                self._last_error = str(exc)

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass

    def status(self) -> dict:
        with self._lock:
            return {
                "connected": self._connected,
                "host": self.host,
                "port": self.port,
                "topic": self.topic,
                "lastError": self._last_error,
                "lastMessageAt": self._last_message_at,
            }

    def latest_summary(self) -> dict:
        with self._lock:
            payload = self._latest_payload.copy() if isinstance(self._latest_payload, dict) else None
            last_message_at = self._last_message_at

        if payload is None:
            return {
                "available": False,
                "updatedAt": last_message_at,
                "totalSlots": 0,
                "occupiedSlots": 0,
                "freeSlots": 0,
                "occupiedLocations": "",
                "occupiedItems": "",
                "stockItems": [],
            }

        items = payload.get("stockItems")
        if not isinstance(items, list):
            items = []

        occupied = []
        for item in items:
            if not isinstance(item, dict):
                continue
            location = str(item.get("location", ""))
            workpiece = item.get("workpiece")
            if not isinstance(workpiece, dict):
                continue
            occupied.append(
                {
                    "location": location,
                    "type": str(workpiece.get("type", "")),
                    "id": str(workpiece.get("id", "")),
                    "state": str(workpiece.get("state", "")),
                }
            )

        occupied_locations = [item["location"] for item in occupied if item["location"]]
        occupied_items = [
            f"{item['location']}:{item['type']}:{item['state']}".strip(":")
            for item in occupied
        ]

        total_slots = len(items)
        occupied_slots = len(occupied)

        return {
            "available": True,
            "updatedAt": payload.get("ts") or last_message_at,
            "totalSlots": total_slots,
            "occupiedSlots": occupied_slots,
            "freeSlots": max(0, total_slots - occupied_slots),
            "occupiedLocations": ", ".join(occupied_locations),
            "occupiedItems": ", ".join(occupied_items),
            "stockItems": items,
        }


_SERVICE_INSTANCE: HighBayStockService | None = None


def get_highbay_stock_service() -> HighBayStockService:
    global _SERVICE_INSTANCE
    if _SERVICE_INSTANCE is None:
        _SERVICE_INSTANCE = HighBayStockService()
    return _SERVICE_INSTANCE


def get_highbay_stock_payload() -> dict:
    service = get_highbay_stock_service()
    return {
        "mqtt": service.status(),
        "stock": service.latest_summary(),
    }
