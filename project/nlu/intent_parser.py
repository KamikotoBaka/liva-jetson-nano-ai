import re
import sqlite3
 
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from text_normalization import normalize_phrase
 
IntentResult = tuple[str, str | None]
Matcher = Callable[[str], bool]

def normalize_text(text: str) -> str:
    return normalize_phrase(text)

def _match(pattern: str, text: str) -> bool:
    """Kurzform für re.search mit is not None."""
    return re.search(pattern, text) is not None
 
 
def _log_unknown_intent(text: str) -> None:
    """
    Speichert nicht erkannte Eingaben in SQLite für spätere Analyse.
    Nützlich für Evaluation und Verbesserung der Intent-Erkennung.
    """
    try:
        db_path = Path("data/liva.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unknown_intents (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                text      TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO unknown_intents (text, timestamp) VALUES (?, ?)",
            (text, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def extract_last_errors_count(normalized: str) -> str | None:
    """
    Extrahiert die Anzahl der letzten Fehler aus dem Text.
    Beispiel: "show last 3 errors" → "3"
    Fallback:  "show last errors"  → "5"
    """
    exact = re.search(r"\blast\s+(\d+)\s+errors?\b", normalized)
    if exact:
        return exact.group(1)
 
    generic = _match(
        r"\b(show|tell|give)\b.*\blast\b.*\berrors?\b", normalized
    )
    if generic:
        return "5"
 
    return None

def match_what_happened_today(text: str) -> bool:
    return _match(r"\bwhat\b.*\bhappened\b.*\btoday\b", text)
 
 
def match_commands_executed_today(text: str) -> bool:
    return _match(
        r"\bhow many\b.*\b(commands?|actions?)\b.*\b(executed|run|processed)\b.*\btoday\b",
        text,
    )
 
 
def match_good_morning(text: str) -> bool:
    return _match(r"\bgood\s*morning\b", text)
 
def match_check_disk(text: str) -> bool:
    return _match(r"\b(check|show)\b.{0,20}\b(disk|storage)\b", text)
 
 
def match_check_memory(text: str) -> bool:
    return _match(r"\b(check|show)\b.{0,20}\b(memory|ram)\b", text)
 
 
def match_check_time(text: str) -> bool:
    return (
        _match(r"\b(what|check|tell)\b.{0,20}\btime\b", text)
        or _match(r"\bcurrent\s*time\b", text)
    )
 
 
def match_check_date(text: str) -> bool:
    return (
        _match(r"\b(what|check|tell)\b.{0,20}\bdate\b", text)
        or _match(r"\btoday('?s)?\s*date\b", text)
    )
 
 
def match_check_uptime(text: str) -> bool:
    return _match(r"\b(check|show|what)\b.{0,20}\buptime\b", text)
 
 
def match_check_hostname(text: str) -> bool:
    return _match(
        r"\b(check|show|what)\b.{0,20}\b(hostname|computer\s*name|machine\s*name)\b",
        text,
    )
 
def match_restart_apache(text: str) -> bool:
    return _match(r"\b(reload|restart)\b.{0,20}\b(apache|apache\s*server)\b", text)
 
 
def match_stop_apache(text: str) -> bool:
    return _match(r"\bstop\b.{0,20}\b(apache|apache\s*server)\b", text)
 
 
def match_restart_nginx(text: str) -> bool:
    return _match(r"\b(reload|restart)\b.{0,20}\bnginx\b", text)
 
 
def match_system_status(text: str) -> bool:
    return _match(r"\b(system|service)\b.{0,20}\bstatus\b", text)
 
def match_open_spotify(text: str) -> bool:
    return _match(r"\b(open|start|launch)\b.{0,20}\bspotify\b", text)
 
 
def match_open_outlook(text: str) -> bool:
    return _match(r"\b(open|start|launch)\b.{0,20}\boutlook\b", text)
 
 
def match_open_teams(text: str) -> bool:
    return _match(r"\b(open|start|launch)\b.{0,20}\b(teams|teems)\b", text)
 
def match_download_logs(text: str) -> bool:
    return _match(
        r"\b(download|export|save)\b.{0,30}\b(data\s*log|datalog|logs?|log\s*file)\b",
        text,
    )

def match_identify_error(text: str) -> bool:
    return _match(r"\b(identify|find)\b.{0,20}\b(error|fault|issue)\b", text)

def match_turn_on_device(text: str) -> bool:
    if _match(r"\b(apache|nginx|spotify|outlook|teams)\b", text):
        return False
    return _match(r"\b(turn\s*on|enable)\b", text)
 
 
def match_turn_off_device(text: str) -> bool:
    if _match(r"\b(apache|nginx|spotify|outlook|teams)\b", text):
        return False
    return _match(r"\b(turn\s*off|disable)\b", text)

INTENT_PATTERNS: list[tuple[str, Matcher]] = [
    ("what_happened_today",     match_what_happened_today),
    ("commands_executed_today", match_commands_executed_today),
    ("good_morning",            match_good_morning),
    ("check_disk",              match_check_disk),
    ("check_memory",            match_check_memory),
    ("check_time",              match_check_time),
    ("check_date",              match_check_date),
    ("check_uptime",            match_check_uptime),
    ("check_hostname",          match_check_hostname),
    ("system_status",           match_system_status),
    ("restart_apache",          match_restart_apache),
    ("stop_apache",             match_stop_apache),
    ("restart_nginx",           match_restart_nginx),
    ("open_spotify",            match_open_spotify),
    ("open_outlook",            match_open_outlook),
    ("open_teams",              match_open_teams),
    ("download_logs",           match_download_logs),
    ("identify_error",          match_identify_error),
    ("turn_on_device",          match_turn_on_device),
    ("turn_off_device",         match_turn_off_device),
]
 
 
# ── Haupt-Funktion ────────────────────────────────────────────────────────────
 
def parse_intent(text: str) -> IntentResult:
    normalized = normalize_text(text)

    amount = extract_last_errors_count(normalized)
    if amount is not None:
        return "show_last_errors", amount
    for intent, matcher in INTENT_PATTERNS:
        if matcher(normalized):
            return intent, None

    _log_unknown_intent(normalized)
    return "unknown", None