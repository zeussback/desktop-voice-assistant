"""Tests for GoogleAuthManager and OAuth 2.0 token management (Phase 4)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.tools.google_auth import GoogleAuthManager


class TestGoogleAuthManager:
    """Google OAuth 2.0 kimlik doğrulama ve token yönetimi testleri."""

    def test_init_paths_default(self):
        """Varsayılan credentials.json ve token.json yollarını doğrular."""
        manager = GoogleAuthManager()
        assert manager.credentials_path.name == "credentials.json"
        assert manager.token_path.name == "token.json"
        assert "calendar" in manager.scopes[0]
        assert "gmail" in manager.scopes[1]

    def test_is_authenticated_false_when_no_token(self, tmp_path):
        """Token dosyası yokken is_authenticated False döner."""
        manager = GoogleAuthManager(
            credentials_path=tmp_path / "credentials.json",
            token_path=tmp_path / "token.json",
        )
        assert manager.is_authenticated() is False
        assert manager.get_credentials() is None
        assert manager.get_auth_headers() is None

    def test_status_message_when_credentials_missing(self, tmp_path):
        """credentials.json yokken kullanıcıya nazik sesli rehberlik mesajı döner."""
        manager = GoogleAuthManager(
            credentials_path=tmp_path / "missing_creds.json",
            token_path=tmp_path / "missing_token.json",
        )
        msg = manager.get_status_message()
        assert "credentials.json" in msg
        assert "bulunamadı" in msg
        assert msg.endswith("efendim.")

    def test_status_message_when_credentials_exist_but_not_authorized(self, tmp_path):
        """credentials.json var ama token.json yokken yetkilendirme gerektiğini bildirir."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"installed": {"client_id": "test_id"}}), encoding="utf-8")

        manager = GoogleAuthManager(
            credentials_path=creds_file,
            token_path=tmp_path / "missing_token.json",
        )
        msg = manager.get_status_message()
        assert "yetkilendirme" in msg.lower()
        assert msg.endswith("efendim.")

    def test_get_credentials_valid_token(self, tmp_path):
        """Geçerli token.json dosyası olduğunda Credentials nesnesi döner."""
        token_file = tmp_path / "token.json"
        token_data = {
            "token": "fake_access_token_123",
            "refresh_token": "fake_refresh_token_456",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake_client_id",
            "client_secret": "fake_client_secret",
            "scopes": GoogleAuthManager.SCOPES,
        }
        token_file.write_text(json.dumps(token_data), encoding="utf-8")

        manager = GoogleAuthManager(token_path=token_file)

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.token = "fake_access_token_123"

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=mock_creds):
            assert manager.is_authenticated() is True
            creds = manager.get_credentials()
            assert creds is not None
            assert creds.token == "fake_access_token_123"

            headers = manager.get_auth_headers()
            assert headers["Authorization"] == "Bearer fake_access_token_123"
            assert "hazır" in manager.get_status_message()

    def test_get_credentials_refreshes_expired_token(self, tmp_path):
        """Süresi dolmuş token olduğunda refresh çağrılır ve güncellenir."""
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"token": "old_token", "refresh_token": "ref_token"}), encoding="utf-8")

        manager = GoogleAuthManager(token_path=token_file)

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "ref_token"
        mock_creds.token = "refreshed_token_999"
        mock_creds.to_json.return_value = json.dumps({"token": "refreshed_token_999"})

        def make_valid(req):
            mock_creds.valid = True

        mock_creds.refresh.side_effect = make_valid

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=mock_creds):
            with patch("google.auth.transport.requests.Request"):
                creds = manager.get_credentials()
                mock_creds.refresh.assert_called_once()
                assert creds is not None
                assert creds.token == "refreshed_token_999"
