"""Google Calendar and Deadline Management Tool for Jarvis."""

from datetime import datetime, timedelta, timezone
import logging
import re
from typing import Any, Dict, List, Optional
import requests

from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.google_auth import GoogleAuthManager

logger = logging.getLogger(__name__)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class GoogleCalendarTool(BaseTool):
    """Google Takvim etkinlik ve son teslim tarihi (deadline) yönetim aracı."""

    name = "manage_calendar"
    description = (
        "Google Takvim üzerinden etkinlik, randevu veya son teslim tarihi (deadline) ekler; "
        "bugünün veya belirtilen günlerin ajandasını listeler; yaklaşan teslim tarihlerini sorgular. "
        "'Bugün neyim var?', 'Yarına ne yetişmeli?', 'Şu tarihe toplantı ekle' gibi taleplerde bu aracı çağır."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self.auth_manager = auth_manager or GoogleAuthManager()

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "description": (
                            "Yapılacak takvim eylemi: "
                            "'list_events' (ajandayı/etkinlikleri listele), "
                            "'add_event' (yeni etkinlik/toplantı ekle), "
                            "'list_deadlines' (yaklaşan son teslim tarihlerini listele), "
                            "'add_deadline' (yeni son teslim tarihi ekle)"
                        ),
                        "enum": ["list_events", "add_event", "list_deadlines", "add_deadline"],
                    },
                    "summary": {
                        "type": "STRING",
                        "description": "Etkinlik veya teslim tarihi başlığı (örn: 'Proje Toplantısı', 'Tez Teslimi').",
                    },
                    "start_time": {
                        "type": "STRING",
                        "description": "Başlangıç zamanı (ISO 8601 formatında veya 'YYYY-MM-DDTHH:MM:SS', örn: '2026-11-12T15:00:00').",
                    },
                    "end_time": {
                        "type": "STRING",
                        "description": "Bitiş zamanı (isteğe bağlı, belirtilmezse başlangıçtan 1 saat sonrası alınır).",
                    },
                    "days": {
                        "type": "INTEGER",
                        "description": "Kaç günlük etkinlik listeleneceği (1 = bugün, 7 = bu hafta). Varsayılan: 1.",
                    },
                    "description": {
                        "type": "STRING",
                        "description": "Etkinlik hakkında ek açıklama veya notlar.",
                    },
                },
                "required": ["action"],
            },
        }

    def _normalize_iso_time(self, time_str: Optional[str]) -> str:
        """Zaman dizgesini RFC 3339 uyumlu ISO formatına dönüştürür."""
        if not time_str:
            now = datetime.now()
            return now.isoformat()

        # Eğer sadece saat verilmişse veya kısmi formattaysa
        try:
            dt = datetime.fromisoformat(time_str)
            return dt.isoformat()
        except Exception:
            return time_str

    def execute(
        self,
        action: str = "list_events",
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days: int = 1,
        description: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        if not self.auth_manager.is_authenticated():
            return ToolResult(
                success=False,
                message=self.auth_manager.get_status_message(),
            )

        headers = self.auth_manager.get_auth_headers()
        if not headers:
            return ToolResult(
                success=False,
                message="Google yetkilendirme başlığı oluşturulamadı efendim.",
            )

        try:
            if action in ("add_event", "add_deadline"):
                return self._handle_add(action, summary, start_time, end_time, description, headers)
            elif action == "list_deadlines":
                return self._handle_list_deadlines(days, headers)
            elif action == "list_events":
                return self._handle_list_events(days, headers)
            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen takvim eylemi '{action}' efendim.",
                )
        except Exception as e:
            logger.error(f"Google Calendar hatası ({action}): {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Takvim işlemi sırasında bir hata oluştu efendim: {str(e)}",
            )

    def _handle_add(
        self,
        action: str,
        summary: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
        description: str,
        headers: Dict[str, str],
    ) -> ToolResult:
        if not summary:
            return ToolResult(success=False, message="Etkinlik başlığı belirtilmedi efendim.")

        is_deadline = action == "add_deadline"
        clean_summary = summary
        if is_deadline:
            if not summary.startswith("[Son Tarih]") and not summary.startswith("[Teslim]"):
                clean_summary = f"[Son Tarih] {summary}"

        start_iso = self._normalize_iso_time(start_time)
        if not end_time:
            try:
                dt_start = datetime.fromisoformat(start_iso)
                dt_end = dt_start + timedelta(hours=1)
                end_iso = dt_end.isoformat()
            except Exception:
                end_iso = start_iso
        else:
            end_iso = self._normalize_iso_time(end_time)

        payload = {
            "summary": clean_summary,
            "description": description or ("Jarvis tarafından otomatik oluşturuldu."),
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
        }

        resp = requests.post(CALENDAR_API_BASE, headers=headers, json=payload, timeout=10)
        if resp.status_code in (200, 201):
            if is_deadline:
                display_name = re.sub(r'^\[(Son Tarih|Teslim)\]\s*', '', clean_summary)
                return ToolResult(
                    success=True,
                    message=f"{display_name} son teslim tarihi takviminize eklendi efendim.",
                    data={"id": resp.json().get("id")},
                )
            else:
                return ToolResult(
                    success=True,
                    message=f"{clean_summary} etkinliği takviminize eklendi efendim.",
                    data={"id": resp.json().get("id")},
                )
        else:
            return ToolResult(
                success=False,
                message="Etkinlik takvime eklenemedi efendim.",
                data={"status_code": resp.status_code, "error": resp.text},
            )

    def _handle_list_events(self, days: int, headers: Dict[str, str]) -> ToolResult:
        now = datetime.now()
        time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
        time_max = (now + timedelta(days=max(1, days))).replace(hour=23, minute=59, second=59).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 20,
        }

        resp = requests.get(CALENDAR_API_BASE, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return ToolResult(success=False, message="Takvim etkinlikleri alınamadı efendim.")

        items = resp.json().get("items", [])
        # Normal etkinlikler (deadlines haricindekiler veya hepsi)
        if not items:
            return ToolResult(
                success=True,
                message="Belirtilen zaman aralığında planlanmış bir etkinliğiniz bulunmuyor efendim.",
                data={"items": []},
            )

        event_summaries = []
        for item in items:
            title = item.get("summary", "İsimsiz Etkinlik")
            start = item.get("start", {}).get("dateTime", "")
            time_part = ""
            if "T" in start:
                try:
                    time_part = datetime.fromisoformat(start).strftime("%H:%M")
                except Exception:
                    pass
            if time_part:
                event_summaries.append(f"saat {time_part}'de {title}")
            else:
                event_summaries.append(title)

        if len(event_summaries) == 1:
            spoken = f"Planlanmış 1 etkinliğiniz var: {event_summaries[0]} efendim."
        elif len(event_summaries) == 2:
            spoken = f"Planlanmış 2 etkinliğiniz var: {event_summaries[0]} ve {event_summaries[1]} efendim."
        else:
            spoken = f"Planlanmış {len(event_summaries)} etkinliğiniz var: {', '.join(event_summaries[:-1])} ve {event_summaries[-1]} efendim."

        return ToolResult(success=True, message=spoken, data={"count": len(items)})

    def _handle_list_deadlines(self, days: int, headers: Dict[str, str]) -> ToolResult:
        now = datetime.now()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=max(1, days or 7))).replace(hour=23, minute=59, second=59).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 30,
        }

        resp = requests.get(CALENDAR_API_BASE, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return ToolResult(success=False, message="Teslim tarihleri alınamadı efendim.")

        items = resp.json().get("items", [])
        deadlines = [
            it for it in items
            if "[Son Tarih]" in it.get("summary", "") or "[Teslim]" in it.get("summary", "")
        ]

        if not deadlines:
            return ToolResult(
                success=True,
                message="Yaklaşan herhangi bir teslim tarihiniz bulunmuyor efendim.",
                data={"deadlines": []},
            )

        deadline_titles = []
        for dl in deadlines:
            clean = re.sub(r'^\[(Son Tarih|Teslim)\]\s*', '', dl.get("summary", ""))
            deadline_titles.append(clean)

        if len(deadline_titles) == 1:
            spoken = f"Yaklaşan 1 teslim tarihiniz var: {deadline_titles[0]} efendim."
        else:
            spoken = f"Yaklaşan {len(deadline_titles)} teslim tarihiniz var: {', '.join(deadline_titles[:-1])} ve {deadline_titles[-1]} efendim."

        return ToolResult(success=True, message=spoken, data={"count": len(deadlines)})
