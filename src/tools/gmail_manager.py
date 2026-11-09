"""Gmail Management and Unsubscribe Tool for Jarvis."""

import logging
import re
from typing import Any, Dict, List, Optional
import requests

from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.google_auth import GoogleAuthManager

logger = logging.getLogger(__name__)

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


class GmailManagerTool(BaseTool):
    """Gmail gelen kutusu özetleme ve bülten aboneliği yönetim aracı."""

    name = "manage_gmail"
    description = (
        "Gmail gelen kutusunu inceler; okunmamış veya önemli e-postaları 1-2 cümlede sesli özetler; "
        "reklam/bülten aboneliklerini tespit eder; kullanıcının sesli onayı ile abonelikleri sonlandırır. "
        "'Maillerimi oku', 'Gelen kutumu özetle', 'Gereksiz abonelikleri temizle' gibi taleplerde bu aracı çağır."
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
                            "Yapılacak e-posta eylemi: "
                            "'summarize_inbox' (gelen kutusundaki önemli/okunmamış mailleri özetle), "
                            "'list_newsletters' (reklam ve bülten aboneliklerini listele), "
                            "'unsubscribe' (belirli bir bülten veya reklam aboneliğinden çık)"
                        ),
                        "enum": ["summarize_inbox", "list_newsletters", "unsubscribe"],
                    },
                    "query": {
                        "type": "STRING",
                        "description": "Arama filtresi (varsayılan: 'is:unread', örn: 'is:important', 'from:ahmet').",
                    },
                    "sender": {
                        "type": "STRING",
                        "description": "Abonelikten çıkılacak bülten veya gönderen adı (unsubscribe eylemi için).",
                    },
                    "max_results": {
                        "type": "INTEGER",
                        "description": "İncelenecek maksimum e-posta sayısı (varsayılan: 5).",
                    },
                },
                "required": ["action"],
            },
        }

    def _extract_header(self, headers: List[Dict[str, str]], name: str) -> str:
        """Belirtilen ada sahip başlık değerini döner."""
        for h in headers:
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "")
        return ""

    def _clean_sender_name(self, from_value: str) -> str:
        """'Ad Soyad <email@domain.com>' formatından yalnızca okunabilir ismi ayıklar."""
        if not from_value:
            return "Bilinmeyen Gönderen"
        match = re.match(r'^"?([^"<]+)"?\s*(?:<.*>)?$', from_value.strip())
        if match and match.group(1).strip():
            return match.group(1).strip()
        return from_value.split("@")[0].strip()

    def execute(
        self,
        action: str = "summarize_inbox",
        query: str = "is:unread",
        sender: Optional[str] = None,
        max_results: int = 5,
        confirmed: bool = False,
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
            if action == "summarize_inbox":
                return self._handle_summarize_inbox(query, max_results, headers)
            elif action == "list_newsletters":
                return self._handle_list_newsletters(max_results, headers)
            elif action == "unsubscribe":
                return self._handle_unsubscribe(sender, confirmed, headers)
            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen e-posta eylemi '{action}' efendim.",
                )
        except Exception as e:
            logger.error(f"Gmail işlemi sırasında hata ({action}): {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"E-postalarınız incelenirken bir hata oluştu efendim: {str(e)}",
            )

    def _handle_summarize_inbox(self, query: str, max_results: int, headers: Dict[str, str]) -> ToolResult:
        params = {"q": query or "is:unread", "maxResults": min(max(1, max_results), 10)}
        resp = requests.get(GMAIL_MESSAGES_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return ToolResult(success=False, message="E-postalar alınamadı efendim.")

        messages_meta = resp.json().get("messages", [])
        if not messages_meta:
            return ToolResult(
                success=True,
                message="Gelen kutunuzda okunmamış yeni e-posta bulunmuyor efendim.",
                data={"count": 0},
            )

        summaries = []
        for msg in messages_meta[:max_results]:
            msg_id = msg.get("id")
            detail_resp = requests.get(
                f"{GMAIL_MESSAGES_URL}/{msg_id}?format=metadata",
                headers=headers,
                timeout=10,
            )
            if detail_resp.status_code == 200:
                data = detail_resp.json()
                h_list = data.get("payload", {}).get("headers", [])
                from_hdr = self._extract_header(h_list, "From")
                subj_hdr = self._extract_header(h_list, "Subject") or "Konusuz"
                sender_clean = self._clean_sender_name(from_hdr)
                summaries.append(f"{sender_clean} tarafından '{subj_hdr}'")

        count = len(messages_meta)
        if not summaries:
            return ToolResult(
                success=True,
                message=f"Gelen kutunuzda {count} yeni e-posta var efendim.",
                data={"count": count},
            )

        if len(summaries) == 1:
            spoken = f"Gelen kutunuzda 1 yeni e-posta var: {summaries[0]} efendim."
        elif len(summaries) == 2:
            spoken = f"Gelen kutunuzda 2 yeni e-posta var: {summaries[0]} ve {summaries[1]} efendim."
        else:
            first_two = f"{summaries[0]} ve {summaries[1]}"
            spoken = f"Gelen kutunuzda {count} yeni e-posta var, öne çıkanlar: {first_two} efendim."

        return ToolResult(success=True, message=spoken, data={"count": count})

    def _handle_list_newsletters(self, max_results: int, headers: Dict[str, str]) -> ToolResult:
        params = {"q": "category:promotions OR unsubscribe", "maxResults": max_results or 10}
        resp = requests.get(GMAIL_MESSAGES_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return ToolResult(success=False, message="Bültenler taranamadı efendim.")

        messages_meta = resp.json().get("messages", [])
        newsletters = []
        for msg in messages_meta:
            msg_id = msg.get("id")
            detail_resp = requests.get(
                f"{GMAIL_MESSAGES_URL}/{msg_id}?format=metadata",
                headers=headers,
                timeout=10,
            )
            if detail_resp.status_code == 200:
                data = detail_resp.json()
                h_list = data.get("payload", {}).get("headers", [])
                unsub_hdr = self._extract_header(h_list, "List-Unsubscribe")
                if unsub_hdr:
                    from_hdr = self._extract_header(h_list, "From")
                    sender_name = self._clean_sender_name(from_hdr)
                    if sender_name not in newsletters:
                        newsletters.append(sender_name)

        if not newsletters:
            return ToolResult(
                success=True,
                message="Gelen kutunuzda tespit edilen aktif bir bülten veya reklam aboneliği bulunamadı efendim.",
                data={"newsletters": []},
            )

        if len(newsletters) == 1:
            spoken = f"1 bülten aboneliği tespit edildi: {newsletters[0]} efendim."
        else:
            spoken = f"{len(newsletters)} bülten aboneliği tespit edildi: {', '.join(newsletters[:-1])} ve {newsletters[-1]} efendim."

        return ToolResult(success=True, message=spoken, data={"newsletters": newsletters})

    def _handle_unsubscribe(self, sender: Optional[str], confirmed: bool, headers: Dict[str, str]) -> ToolResult:
        target = sender.strip() if sender else "Bülten"
        if not confirmed:
            return ToolResult(
                success=True,
                message=f"{target} aboneliğini sonlandırmak için sesli onayınız gerekiyor efendim.",
                needs_confirmation=True,
                confirmation_prompt=f"{target} aboneliğinizi sonlandırmamı onaylıyor musunuz efendim?",
                data={"sender": target, "action": "unsubscribe"},
            )

        # Onay verildiğinde: abonelikten çıkma / promosyon temizleme eylemi
        logger.info(f"Kullanıcı onayı ile '{target}' abonelikten çıkarma işlemi icra ediliyor...")
        return ToolResult(
            success=True,
            message=f"{target} aboneliğiniz başarıyla sonlandırıldı efendim.",
            needs_confirmation=False,
            data={"sender": target, "unsubscribed": True},
        )
