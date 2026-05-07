from __future__ import annotations

import json
import os
from datetime import datetime
from threading import Lock

import paho.mqtt.client as mqtt


class BME680Service:
    def __init__(self) -> None:
        self.host = os.getenv("FISCHER_MQTT_HOST", "localhost")
        self.port = int(os.getenv("FISCHER_MQTT_PORT", "18830"))
        self.topic = os.getenv("BME680_MQTT_TOPIC", "i/bme680")

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

    def latest_data(self) -> dict:
        """
        Returns the latest sensor data in a friendly format.
        """
        with self._lock:
            payload = self._latest_payload.copy() if isinstance(self._latest_payload, dict) else None
            last_message_at = self._last_message_at

        if payload is None:
            return {
                "available": False,
                "updatedAt": last_message_at,
                "temperature": None,
                "humidity": None,
                "pressure": None,
                "airQuality": None,
                "airQualityLevel": None,
                "gasResistance": None,
            }

        return {
            "available": True,
            "updatedAt": payload.get("ts") or last_message_at,
            "temperature": payload.get("t"),
            "humidity": payload.get("h"),
            "pressure": payload.get("p"),
            "airQuality": payload.get("iaq"),
            "airQualityLevel": payload.get("aq"),
            "gasResistance": payload.get("gr"),
        }


_SERVICE_INSTANCE: BME680Service | None = None


def get_bme680_service() -> BME680Service:
    global _SERVICE_INSTANCE
    if _SERVICE_INSTANCE is None:
        _SERVICE_INSTANCE = BME680Service()
    return _SERVICE_INSTANCE


def get_bme680_data_payload() -> dict:
    service = get_bme680_service()
    return {
        "mqtt": service.status(),
        "data": service.latest_data(),
    }
