"""Gmail Management and Unsubscribe Tool for Jarvis."""

import html
import logging
import re
from typing import Any, Dict, List, Optional
import requests

from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.google_auth import GoogleAuthManager

logger = logging.getLogger(__name__)

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _clean_text_for_speech(text: str) -> str:
    """TTS ve sesli özet için metindeki emojileri, HTML karakterlerini ve linkleri temizler."""
    if not text:
        return ""
    text = html.unescape(text)
    # Emojileri temizle (SMP, Misc Symbols, vb.)
    text = re.sub(
        r"[\U00010000-\U0010ffff]|[\u200d\uFE0E\uFE0F]|[\u2600-\u27bf]|[\u2300-\u23ff]",
        "",
        text,
    )
    # URL ve HTML etiketlerini temizle
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    # Üç nokta ve gereksiz karakterleri düzelt
    text = text.replace("…", ". ")
    text = re.sub(r"\.{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class GmailManagerTool(BaseTool):
    """Gmail gelen kutusu özetleme ve bülten aboneliği yönetim aracı."""

    name = "manage_gmail"
    description = (
        "Gmail gelen kutusunu inceler; gelen e-postaları kimden geldiği, konusu ve ne anlattığı ile birlikte sesli özetler; "
        "önemli ve önemsiz/bülten e-postaları sınıflandırır; bülten aboneliklerini tespit edip iptal eder. "
        "'Maillerimi oku', 'Son gelen mailim ne', 'Gelen kutumu özetle', 'Önemli maillerim var mı' gibi taleplerde bu aracı çağır."
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
                            "'summarize_inbox' (gelen kutusundaki önemli/okunmamış mailleri ve içeriklerini özetle), "
                            "'list_newsletters' (reklam ve bülten aboneliklerini listele), "
                            "'unsubscribe' (belirli bir bülten veya reklam aboneliğinden çık)"
                        ),
                        "enum": ["summarize_inbox", "list_newsletters", "unsubscribe"],
                    },
                    "query": {
                        "type": "STRING",
                        "description": "Arama filtresi (varsayılan: 'is:unread', örn: 'is:important', 'from:ahmet', 'in:inbox').",
                    },
                    "sender": {
                        "type": "STRING",
                        "description": "Abonelikten çıkılacak bülten veya gönderen adı (unsubscribe eylemi için).",
                    },
                    "max_results": {
                        "type": "INTEGER",
                        "description": "İncelenecek maksimum e-posta sayısı (varsayılan: 5, en fazla 10).",
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
            raw_name = match.group(1).strip()
        else:
            raw_name = from_value.split("@")[0].strip()
        return _clean_text_for_speech(raw_name)

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
        search_query = query or "is:unread"
        limit = min(max(1, max_results), 10)
        params = {"q": search_query, "maxResults": limit}
        resp = requests.get(GMAIL_MESSAGES_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return ToolResult(success=False, message="E-postalar alınamadı efendim.")

        messages_meta = resp.json().get("messages", [])

        # Eğer is:unread ile arandı ve sonuç boşsa, genel gelen kutusuna bak
        if not messages_meta and search_query == "is:unread":
            logger.info("Okunmamış e-posta bulunamadı, en son gelen e-postalara bakılıyor (in:inbox)...")
            fallback_resp = requests.get(
                GMAIL_MESSAGES_URL,
                headers=headers,
                params={"q": "in:inbox", "maxResults": limit},
                timeout=10,
            )
            if fallback_resp.status_code == 200:
                messages_meta = fallback_resp.json().get("messages", [])

        if not messages_meta:
            return ToolResult(
                success=True,
                message="Gelen kutunuzda okunmamış yeni e-posta bulunmuyor efendim.",
                data={"count": 0, "emails": []},
            )

        emails = []
        for msg in messages_meta[:limit]:
            msg_id = msg.get("id")
            detail_resp = requests.get(
                f"{GMAIL_MESSAGES_URL}/{msg_id}",
                headers=headers,
                timeout=10,
            )
            if detail_resp.status_code == 200:
                data = detail_resp.json()
                h_list = data.get("payload", {}).get("headers", [])
                from_hdr = self._extract_header(h_list, "From")
                subj_hdr = self._extract_header(h_list, "Subject") or "Konusuz"
                unsub_hdr = self._extract_header(h_list, "List-Unsubscribe")
                label_ids = data.get("labelIds", [])
                snippet = data.get("snippet", "")

                sender_clean = self._clean_sender_name(from_hdr)
                subject_clean = _clean_text_for_speech(subj_hdr)
                snippet_clean = _clean_text_for_speech(snippet)

                # Önem sınıflandırması:
                # Promosyon, sosyal bildirim veya bültenler 'önemsiz/bülten' kategorisine alınır.
                is_promo_or_social = any(
                    cat in label_ids
                    for cat in ["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_UPDATES", "CATEGORY_FORUMS"]
                ) or bool(unsub_hdr)

                is_important = (
                    "IMPORTANT" in label_ids
                    or "STARRED" in label_ids
                    or "CATEGORY_PERSONAL" in label_ids
                ) and not is_promo_or_social

                emails.append({
                    "id": msg_id,
                    "sender": sender_clean,
                    "subject": subject_clean,
                    "snippet": snippet_clean,
                    "is_important": is_important,
                    "category": "important" if is_important else "other",
                })

        count = len(messages_meta)
        if not emails:
            return ToolResult(
                success=True,
                message=f"Gelen kutunuzda {count} yeni e-posta var efendim.",
                data={"count": count, "emails": []},
            )

        # 1 E-posta Özeti (örn: "Son gelen mailim ne?")
        if len(emails) == 1:
            e = emails[0]
            snip_part = f" İçeriğinde özetle: {e['snippet']}." if e["snippet"] else ""
            spoken = f"Gelen son e-postanız {e['sender']} tarafından gönderilmiş, konusu '{e['subject']}'.{snip_part} efendim."

        # Çoklu E-posta Özeti (Önemli ve Diğer / Bülten olarak sınıflandırılmış)
        else:
            important_list = [e for e in emails if e["is_important"]]
            other_list = [e for e in emails if not e["is_important"]]

            parts = []
            if important_list:
                imp_descriptions = []
                for e in important_list[:3]:
                    desc = f"{e['sender']} '{e['subject']}'"
                    if e["snippet"]:
                        short_snip = e["snippet"][:65].strip()
                        desc += f" ({short_snip})"
                    imp_descriptions.append(desc)
                parts.append(f"Önemli görünenler: {', '.join(imp_descriptions)}")

            if other_list:
                senders = list(dict.fromkeys(e["sender"] for e in other_list))
                other_sample = ", ".join(senders[:3])
                if important_list:
                    parts.append(f"Kalan {len(other_list)} e-posta ise bülten ve bildirim kategorisinde: {other_sample}")
                else:
                    parts.append(f"Tümü bülten ve bildirim kategorisinde: {other_sample}")

            summary_body = ". ".join(parts)
            spoken = f"Gelen kutunuzda {count} yeni e-posta var. {summary_body} efendim."

        return ToolResult(
            success=True,
            message=spoken,
            data={"count": count, "emails": emails},
        )


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
