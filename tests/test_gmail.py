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
        """Tek bir e-posta olduğunda Gemini ile zeki yönetici özeti üretilir."""
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

        mock_gemini_client = MagicMock()
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "İman Gadzhi potansiyel müşterilere nasıl ulaşılacağı ve satış stratejileri üzerine bir rehber paylaşmış efendim."
        mock_gemini_client.models.generate_content.return_value = mock_gemini_resp

        with patch("requests.get", side_effect=mock_get):
            tool = GmailManagerTool(auth_manager=mock_auth, client=mock_gemini_client)
            res = tool.execute(action="summarize_inbox", max_results=1)

            assert res.success is True
            assert "İman Gadzhi" in res.message or "satış" in res.message
            assert res.message.endswith("efendim.")
            mock_gemini_client.models.generate_content.assert_called_once()



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

    def test_determine_category_all_types(self):
        """Farklı e-posta gönderen ve konularının doğru kategorilere sınıflandırıldığını doğrular."""
        from src.tools.gmail_manager import _determine_category

        # Finans
        assert _determine_category("Garanti BBVA", "Hesap Özeti ve Dekont", "") == "Finans"
        assert _determine_category("AWS Billing", "November Invoice", "") == "Finans"
        assert _determine_category("Turkcell Fatura", "Kasım Ayı Faturanız", "") == "Finans"

        # Sosyal Medya (özellikle Pinterest ve 'e-posta/gibi' içeren durumlar)
        assert _determine_category("Pinterest <updates@pinterest.com>", "Günün fikirleri gibi harika pinler", "e-posta bildirimleri") == "Sosyal Medya"
        assert _determine_category("Pinterest", "Yeni pin ve panolar", "postlar") == "Sosyal Medya"
        assert _determine_category("LinkedIn Updates", "Zafer AYAN paylaştı", "") == "Sosyal Medya"
        assert _determine_category("YouTube", "Yeni video yüklendi", "", ["CATEGORY_SOCIAL"]) == "Sosyal Medya"

        # Alışveriş & Kargo
        assert _determine_category("Trendyol", "Siparişiniz kargoya verildi", "") == "Alışveriş & Kargo"
        assert _determine_category("Yurtiçi Kargo", "Takip No: 12345", "") == "Alışveriş & Kargo"

        # Eğitim & Gelişim
        assert _determine_category("Udemy", "Yeni kurs eklendi", "") == "Eğitim & Gelişim"
        assert _determine_category("Iman Gadzhi", "training guide", "") == "Eğitim & Gelişim"

        # İş & Proje
        assert _determine_category("Ahmet Yılmaz", "Sprint Planlaması Toplantısı", "") == "İş & Proje"

        # Bülten & Tanıtım
        assert _determine_category("Teknoloji Dergisi", "Haftalık Bülten İndirimi", "", ["CATEGORY_PROMOTIONS"]) == "Bülten & Tanıtım"

        # Kişisel
        assert _determine_category("Arkadaşım Ali", "Selam nasılsın", "") == "Kişisel"

    def test_gmail_categorize_and_label_action(self):
        """categorize_and_label eylemi mailleri etiketleyip Gmail'e basar ve döküm döner."""
        from src.tools.gmail_manager import _determine_category

        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "messages": [{"id": "msg_finans"}, {"id": "msg_social"}]
        }

        mock_finans_resp = MagicMock()
        mock_finans_resp.status_code = 200
        mock_finans_resp.json.return_value = {
            "id": "msg_finans",
            "snippet": "Garanti Bankası ekstresi...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Garanti BBVA <ekstre@garanti.com.tr>"},
                    {"name": "Subject", "value": "Kasım Ayı Hesap Ekstresi"},
                ]
            },
        }

        mock_social_resp = MagicMock()
        mock_social_resp.status_code = 200
        mock_social_resp.json.return_value = {
            "id": "msg_social",
            "snippet": "Zafer AYAN paylaştı...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "LinkedIn <updates@linkedin.com>"},
                    {"name": "Subject", "value": "Zafer AYAN yeni bir gönderi paylaştı"},
                ]
            },
        }

        def mock_get(url, **kwargs):
            if "messages/msg_finans" in url:
                return mock_finans_resp
            elif "messages/msg_social" in url:
                return mock_social_resp
            elif "labels" in url:
                mock_labels = MagicMock()
                mock_labels.status_code = 200
                mock_labels.json.return_value = {"labels": [{"id": "Label_Finans", "name": "Finans"}]}
                return mock_labels
            return mock_list_resp

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id": "Label_New"}

        with patch("requests.get", side_effect=mock_get):
            with patch("requests.post", return_value=mock_post_resp) as mock_post:
                tool = GmailManagerTool(auth_manager=mock_auth)
                result = tool.execute(action="categorize_and_label")

                assert result.success is True
                assert "etiketlendi" in result.message
                assert "Finans" in result.message
                assert "Sosyal Medya" in result.message
                assert result.message.endswith("efendim.")
                assert "categories" in result.data
                assert result.data["categories"]["Finans"] == 1
                assert result.data["categories"]["Sosyal Medya"] == 1
                # POST yapıldı (modify veya label oluşturma)
                assert mock_post.called

    def test_gmail_mark_as_read_from_cached_summarized_ids(self):
        """Son özetlenen e-postaların kimlikleri üzerinden okundu olarak işaretleme testi."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id": "msg_1", "labelIds": []}

        with patch("requests.post", return_value=mock_post_resp) as mock_post:
            tool = GmailManagerTool(auth_manager=mock_auth)
            tool._last_summarized_ids = ["msg_1", "msg_2"]

            result = tool.execute(action="mark_as_read")

            assert result.success is True
            assert "Özetlenen 2 e-posta" in result.message
            assert result.message.endswith("efendim.")
            assert result.data["count"] == 2
            assert tool._last_summarized_ids == []
            assert mock_post.call_count == 2
            # UNREAD etiketinin kaldırıldığını doğrula
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs.get("json") == {"removeLabelIds": ["UNREAD"]}

    def test_gmail_mark_as_read_fallback_queries_inbox(self):
        """Hafızada özet bulunmadığında gelen kutusundaki okunmamış mailleri sorgulayıp okundu yapar."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "messages": [{"id": "msg_unread_1"}]
        }

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200

        with patch("requests.get", return_value=mock_list_resp):
            with patch("requests.post", return_value=mock_post_resp) as mock_post:
                tool = GmailManagerTool(auth_manager=mock_auth)
                assert tool._last_summarized_ids == []

                result = tool.execute(action="mark_as_read")

                assert result.success is True
                assert "Belirtilen 1 e-posta" in result.message
                assert result.message.endswith("efendim.")
                assert result.data["count"] == 1
                assert mock_post.called

    def test_gmail_summarize_inbox_auto_marks_as_read_and_caches_ids(self):
        """summarize_inbox çalıştırıldığında e-postalar otomatik okundu işaretlenir ve ID'leri saklanır."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer fake_token"}

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "messages": [{"id": "msg_auto_1"}]
        }

        mock_msg_resp = MagicMock()
        mock_msg_resp.status_code = 200
        mock_msg_resp.json.return_value = {
            "id": "msg_auto_1",
            "snippet": "Test mesajı",
            "labelIds": ["UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Test <test@example.com>"},
                    {"name": "Subject", "value": "Test Konusu"},
                ]
            },
        }

        def mock_get(url, **kwargs):
            if "labels" in url:
                m = MagicMock()
                m.status_code = 200
                m.json.return_value = {"labels": []}
                return m
            elif "msg_auto_1" in url:
                return mock_msg_resp
            return mock_list_resp

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id": "Label_Id"}

        with patch("requests.get", side_effect=mock_get):
            with patch("requests.post", return_value=mock_post_resp) as mock_post:
                tool = GmailManagerTool(auth_manager=mock_auth)
                result = tool.execute(action="summarize_inbox")

                assert result.success is True
                assert tool._last_summarized_ids == ["msg_auto_1"]
                # modify endpoint'i çağrılmış olmalı
                modify_calls = [
                    call for call in mock_post.call_args_list
                    if call[1].get("json") == {"removeLabelIds": ["UNREAD"]}
                ]
                assert len(modify_calls) == 1


