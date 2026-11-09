"""Tests for MorningBriefingTool (Phase 4)."""

from unittest.mock import MagicMock
import pytest

from src.tools.morning_briefing import MorningBriefingTool
from src.tools.base import ConfirmationPolicy, ToolResult
from src.tools import create_default_tool_registry


class TestMorningBriefingTool:
    """Sabah brifingi derleme ve sesli ajanda birleştirme testleri."""

    def test_morning_briefing_tool_declaration(self):
        """get_morning_briefing aracının adı, parametreleri ve teyit politikasını doğrular."""
        tool = MorningBriefingTool()
        assert tool.name == "get_morning_briefing"
        assert tool.confirmation_policy == ConfirmationPolicy.IMMEDIATE
        assert "sabah" in tool.description.lower() or "brifing" in tool.description.lower()

        decl = tool.get_declaration()
        assert decl["name"] == "get_morning_briefing"

    def test_morning_briefing_unauthenticated_returns_status(self):
        """Oturum açılmamışken aracın asistanı çökertmeyip durum mesajı döndüğünü doğrular."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_status_message.return_value = "Google kimlik bilgileri bulunamadı efendim."

        tool = MorningBriefingTool(auth_manager=mock_auth)
        result = tool.execute()

        assert result.success is False
        assert "kimlik bilgileri" in result.message
        assert result.message.endswith("efendim.")

    def test_morning_briefing_compiles_events_deadlines_and_emails(self):
        """Takvim randevuları, teslim tarihleri ve okunmamış e-postalar tek bir akıcı metinde birleştirilir."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True

        mock_calendar = MagicMock()
        mock_calendar.execute.side_effect = [
            # 1. list_events (bugün)
            ToolResult(success=True, message="Planlanmış 1 etkinliğiniz var: saat 14:00'te Sprint Planlaması efendim."),
            # 2. list_deadlines (3 gün)
            ToolResult(success=True, message="Yaklaşan 1 teslim tarihiniz var: Makale Teslimi efendim."),
        ]

        mock_gmail = MagicMock()
        mock_gmail.execute.return_value = ToolResult(
            success=True,
            message="Gelen kutunuzda 2 yeni e-posta var, öne çıkanlar: Ahmet Yılmaz ve AWS Billing efendim.",
        )

        tool = MorningBriefingTool(
            auth_manager=mock_auth,
            calendar_tool=mock_calendar,
            gmail_tool=mock_gmail,
        )

        result = tool.execute()

        assert result.success is True
        assert "Günaydın efendim" in result.message or "günaydın" in result.message.lower()
        assert "Sprint Planlaması" in result.message
        assert "Makale Teslimi" in result.message
        assert "e-posta" in result.message
        assert result.message.endswith("efendim.")

    def test_morning_briefing_empty_schedule_warm_message(self):
        """Hiçbir randevu veya mail yokken sakin bir gün mesajı döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True

        mock_calendar = MagicMock()
        mock_calendar.execute.side_effect = [
            ToolResult(success=True, message="Belirtilen zaman aralığında planlanmış bir etkinliğiniz bulunmuyor efendim."),
            ToolResult(success=True, message="Yaklaşan herhangi bir teslim tarihiniz bulunmuyor efendim."),
        ]

        mock_gmail = MagicMock()
        mock_gmail.execute.return_value = ToolResult(
            success=True,
            message="Gelen kutunuzda okunmamış yeni e-posta bulunmuyor efendim.",
        )

        tool = MorningBriefingTool(
            auth_manager=mock_auth,
            calendar_tool=mock_calendar,
            gmail_tool=mock_gmail,
        )

        result = tool.execute()

        assert result.success is True
        assert "etkinliğiniz" in result.message
        assert result.message.endswith("efendim.")

    def test_morning_briefing_registered_in_default_registry(self):
        """create_default_tool_registry() fabrikasının get_morning_briefing aracını içerdiğini doğrular."""
        registry = create_default_tool_registry()
        tool = registry.get("get_morning_briefing")
        assert tool is not None
        assert isinstance(tool, MorningBriefingTool)
