import csv
import io
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


class ErrorStore:
    def __init__(self, db_path: str | None = None) -> None:
        default_path = Path(__file__).resolve().parent / "data" / "error_events.db"
        self.db_path = Path(db_path) if db_path else default_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_json_path = self.db_path.parent / "error_events.json"
        self._init_db()
        self._migrate_legacy_json()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS error_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    device TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    intent TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    command_text TEXT NOT NULL,
                    success INTEGER NOT NULL
                )
                """
            )
            connection.commit()

    def _has_rows(self) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("SELECT COUNT(1) FROM error_events")
            count = cursor.fetchone()[0]
            return count > 0

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_json_path.exists() or self._has_rows():
            return

        try:
            events = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        if not isinstance(events, list):
            return

        with self._connect() as connection:
            for event in events:
                if not isinstance(event, dict):
                    continue

                event_id = str(event.get("id") or uuid.uuid4())
                timestamp = str(event.get("timestamp") or datetime.now(timezone.utc).isoformat())
                device = str(event.get("device") or "unknown")
                reason = str(event.get("reason") or "unknown")
                intent = str(event.get("intent") or "identify_error")

                connection.execute(
                    """
                    INSERT OR IGNORE INTO error_events (id, timestamp, device, reason, intent)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (event_id, timestamp, device, reason, intent),
                )
            connection.commit()

    def add_error(self, device_name: str, reason: str, source_intent: str) -> dict:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device": device_name,
            "reason": reason,
            "intent": source_intent,
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO error_events (id, timestamp, device, reason, intent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event["id"], event["timestamp"], event["device"], event["reason"], event["intent"]),
            )
            connection.commit()

        return event

    def add_command_event(self, intent: str, transcript: str, command_text: str, success: bool) -> dict:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "transcript": transcript,
            "command_text": command_text,
            "success": 1 if success else 0,
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO command_events (id, timestamp, intent, transcript, command_text, success)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["timestamp"],
                    event["intent"],
                    event["transcript"],
                    event["command_text"],
                    event["success"],
                ),
            )
            connection.commit()

        return event

    def list_errors(self) -> list[dict]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, timestamp, device, reason, intent
                FROM error_events
                ORDER BY timestamp DESC
                """
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "device": row[2],
                "reason": row[3],
                "intent": row[4],
            }
            for row in rows
        ]

    def list_last_errors(self, limit: int = 5) -> list[dict]:
        safe_limit = max(1, min(limit, 50))
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, timestamp, device, reason, intent
                FROM error_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (safe_limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "device": row[2],
                "reason": row[3],
                "intent": row[4],
            }
            for row in rows
        ]

    def list_today_errors(self) -> list[dict]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, timestamp, device, reason, intent
                FROM error_events
                WHERE date(timestamp) = date('now')
                ORDER BY timestamp DESC
                """
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "device": row[2],
                "reason": row[3],
                "intent": row[4],
            }
            for row in rows
        ]

    def list_recent_errors(self, hours: int = 4) -> list[dict]:
        safe_hours = max(1, min(hours, 168))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=safe_hours)
        recent_errors: list[dict] = []

        for event in self.list_errors():
            raw_timestamp = event.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(raw_timestamp)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            if timestamp >= cutoff:
                recent_errors.append(event)

        return recent_errors

    def count_today_commands(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT COUNT(1)
                FROM command_events
                WHERE date(timestamp) = date('now')
                """
            )
            return int(cursor.fetchone()[0])

    def delete_error(self, event_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM error_events WHERE id = ?", (event_id,))
            connection.commit()
            return cursor.rowcount > 0

    def export_csv(self) -> str:
        events = self.list_errors()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "timestamp", "device", "reason", "intent"])
        for event in events:
            writer.writerow([
                event["id"],
                event["timestamp"],
                event["device"],
                event["reason"],
                event["intent"],
            ])
        return buffer.getvalue()
