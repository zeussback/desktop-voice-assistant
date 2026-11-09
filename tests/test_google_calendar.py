"""Tests for GoogleCalendarTool (Phase 4)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from src.tools.google_calendar import GoogleCalendarTool
from src.tools.base import ConfirmationPolicy
from src.tools import create_default_tool_registry


class TestGoogleCalendarTool:
    """GoogleCalendarTool takvim ve teslim tarihi yönetimi testleri."""

    def test_google_calendar_tool_declaration(self):
        """manage_calendar aracının adı, parametreleri ve teyit politikasını doğrular."""
        tool = GoogleCalendarTool()
        assert tool.name == "manage_calendar"
        assert tool.confirmation_policy == ConfirmationPolicy.IMMEDIATE
        assert "takvim" in tool.description.lower()

        decl = tool.get_declaration()
        assert decl["name"] == "manage_calendar"
        props = decl["parameters"]["properties"]
        assert "action" in props
        assert "summary" in props
        assert "start_time" in props
        assert "days" in props

    def test_google_calendar_unauthenticated_returns_status_message(self):
        """Oturum açılmamışken aracın asistanı çökertmeyip durum mesajı döndüğünü doğrular."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_status_message.return_value = "Google kimlik bilgileri bulunamadı efendim."

        tool = GoogleCalendarTool(auth_manager=mock_auth)
        result = tool.execute(action="list_events")

        assert result.success is False
        assert "kimlik bilgileri" in result.message
        assert result.message.endswith("efendim.")

    def test_google_calendar_add_event_success(self):
        """Takvime yeni toplantı/etkinlik başarıyla eklendiğinde sesli onay mesajı döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "evt_123",
            "summary": "Proje Toplantısı",
            "start": {"dateTime": "2026-11-12T15:00:00+03:00"},
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            tool = GoogleCalendarTool(auth_manager=mock_auth)
            result = tool.execute(
                action="add_event",
                summary="Proje Toplantısı",
                start_time="2026-11-12T15:00:00",
                description="Haftalık sprint değerlendirmesi",
            )

            assert result.success is True
            assert "Proje Toplantısı" in result.message
            assert result.message.endswith("efendim.")
            mock_post.assert_called_once()
            call_json = mock_post.call_args[1]["json"]
            assert call_json["summary"] == "Proje Toplantısı"
            assert "2026-11-12" in call_json["start"]["dateTime"]

    def test_google_calendar_add_deadline_prepends_tag(self):
        """Teslim tarihi eklendiğinde [Son Tarih] etiketi eklenir ve sesli teyit döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "dl_123",
            "summary": "[Son Tarih] Tez Teslimi",
            "start": {"dateTime": "2026-11-15T18:00:00+03:00"},
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            tool = GoogleCalendarTool(auth_manager=mock_auth)
            result = tool.execute(
                action="add_deadline",
                summary="Tez Teslimi",
                start_time="2026-11-15T18:00:00",
            )

            assert result.success is True
            assert "Tez Teslimi" in result.message
            assert "teslim tarihi" in result.message.lower()
            assert result.message.endswith("efendim.")
            call_json = mock_post.call_args[1]["json"]
            assert call_json["summary"] == "[Son Tarih] Tez Teslimi"

    def test_google_calendar_list_events_success(self):
        """Takvimdeki etkinlikler seslendirmeye uygun akıcı formatta döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "summary": "Mimari Tasarım Toplantısı",
                    "start": {"dateTime": "2026-11-10T10:00:00+03:00"},
                },
                {
                    "summary": "Kod İnceleme Görüşmesi",
                    "start": {"dateTime": "2026-11-10T14:30:00+03:00"},
                },
            ]
        }

        with patch("requests.get", return_value=mock_response):
            tool = GoogleCalendarTool(auth_manager=mock_auth)
            result = tool.execute(action="list_events", days=1)

            assert result.success is True
            assert "Mimari Tasarım Toplantısı" in result.message
            assert "Kod İnceleme Görüşmesi" in result.message
            assert result.message.endswith("efendim.")

    def test_google_calendar_list_events_empty(self):
        """Takvimde etkinlik yokken kibar bilgilendirme mesajı döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch("requests.get", return_value=mock_response):
            tool = GoogleCalendarTool(auth_manager=mock_auth)
            result = tool.execute(action="list_events", days=1)

            assert result.success is True
            assert "etkinliğiniz bulunmuyor" in result.message
            assert result.message.endswith("efendim.")

    def test_google_calendar_list_deadlines_filters_tag(self):
        """list_deadlines yalnızca [Son Tarih] veya [Teslim] etiketli işleri filtreler."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "summary": "Ekip Öğle Yemeği",
                    "start": {"dateTime": "2026-11-11T12:00:00+03:00"},
                },
                {
                    "summary": "[Son Tarih] Makale Revizyonu",
                    "start": {"dateTime": "2026-11-11T23:59:00+03:00"},
                },
            ]
        }

        with patch("requests.get", return_value=mock_response):
            tool = GoogleCalendarTool(auth_manager=mock_auth)
            result = tool.execute(action="list_deadlines", days=7)

            assert result.success is True
            assert "Makale Revizyonu" in result.message
            assert "Ekip Öğle Yemeği" not in result.message
            assert result.message.endswith("efendim.")

    def test_google_calendar_registered_in_default_registry(self):
        """create_default_tool_registry() fabrikasının manage_calendar aracını içerdiğini doğrular."""
        registry = create_default_tool_registry()
        tool = registry.get("manage_calendar")
        assert tool is not None
        assert isinstance(tool, GoogleCalendarTool)
