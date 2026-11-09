"""Google OAuth 2.0 authentication and token management for Calendar and Gmail."""

import http.server
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import webbrowser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import requests

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Local HTTP request handler to capture the OAuth 2.0 authorization code."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server request logs to keep terminal clean."""
        pass

    def do_GET(self) -> None:
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Jarvis - Yetkilendirme Başarılı</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 40px;
            max-width: 480px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h1 { color: #58a6ff; margin-bottom: 12px; }
        p { color: #8b949e; font-size: 16px; line-height: 1.5; }
        .success { color: #3fb950; font-size: 48px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="success">&#10004;</div>
        <h1>Yetkilendirme Başarılı!</h1>
        <p>Google hesabınız Jarvis'e başarıyla bağlandı efendim.</p>
        <p>Bu sekmeyi güvenle kapatıp Jarvis ile konuşmaya devam edebilirsiniz.</p>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        elif "error" in params:
            self.server.auth_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            err_msg = f"Yetkilendirme hatası: {params['error'][0]}"
            self.wfile.write(err_msg.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class GoogleAuthManager:
    """Manages Google OAuth 2.0 credentials, token persistence, and automatic refreshing."""

    SCOPES: List[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    _auth_thread: Optional[threading.Thread] = None
    _auth_lock = threading.Lock()

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

    def get_status_message(self, auto_launch: bool = True) -> str:
        """Kullanıcıya seslendirilecek bağlantı durum mesajını döner."""
        if self.is_authenticated():
            return "Google hesabınız bağlı ve hazır efendim."

        if not self.credentials_path.exists():
            return (
                "Google kimlik bilgileri (credentials.json) bulunamadı, "
                "lütfen dosyayı proje ana dizinine ekleyin efendim."
            )

        if auto_launch:
            launched = self.start_authorization_flow_async()
            if launched:
                return "Google yetkilendirme sayfasını tarayıcınızda açtım, lütfen onaylayın efendim."

        return "Google hesabınıza bağlanmak için yetkilendirme gerekiyor efendim."

    def start_authorization_flow_async(self, port: int = 8088) -> bool:
        """Yetkilendirme akışını arka planda bir thread'de başlatır ve tarayıcıyı açar."""
        if not self.credentials_path.exists():
            logger.warning("credentials.json bulunamadığı için yetkilendirme başlatılamadı.")
            return False

        with self._auth_lock:
            if self._auth_thread and self._auth_thread.is_alive():
                logger.info("Yetkilendirme akışı zaten arka planda çalışıyor.")
                return True

            self._auth_thread = threading.Thread(
                target=self._run_auth_safe,
                args=(port,),
                daemon=True,
                name="GoogleOAuthThread",
            )
            self._auth_thread.start()
            return True

    def _run_auth_safe(self, port: int) -> None:
        try:
            self.authenticate_interactive(port=port)
        except Exception as e:
            logger.error(f"Arka plan OAuth yetkilendirmesi sırasında hata: {e}", exc_info=True)

    def authenticate_interactive(
        self,
        port: int = 8088,
        timeout: int = 180,
        open_browser: bool = True,
    ) -> bool:
        """Yerel HTTP sunucusu açar, tarayıcıyı başlatır ve Google OAuth token'ını alır."""
        if not self.credentials_path.exists():
            logger.error(f"credentials.json bulunamadı: {self.credentials_path}")
            return False

        try:
            creds_raw = json.loads(self.credentials_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"credentials.json okunamadı: {e}")
            return False

        client_config = creds_raw.get("installed") or creds_raw.get("web")
        if not client_config:
            logger.error("credentials.json geçerli bir 'installed' istemci yapılandırması içermiyor.")
            return False

        client_id = client_config.get("client_id")
        client_secret = client_config.get("client_secret")
        auth_uri = client_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
        token_uri = client_config.get("token_uri", "https://oauth2.googleapis.com/token")

        if not client_id or not client_secret:
            logger.error("credentials.json içinde client_id veya client_secret bulunamadı.")
            return False

        server = None
        actual_port = port
        for p in range(port, port + 20):
            try:
                server = http.server.HTTPServer(("localhost", p), _OAuthCallbackHandler)
                actual_port = p
                break
            except OSError:
                continue

        if server is None:
            try:
                server = http.server.HTTPServer(("localhost", 0), _OAuthCallbackHandler)
                actual_port = server.server_address[1]
            except Exception as e:
                logger.error(f"Yerel OAuth sunucusu başlatılamadı: {e}")
                return False

        redirect_uri = f"http://localhost:{actual_port}/"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"{auth_uri}?{urllib.parse.urlencode(params)}"

        logger.info(f"Google OAuth yetkilendirmesi başlatılıyor (Port: {actual_port}).")
        logger.info(f"Yetkilendirme URL'si: {auth_url}")

        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                logger.warning(f"Tarayıcı otomatik açılamadı: {e}. Lütfen URL'yi elle açın.")

        server.timeout = 1.0
        start_time = time.time()
        auth_code: Optional[str] = None

        try:
            while time.time() - start_time < timeout:
                if hasattr(server, "auth_code"):
                    auth_code = getattr(server, "auth_code")
                    break
                if hasattr(server, "auth_error"):
                    err = getattr(server, "auth_error")
                    logger.error(f"Google yetkilendirme hatası aldı: {err}")
                    return False
                server.handle_request()
        finally:
            server.server_close()

        if not auth_code:
            logger.warning("Google OAuth yetkilendirmesi zaman aşımına uğradı.")
            return False

        # Yetkilendirme kodunu erişim token'ı ile takas et
        try:
            token_payload = {
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            resp = requests.post(token_uri, data=token_payload, timeout=20)
            if resp.status_code != 200:
                logger.error(f"Token alma başarısız oldu ({resp.status_code}): {resp.text}")
                return False

            token_data = resp.json()
            creds_data = {
                "token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_uri": token_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": self.scopes,
            }

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(json.dumps(creds_data, indent=2), encoding="utf-8")

            # Credentials nesnesini hemen önbelleğe al
            self._cached_creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
            logger.info("Google OAuth token.json başarıyla oluşturuldu ve doğrulandı.")
            return True
        except Exception as e:
            logger.error(f"Token kaydetme sırasında hata: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("=" * 60)
    print("Jarvis Desktop - Google OAuth 2.0 Yetkilendirme Aracı")
    print("=" * 60)

    auth = GoogleAuthManager()
    if not auth.credentials_path.exists():
        print(f"\n[HATA] credentials.json bulunamadı: {auth.credentials_path}")
        print("Lütfen Google Cloud Console'dan indirdiğiniz credentials.json dosyasını proje kök dizinine yerleştirin.")
        sys.exit(1)

    print("\nTarayıcınızda Google yetkilendirme sayfası açılıyor...")
    print("Lütfen açılan pencerede hesabınızı seçin, izinleri onaylayın.")
    ok = auth.authenticate_interactive()
    if ok:
        print("\n" + "=" * 60)
        print("[BAŞARILI] Google hesabınız bağlandı! token.json dosyası oluşturuldu.")
        print("Artık sesli olarak 'Mailimi kontrol et' veya 'Bugün neyim var?' diyebilirsiniz efendim.")
        print("=" * 60)
    else:
        print("\n[HATA] Yetkilendirme tamamlanamadı. Konsol loglarını kontrol edin.")
        sys.exit(1)
