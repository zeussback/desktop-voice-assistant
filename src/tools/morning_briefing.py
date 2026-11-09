"""Morning Briefing Aggregator Tool for Jarvis (Calendar, Deadlines & Gmail)."""

import logging
import re
from typing import Any, Dict, Optional

from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.google_auth import GoogleAuthManager
from src.tools.google_calendar import GoogleCalendarTool
from src.tools.gmail_manager import GmailManagerTool

logger = logging.getLogger(__name__)


def _clean_clause(text: str) -> str:
    """Metin içindeki 'efendim' kelimelerini ve baştaki/sondaki noktalamayı temizler."""
    if not text:
        return ""
    c = re.sub(r'\befendim\b', '', text, flags=re.IGNORECASE)
    c = c.strip(" .,;!?")
    c = re.sub(r'\s+', ' ', c).strip()
    return c


class MorningBriefingTool(BaseTool):
    """Günün takvim etkinliklerini, teslim tarihlerini ve e-postalarını özetleyen sabah brifingi aracı."""

    name = "get_morning_briefing"
    description = (
        "Sabahları günün ajandasını, bugünün takvim randevularını, yaklaşan teslim tarihlerini (deadlines) "
        "ve gelen kutusundaki önemli okunmamış e-postaları tek bir akıcı sesli brifing olarak sunar. "
        "'Günaydın Jarvis', 'Bugün neyim var?', 'Bugün yapmam gerekenler neler?', 'Günün özeti nedir?' "
        "gibi taleplerde bu aracı çağır."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def __init__(
        self,
        auth_manager: Optional[GoogleAuthManager] = None,
        calendar_tool: Optional[GoogleCalendarTool] = None,
        gmail_tool: Optional[GmailManagerTool] = None,
    ):
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.calendar_tool = calendar_tool or GoogleCalendarTool(auth_manager=self.auth_manager)
        self.gmail_tool = gmail_tool or GmailManagerTool(auth_manager=self.auth_manager)

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "days_ahead": {
                        "type": "INTEGER",
                        "description": "Teslim tarihleri için kaç gün ileriye bakılacağı (varsayılan: 3).",
                    }
                },
                "required": [],
            },
        }

    def execute(self, days_ahead: int = 3, **kwargs: Any) -> ToolResult:
        if not self.auth_manager.is_authenticated():
            return ToolResult(
                success=False,
                message=self.auth_manager.get_status_message(),
            )

        try:
            # 1. Bugünün takvim randevuları
            cal_res = self.calendar_tool.execute(action="list_events", days=1)
            # 2. Yaklaşan teslim tarihleri
            dl_res = self.calendar_tool.execute(action="list_deadlines", days=days_ahead)
            # 3. Gelen kutusu okunmamış mailler
            mail_res = self.gmail_tool.execute(action="summarize_inbox", query="is:unread", max_results=3)

            cal_msg = _clean_clause(cal_res.message)
            dl_msg = _clean_clause(dl_res.message)
            mail_msg = _clean_clause(mail_res.message)

            has_events = "bulunmuyor" not in cal_msg.lower() and bool(cal_msg)
            has_deadlines = "bulunmuyor" not in dl_msg.lower() and bool(dl_msg)
            has_mail = "bulunmuyor" not in mail_msg.lower() and bool(mail_msg)

            parts = []

            if has_events:
                parts.append(cal_msg)
            if has_deadlines:
                parts.append(f"ayrıca {dl_msg}")
            if has_mail:
                parts.append(mail_msg)

            if not parts:
                spoken = (
                    "Günaydın efendim. Bugün için planlanmış bir etkinliğiniz, "
                    "yaklaşan bir teslim tarihiniz veya yeni e-postanız bulunmuyor; "
                    "sakin ve verimli bir gün dilerim efendim."
                )
            else:
                combined_body = ". ".join(parts)
                # Sondaki noktalamaları temizle ve tek efendim ekle
                combined_body = re.sub(r'\befendim\b', '', combined_body, flags=re.IGNORECASE).strip(" .,;!?")
                spoken = f"Günaydın efendim. {combined_body} efendim."

            return ToolResult(
                success=True,
                message=spoken,
                data={
                    "has_events": has_events,
                    "has_deadlines": has_deadlines,
                    "has_mail": has_mail,
                },
            )

        except Exception as e:
            logger.error(f"Sabah brifingi derlenirken hata: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Sabah brifingi hazırlanırken bir hata oluştu efendim: {str(e)}",
            )
