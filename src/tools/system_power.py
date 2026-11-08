"""System power control tool (shutdown, restart, sleep) with confirmation policy."""

import logging
import subprocess
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


class SystemPowerTool(BaseTool):
    """Controls system power states: shutdown, restart, and sleep.
    
    Always requires confirmation before execution to prevent accidental shutdown.
    """

    name = "control_system_power"
    description = (
        "Bilgisayarı kapatır, yeniden başlatır veya uyku moduna alır. "
        "Güvenlik gereği her zaman kullanıcıdan sesli onay ister."
    )
    confirmation_policy = ConfirmationPolicy.REQUIRE_CONFIRMATION

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "description": "Güç eylemi: 'shutdown' (kapat), 'restart' (yeniden başlat), 'sleep' (uyku)",
                        "enum": ["shutdown", "restart", "sleep"]
                    }
                },
                "required": ["action"]
            }
        }

    def _execute_power_command(self, action: str) -> None:
        """Helper to invoke system shutdown commands."""
        if action == "shutdown":
            subprocess.Popen(["shutdown", "/s", "/t", "5"])
        elif action == "restart":
            subprocess.Popen(["shutdown", "/r", "/t", "5"])
        elif action == "sleep":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

    def execute(self, action: str, **kwargs: Any) -> ToolResult:
        try:
            if action == "shutdown":
                self._execute_power_command("shutdown")
                return ToolResult(
                    success=True,
                    message="Bilgisayarınız kapatılıyor efendim. Görüşmek üzere.",
                    data={"action": "shutdown"}
                )
            elif action == "restart":
                self._execute_power_command("restart")
                return ToolResult(
                    success=True,
                    message="Bilgisayarınız yeniden başlatılıyor efendim.",
                    data={"action": "restart"}
                )
            elif action == "sleep":
                self._execute_power_command("sleep")
                return ToolResult(
                    success=True,
                    message="Bilgisayarınız uyku moduna alınıyor efendim.",
                    data={"action": "sleep"}
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen sistem gücü eylemi: '{action}' efendim."
                )
        except Exception as e:
            logger.error(f"SystemPowerTool hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Güç işlemi gerçekleştirilirken bir hata oluştu efendim: {str(e)}"
            )
