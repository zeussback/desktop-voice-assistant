"""System audio control tool using pycaw."""

import logging
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


class SystemAudioTool(BaseTool):
    """Controls Windows master volume and mute state."""

    name = "control_system_audio"
    description = (
        "Bilgisayarın ana hoparlör ses düzeyini ayarlar, artırır/azaltır, "
        "mevcut seviyeyi okur veya sesi susturur/açar (mute/unmute)."
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
                        "description": "Yapılacak eylem: 'set_volume', 'change_volume', 'get_volume', 'mute', 'unmute'",
                        "enum": ["set_volume", "change_volume", "get_volume", "mute", "unmute"]
                    },
                    "level": {
                        "type": "INTEGER",
                        "description": "0 ile 100 arasında hedef ses seviyesi (set_volume için zorunlu)."
                    },
                    "delta": {
                        "type": "INTEGER",
                        "description": "Ses seviyesi artırma (+) veya azaltma (-) miktarı (change_volume için)."
                    }
                },
                "required": ["action"]
            }
        }

    def _get_endpoint_volume(self):
        """Helper to get pycaw EndpointVolume."""
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        if not device:
            raise RuntimeError("Hoparlör aygıtı bulunamadı.")
        return device.EndpointVolume

    def execute(
        self,
        action: str,
        level: Optional[int] = None,
        delta: Optional[int] = None,
        **kwargs: Any
    ) -> ToolResult:
        import comtypes
        comtypes.CoInitialize()
        try:
            vol = self._get_endpoint_volume()

            if action == "set_volume":
                if level is None:
                    return ToolResult(
                        success=False,
                        message="Ses düzeyini ayarlamak için bir seviye (0-100) belirtmelisiniz efendim."
                    )
                clamped = max(0, min(100, int(level)))
                vol.SetMasterVolumeLevelScalar(clamped / 100.0, None)
                if vol.GetMute():
                    vol.SetMute(0, None)
                return ToolResult(
                    success=True,
                    message=f"Ses düzeyi %{clamped} olarak ayarlandı efendim.",
                    data={"volume": clamped}
                )

            elif action == "change_volume":
                if delta is None:
                    return ToolResult(
                        success=False,
                        message="Ses düzeyini değiştirmek için artış veya azalış miktarını belirtmelisiniz efendim."
                    )
                current_scalar = vol.GetMasterVolumeLevelScalar()
                current_percent = round(current_scalar * 100)
                new_percent = max(0, min(100, current_percent + int(delta)))
                vol.SetMasterVolumeLevelScalar(new_percent / 100.0, None)
                if vol.GetMute() and new_percent > 0:
                    vol.SetMute(0, None)
                return ToolResult(
                    success=True,
                    message=f"Ses düzeyi %{new_percent} seviyesine getirildi efendim.",
                    data={"volume": new_percent}
                )

            elif action == "get_volume":
                scalar = vol.GetMasterVolumeLevelScalar()
                percent = round(scalar * 100)
                is_muted = bool(vol.GetMute())
                mute_str = " (Sessize alınmış durumda)" if is_muted else ""
                return ToolResult(
                    success=True,
                    message=f"Mevcut ses düzeyi %{percent}{mute_str} efendim.",
                    data={"volume": percent, "is_muted": is_muted}
                )

            elif action == "mute":
                vol.SetMute(1, None)
                return ToolResult(
                    success=True,
                    message="Ses kapatıldı efendim.",
                    data={"is_muted": True}
                )

            elif action == "unmute":
                vol.SetMute(0, None)
                scalar = vol.GetMasterVolumeLevelScalar()
                percent = round(scalar * 100)
                return ToolResult(
                    success=True,
                    message=f"Ses açıldı efendim. Seviye %{percent}.",
                    data={"is_muted": False, "volume": percent}
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"Geçersiz ses eylemi: '{action}' efendim."
                )

        except Exception as e:
            logger.error(f"SystemAudioTool hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Ses ayarı değiştirilirken bir hata oluştu efendim: {str(e)}"
            )
        finally:
            comtypes.CoUninitialize()
