"""Media playback control tool using Windows virtual keys."""

import ctypes
import logging
import time
from typing import Any, Dict
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)

# Windows Virtual Key Codes
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def _send_media_key(vk_code: int) -> None:
    """Simulate key press and release for a virtual key code."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


class MediaControlTool(BaseTool):
    """Controls Windows media playback (Play/Pause, Next, Previous, Stop)."""

    name = "control_media"
    description = (
        "Bilgisayarda çalan veya duraklatılmış medyayı (müzik, video, Spotify, YouTube vb.) kontrol eder. "
        "Müziği başlatmak, çalmak, durdurmak, duraklatmak, devam ettirmek (play/pause), sonraki/önceki parçaya geçmek için bu aracı kullan. "
        "ÖNEMLİ: Kullanıcı 'müziği başlat', 'müziği aç', 'müzik çal', 'şarkıyı aç', 'müziği durdur', 'müziği duraklat' dediğinde "
        "uygulama açma aracı yerine MUTLAKA bu 'control_media' aracını (action='play_pause') kullanmalısın."
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
                        "description": "Medya kontrol eylemi: 'play_pause', 'next_track', 'previous_track', 'stop'",
                        "enum": ["play_pause", "next_track", "previous_track", "stop"]
                    }
                },
                "required": ["action"]
            }
        }

    def execute(self, action: str, **kwargs: Any) -> ToolResult:
        try:
            if action == "play_pause":
                _send_media_key(VK_MEDIA_PLAY_PAUSE)
                return ToolResult(
                    success=True,
                    message="Medya durumu değiştirildi efendim.",
                    data={"action": action}
                )
            elif action == "next_track":
                _send_media_key(VK_MEDIA_NEXT_TRACK)
                return ToolResult(
                    success=True,
                    message="Sonraki parçaya geçildi efendim.",
                    data={"action": action}
                )
            elif action == "previous_track":
                _send_media_key(VK_MEDIA_PREV_TRACK)
                return ToolResult(
                    success=True,
                    message="Önceki parçaya dönüldü efendim.",
                    data={"action": action}
                )
            elif action == "stop":
                _send_media_key(VK_MEDIA_STOP)
                return ToolResult(
                    success=True,
                    message="Medya durduruldu efendim.",
                    data={"action": action}
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen medya eylemi: '{action}' efendim."
                )
        except Exception as e:
            logger.error(f"MediaControlTool hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Medya kontrol edilirken bir hata oluştu efendim: {str(e)}"
            )
