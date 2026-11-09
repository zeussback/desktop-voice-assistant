"""Tests for GmailManagerTool (Phase 4)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from src.tools.gmail_manager import GmailManagerTool
from src.tools.base import ConfirmationPolicy
from src.tools import create_default_tool_registry


class TestGmailManagerTool:
    """Gmail gelen kutusu özetleme, bülten tespiti ve teyitli abonelikten çıkma testleri."""

    def test_gmail_tool_declaration(self):
        """manage_gmail aracının adı, parametreleri ve teyit politikasını doğrular."""
        tool = GmailManagerTool()
        assert tool.name == "manage_gmail"
        assert "gmail" in tool.description.lower() or "e-posta" in tool.description.lower()

        decl = tool.get_declaration()
        assert decl["name"] == "manage_gmail"
        props = decl["parameters"]["properties"]
        assert "action" in props
        assert "query" in props
        assert "sender" in props

    def test_gmail_unauthenticated_returns_status(self):
        """Oturum açılmamışken aracın asistanı çökertmeyip durum mesajı döndüğünü doğrular."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_status_message.return_value = "Google kimlik bilgileri bulunamadı efendim."

        tool = GmailManagerTool(auth_manager=mock_auth)
        result = tool.execute(action="summarize_inbox")

        assert result.success is False
        assert "kimlik bilgileri" in result.message
        assert result.message.endswith("efendim.")

    def test_gmail_summarize_inbox_success(self):
        """Okunmamış mailler alındığında Piper TTS için akıcı sesli özet üretilir."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        # 1. Mesaj listesi isteği
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "messages": [{"id": "msg_1"}, {"id": "msg_2"}]
        }

        # 2. Mesaj detayları isteği
        mock_msg1_resp = MagicMock()
        mock_msg1_resp.status_code = 200
        mock_msg1_resp.json.return_value = {
            "id": "msg_1",
            "snippet": "Yarınki sprint planlama toplantısı hakkında...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Ahmet Yılmaz <ahmet@example.com>"},
                    {"name": "Subject", "value": "Sprint Planlaması"},
                ]
            },
        }

        mock_msg2_resp = MagicMock()
        mock_msg2_resp.status_code = 200
        mock_msg2_resp.json.return_value = {
            "id": "msg_2",
            "snippet": "Faturanız hazır...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "AWS Billing <no-reply@amazon.com>"},
                    {"name": "Subject", "value": "Kasım Ayı Faturası"},
                ]
            },
        }

        def mock_get(url, **kwargs):
            if "messages/msg_1" in url:
                return mock_msg1_resp
            elif "messages/msg_2" in url:
                return mock_msg2_resp
            return mock_list_resp

        with patch("requests.get", side_effect=mock_get):
            tool = GmailManagerTool(auth_manager=mock_auth)
            result = tool.execute(action="summarize_inbox")

            assert result.success is True
            assert "Ahmet Yılmaz" in result.message or "Sprint Planlaması" in result.message
            assert result.message.endswith("efendim.")
            assert "emails" in result.data
            assert len(result.data["emails"]) == 2

    def test_gmail_summarize_single_email_with_snippet(self):
        """Tek bir e-posta olduğunda içerik özeti (snippet) ile birlikte detaylı aktarılır."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {"messages": [{"id": "single_msg"}]}

        mock_detail_resp = MagicMock()
        mock_detail_resp.status_code = 200
        mock_detail_resp.json.return_value = {
            "id": "single_msg",
            "snippet": "Müşterilerimizi nasıl bulacağımız hakkında detaylar...",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Iman Gadzhi <iman@agency.com>"},
                    {"name": "Subject", "value": "today we go and find your customers"},
                ]
            },
        }

        def mock_get(url, **kwargs):
            if "messages/single_msg" in url:
                return mock_detail_resp
            return mock_list_resp

        with patch("requests.get", side_effect=mock_get):
            tool = GmailManagerTool(auth_manager=mock_auth)
            res = tool.execute(action="summarize_inbox", max_results=1)

            assert res.success is True
            assert "Iman Gadzhi" in res.message
            assert "today we go and find your customers" in res.message
            assert "Müşterilerimizi nasıl bulacağımız" in res.message
            assert res.message.endswith("efendim.")


    def test_gmail_summarize_inbox_empty(self):
        """Gelen kutusu boşken uygun mesaj döner."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": []}

        with patch("requests.get", return_value=mock_resp):
            tool = GmailManagerTool(auth_manager=mock_auth)
            result = tool.execute(action="summarize_inbox")

            assert result.success is True
            assert "okunmamış" in result.message.lower()
            assert result.message.endswith("efendim.")

    def test_gmail_list_newsletters_detects_unsubscribe_header(self):
        """List-Unsubscribe başlığı taşıyan mailleri tespit eder."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {"messages": [{"id": "promo_1"}]}

        mock_promo_resp = MagicMock()
        mock_promo_resp.status_code = 200
        mock_promo_resp.json.return_value = {
            "id": "promo_1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Haftalık Teknoloji Bülteni <newsletter@tech.com>"},
                    {"name": "Subject", "value": "Haftanın Yapay Zeka Haberleri"},
                    {"name": "List-Unsubscribe", "value": "<https://tech.com/unsub?id=123>"},
                ]
            },
        }

        def mock_get(url, **kwargs):
            if "promo_1" in url:
                return mock_promo_resp
            return mock_list_resp

        with patch("requests.get", side_effect=mock_get):
            tool = GmailManagerTool(auth_manager=mock_auth)
            result = tool.execute(action="list_newsletters")

            assert result.success is True
            assert "Haftalık Teknoloji Bülteni" in result.message
            assert result.message.endswith("efendim.")

    def test_gmail_unsubscribe_requires_confirmation(self):
        """unsubscribe eylemi teyitsiz çalıştırıldığında sesli onay ister."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        tool = GmailManagerTool(auth_manager=mock_auth)
        result = tool.execute(action="unsubscribe", sender="Teknoloji Bülteni", confirmed=False)

        assert result.needs_confirmation is True
        assert "Teknoloji Bülteni" in result.confirmation_prompt
        assert "onaylıyor musunuz" in result.confirmation_prompt

    def test_gmail_unsubscribe_executes_when_confirmed(self):
        """unsubscribe eylemi confirmed=True olduğunda işlemi tamamlar."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        tool = GmailManagerTool(auth_manager=mock_auth)
        result = tool.execute(action="unsubscribe", sender="Teknoloji Bülteni", confirmed=True)

        assert result.success is True
        assert result.needs_confirmation is False
        assert "Teknoloji Bülteni" in result.message
        assert "sonlandırıldı" in result.message or "çıkarıldı" in result.message
        assert result.message.endswith("efendim.")

    def test_gmail_tool_registered_in_default_registry(self):
        """create_default_tool_registry() fabrikasının manage_gmail aracını içerdiğini doğrular."""
        registry = create_default_tool_registry()
        tool = registry.get("manage_gmail")
        assert tool is not None
        assert isinstance(tool, GmailManagerTool)
