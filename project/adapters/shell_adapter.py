import platform
import subprocess
from pathlib import Path

import yaml
from adapters.base_adapter import AdapterExecutionResult, BaseAdapter


ALLOWED_COMMANDS_BY_OS: dict[str, dict[str, list[str]]] = {
    "linux": {
        "restart_apache": ["systemctl", "restart", "apache2"],
        "stop_apache": ["systemctl", "stop", "apache2"],
        "restart_nginx": ["systemctl", "restart", "nginx"],
        "system_status": ["systemctl", "status", "apache2"],
        "check_disk": ["df", "-h"],
        "check_memory": ["free", "-h"],
        "check_time": ["date", "+%H:%M:%S"],
        "check_date": ["date", "+%Y-%m-%d"],
        "check_uptime": ["uptime", "-p"],
        "check_hostname": ["hostname"],
        "open_spotify": ["xdg-open", "spotify:"],
        "open_outlook": ["xdg-open", "https://outlook.office.com"],
        "open_teams": ["xdg-open", "https://teams.microsoft.com"],
    },
    "windows": {
        "restart_apache": ["powershell", "-NoProfile", "-Command", "Restart-Service -Name Apache2.4"],
        "stop_apache": ["powershell", "-NoProfile", "-Command", "Stop-Service -Name Apache2.4"],
        "restart_nginx": ["powershell", "-NoProfile", "-Command", "Restart-Service -Name nginx"],
        "system_status": ["powershell", "-NoProfile", "-Command", "Get-Service -Name Apache2.4"],
        "check_disk": [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free",
        ],
        "check_memory": [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory",
        ],
        "check_time": ["powershell", "-NoProfile", "-Command", "Get-Date -Format HH:mm:ss"],
        "check_date": ["powershell", "-NoProfile", "-Command", "Get-Date -Format yyyy-MM-dd"],
        "check_uptime": [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime",
        ],
        "check_hostname": ["powershell", "-NoProfile", "-Command", "$env:COMPUTERNAME"],
        "open_spotify": ["powershell", "-NoProfile", "-Command", "Start-Process 'spotify:'"],
        "open_outlook": [
            "powershell",
            "-NoProfile",
            "-Command",
            "$fixed = 'C:\\Program Files\\Microsoft Office\\Root\\Office16\\OUTLOOK.EXE'; if (Test-Path $fixed) { Start-Process $fixed; exit 0 }; $exe = $null; if (Get-Command outlook.exe -ErrorAction SilentlyContinue) { $exe = (Get-Command outlook.exe).Source }; if ($exe) { Start-Process $exe; exit 0 }; $candidates = @('$env:ProgramFiles\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE','$env:ProgramFiles(x86)\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE','$env:ProgramFiles\\Microsoft Office\\Office16\\OUTLOOK.EXE','$env:ProgramFiles(x86)\\Microsoft Office\\Office16\\OUTLOOK.EXE'); foreach ($p in $candidates) { $expanded = [Environment]::ExpandEnvironmentVariables($p); if (Test-Path $expanded) { Start-Process $expanded; exit 0 } }; Write-Error 'Outlook Classic executable not found'; exit 1",
        ],
        "open_teams": [
            "powershell",
            "-NoProfile",
            "-Command",
            "if (Get-Command ms-teams.exe -ErrorAction SilentlyContinue) { Start-Process ms-teams.exe } else { Start-Process 'msteams:' }",
        ],
    },
}


SHELL_INTENTS = {
    "restart_apache",
    "stop_apache",
    "restart_nginx",
    "system_status",
    "check_disk",
    "check_memory",
    "check_time",
    "check_date",
    "check_uptime",
    "check_hostname",
    "open_spotify",
    "open_outlook",
    "open_teams",
}


class ShellAdapter(BaseAdapter):
    def __init__(self, timeout_seconds: int = 10, config_path: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.os_name = platform.system().lower()
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "config" / "devices.yaml"

    def _get_allowed_commands(self) -> dict[str, list[str]]:
        configured_commands = self._load_commands_from_config()
        if configured_commands:
            return configured_commands

        if self.os_name.startswith("win"):
            return ALLOWED_COMMANDS_BY_OS["windows"]
        return ALLOWED_COMMANDS_BY_OS["linux"]

    def _load_commands_from_config(self) -> dict[str, list[str]]:
        if not self.config_path.exists():
            return {}

        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
        except (yaml.YAMLError, OSError):
            return {}

        shell_commands = config.get("shell_commands", {})
        key = "windows" if self.os_name.startswith("win") else "linux"
        os_commands = shell_commands.get(key, {})

        filtered: dict[str, list[str]] = {}
        for intent, command in os_commands.items():
            if isinstance(intent, str) and isinstance(command, list) and all(isinstance(part, str) for part in command):
                filtered[intent] = command
        return filtered

    def execute_system_command(self, command: list[str]) -> dict:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out",
                "returncode": -1,
            }
        except FileNotFoundError as exc:
            return {
                "success": False,
                "output": "",
                "error": str(exc),
                "returncode": -1,
            }

    def execute(self, intent: str, entity: str | None = None) -> AdapterExecutionResult:
        allowed_commands = self._get_allowed_commands()
        if intent not in allowed_commands:
            return AdapterExecutionResult(
                command="",
                payload={"success": False, "error": "Command is not allowed", "output": "", "returncode": -1},
            )

        command = allowed_commands[intent]
        result = self.execute_system_command(command)
        return AdapterExecutionResult(command=" ".join(command), payload=result)