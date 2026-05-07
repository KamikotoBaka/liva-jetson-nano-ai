from __future__ import annotations

import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt


ALLOWED_WORKPIECE_TYPES = {"RED", "BLUE", "WHITE"}


def publish_workpiece_order(workpiece_type: str) -> dict:
    normalized_type = str(workpiece_type).strip().upper()
    if normalized_type not in ALLOWED_WORKPIECE_TYPES:
        raise RuntimeError(f"Unsupported workpiece type: {workpiece_type}")

    host = os.getenv("FISCHER_MQTT_HOST", "localhost")
    port = int(os.getenv("FISCHER_MQTT_ORDER_PORT", "18830"))
    topic = os.getenv("FISCHER_MQTT_ORDER_TOPIC", "f/o/order")

    payload = {"type": normalized_type}
    payload_text = json.dumps(payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(host, port, keepalive=30)
        result = client.publish(topic, payload=payload_text, qos=0, retain=False)
        result.wait_for_publish(timeout=3)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with code {result.rc}")

        return {
            "ok": True,
            "workpieceType": normalized_type,
            "topic": topic,
            "host": host,
            "port": port,
            "publishedAt": datetime.now().isoformat(),
            "status": f"Order for {normalized_type} workpiece sent.",
        }
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
