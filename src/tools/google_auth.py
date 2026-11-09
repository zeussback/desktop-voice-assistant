"""Google OAuth 2.0 authentication and token management for Calendar and Gmail."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class GoogleAuthManager:
    """Manages Google OAuth 2.0 credentials, token persistence, and automatic refreshing."""

    SCOPES: List[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        token_path: Optional[Path] = None,
        scopes: Optional[List[str]] = None,
    ):
        self.credentials_path = Path(credentials_path or (_PROJECT_ROOT / "credentials.json"))
        self.token_path = Path(token_path or (_PROJECT_ROOT / "token.json"))
        self.scopes = scopes or list(self.SCOPES)
        self._cached_creds: Optional[Credentials] = None

    def is_authenticated(self) -> bool:
        """Kullanıcının geçerli ve yetkilendirilmiş bir Google oturumu olup olmadığını döner."""
        creds = self.get_credentials()
        return creds is not None and creds.valid

    def get_credentials(self) -> Optional[Credentials]:
        """Geçerli veya yenilenmiş Credentials nesnesini döner; yoksa None döner."""
        if not self.token_path.exists():
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

            if creds.expired and creds.refresh_token:
                logger.info("Google OAuth token süresi dolmuş, yenileniyor...")
                creds.refresh(Request())
                self._save_token(creds)

            if creds.valid:
                self._cached_creds = creds
                return creds
        except Exception as e:
            logger.warning(f"Google token yüklenirken/yenilenirken hata: {e}")

        return None

    def _save_token(self, creds: Credentials) -> None:
        """Yenilenen token bilgilerini yerel token.json dosyasına kaydeder."""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            logger.info("Google OAuth token.json başarıyla güncellendi.")
        except Exception as e:
            logger.error(f"token.json kaydedilemedi: {e}")

    def get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Google REST API istekleri için Bearer authorization başlığını döner."""
        creds = self.get_credentials()
        if creds and creds.token:
            return {
                "Authorization": f"Bearer {creds.token}",
                "Accept": "application/json",
            }
        return None

    def get_status_message(self) -> str:
        """Kullanıcıya seslendirilecek bağlantı durum mesajını döner."""
        if self.is_authenticated():
            return "Google hesabınız bağlı ve hazır efendim."

        if not self.credentials_path.exists():
            return (
                "Google kimlik bilgileri (credentials.json) bulunamadı, "
                "lütfen dosyayı proje ana dizinine ekleyin efendim."
            )

        return "Google hesabınıza bağlanmak için yetkilendirme gerekiyor efendim."
