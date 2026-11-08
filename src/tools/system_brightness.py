"""Display brightness control tool using screen_brightness_control."""

import logging
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


class SystemBrightnessTool(BaseTool):
    """Controls screen brightness on supported monitors."""

    name = "control_system_brightness"
    description = (
        "Ekranın (monitörün) parlaklık seviyesini ayarlar, artırır/azaltır veya "
        "mevcut parlaklık seviyesini okur."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "description": "Parlaklık eylemi: 'set_brightness', 'change_brightness', 'get_brightness'",
                        "enum": ["set_brightness", "change_brightness", "get_brightness"]
                    },
                    "level": {
                        "type": "INTEGER",
                        "description": "0 ile 100 arasında hedef parlaklık yüzdesi (set_brightness için zorunlu)."
                    },
                    "delta": {
                        "type": "INTEGER",
                        "description": "Parlaklık artırma (+) veya azaltma (-) miktarı (change_brightness için)."
                    }
                },
                "required": ["action"]
            }
        }

    def _get_current_brightness(self) -> int:
        """Helper to get current primary brightness percentage."""
        import screen_brightness_control as sbc
        current = sbc.get_brightness()
        if isinstance(current, list):
            if not current:
                raise RuntimeError("Monitör parlaklık bilgisi alınamadı.")
            return int(current[0])
        return int(current)

    def _set_brightness(self, level: int) -> None:
        """Helper to set brightness."""
        import screen_brightness_control as sbc
        sbc.set_brightness(level)

    def execute(
        self,
        action: str,
        level: Optional[int] = None,
        delta: Optional[int] = None,
        **kwargs: Any
    ) -> ToolResult:
        try:
            if action == "set_brightness":
                if level is None:
                    return ToolResult(
                        success=False,
                        message="Parlaklığı ayarlamak için 0 ile 100 arasında bir seviye belirtmelisiniz efendim."
                    )
                clamped = max(0, min(100, int(level)))
                self._set_brightness(clamped)
                return ToolResult(
                    success=True,
                    message=f"Ekran parlaklığı %{clamped} olarak ayarlandı efendim.",
                    data={"brightness": clamped}
                )

            elif action == "change_brightness":
                if delta is None:
                    return ToolResult(
                        success=False,
                        message="Parlaklığı değiştirmek için artış veya azalış miktarını belirtmelisiniz efendim."
                    )
                current = self._get_current_brightness()
                new_val = max(0, min(100, current + int(delta)))
                self._set_brightness(new_val)
                return ToolResult(
                    success=True,
                    message=f"Ekran parlaklığı %{new_val} seviyesine getirildi efendim.",
                    data={"brightness": new_val}
                )

            elif action == "get_brightness":
                current = self._get_current_brightness()
                return ToolResult(
                    success=True,
                    message=f"Mevcut ekran parlaklığı %{current} efendim.",
                    data={"brightness": current}
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen parlaklık eylemi: '{action}' efendim."
                )

        except Exception as e:
            logger.warning(f"SystemBrightnessTool hatası: {e}")
            return ToolResult(
                success=False,
                message="Efendim, bağlı monitörünüz yazılımsal parlaklık kontrolünü desteklemiyor veya izin vermiyor."
            )
