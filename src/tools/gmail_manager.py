"""Gmail Management, Content Summarization, and Intelligent Auto-Labeling Tool for Jarvis."""

import base64
from collections import Counter
import html
import logging
import re
from typing import Any, Dict, List, Optional
import requests

from src.config import settings
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.google_auth import GoogleAuthManager

logger = logging.getLogger(__name__)

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_LABELS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/labels"


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


def _extract_body_text(payload: Dict[str, Any], max_chars: int = 1500) -> str:
    """Gmail mesaj payload'ından okunabilir düz metin gövdesini (plain text) çıkarır."""
    if not payload:
        return ""

    def _decode_data(d: Optional[str]) -> str:
        if not d:
            return ""
        try:
            padded = d + "=" * ((4 - len(d) % 4) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
            raw = re.sub(r"<style[\s\S]*?</style>", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = re.sub(r"https?://\S+|www\.\S+", "", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            return raw
        except Exception:
            return ""

    # 1. Doğrudan body kontrolü
    direct_data = payload.get("body", {}).get("data")
    if direct_data and payload.get("mimeType") == "text/plain":
        text = _decode_data(direct_data)
        if text:
            return text[:max_chars]

    # 2. Parçalar (parts) içinde text/plain ara
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            text = _decode_data(part.get("body", {}).get("data"))
            if text:
                return text[:max_chars]
        elif "parts" in part:
            nested = _extract_body_text(part, max_chars=max_chars)
            if nested:
                return nested

    # 3. text/html varsa HTML etiketlerini temizleyip kullan
    if direct_data:
        text = _decode_data(direct_data)
        if text:
            return text[:max_chars]

    for part in parts:
        if part.get("mimeType") == "text/html":
            text = _decode_data(part.get("body", {}).get("data"))
            if text:
                return text[:max_chars]

    return ""


def _determine_category(
    sender: str,
    subject: str,
    snippet: str,
    label_ids: Optional[List[str]] = None,
) -> str:
    """E-postanın gönderen, konu ve içerik bilgilerine göre semantik kategorisini belirler."""
    combined = f"{sender} {subject} {snippet}".lower()
    labels = label_ids or []

    # 1. Finans (Banka, fatura, ödeme, dekont, ekstre, POS, para transferi)
    finance_keywords = [
        "bank", "fatura", "ödeme", "odeme", "dekont", "ekstre", "hesap özeti", "kredi kartı",
        "garanti", "isbank", "iş bankası", "yapı kredi", "akbank", "ziraat", "qnb",
        "enpara", "papara", "halkbank", "vakıfbank", "pos", "iban", "havale", "eft",
        "tahsilat", "aws billing", "invoice", "receipt", "kripto", "binance", "vergi", "gib",
        "turkcell fatura", "vodafone fatura", "türk telekom fatura", "enerjisa", "iski",
        "ödendi", "ödeme alındı", "payment"
    ]
    if any(k in combined for k in finance_keywords):
        return "Finans"

    # 2. Sosyal Medya (LinkedIn, X, Instagram, YouTube, Facebook, Reddit, vb.)
    social_keywords = [
        "linkedin", "twitter", "instagram", "facebook", "youtube", "tiktok", "reddit",
        "pinterest", "threads", "discord", "paylaştı:", "bağlantı kurdu", "ağınızda",
        "takip etti", "kanalıma abone", "bildirim:", "sosyal medya", "social"
    ]
    if any(k in combined for k in social_keywords) or "CATEGORY_SOCIAL" in labels:
        return "Sosyal Medya"

    # 3. Alışveriş & Kargo (Sipariş, kargo takibi, e-ticaret)
    shopping_keywords = [
        "sipariş", "siparis", "kargo", "teslimat", "trendyol", "hepsiburada", "amazon.com.tr",
        "yemeksepeti", "getir", "yurtiçi kargo", "aras kargo", "mng kargo", "sürat kargo",
        "ptt kargo", "kargonuz yola çıktı", "siparişiniz alındı", "order confirmed", "tracking"
    ]
    if any(k in combined for k in shopping_keywords):
        return "Alışveriş & Kargo"

    # 4. Eğitim & Gelişim (Kurs, webinar, gelişim, eğitim rehberleri)
    education_keywords = [
        "eğitim", "egitim", "kurs", "webinar", "seminar", "rehber", "guide", "gelişim",
        "öğren", "udemy", "coursera", "iman gadzhi", "training", "ders", "masterclass"
    ]
    if any(k in combined for k in education_keywords):
        return "Eğitim & Gelişim"

    # 5. Bülten & Tanıtım (Pazarlama, indirim, promosyon)
    promo_keywords = [
        "indirim", "fırsat", "kampanya", "bülten", "newsletter", "promosyon", "özel teklif",
        "unsubscribe", "abonelikten çık", "reklam"
    ]
    if any(k in combined for k in promo_keywords) or "CATEGORY_PROMOTIONS" in labels:
        return "Bülten & Tanıtım"

    # 6. İş & Proje (Sprint, toplantı, müşteri, iş teklifi, kod)
    work_keywords = [
        "sprint", "proje", "toplantı", "meeting", "görüşme", "sunum", "sözleşme", "teklif",
        "müşteri", "yazılım", "github", "gitlab", "jira", "pull request", "kod inceleme",
        "task", "deadline", "iş birliği"
    ]
    if any(k in combined for k in work_keywords):
        return "İş & Proje"

    # 7. Varsayılan (Kişisel / Bireysel)
    return "Kişisel"


def _clean_summary_for_tts(text: str) -> str:
    """Yapay zekanın ürettiği özeti TTS için temizler ve tek 'efendim.' ile bitmesini garantiler."""
    if not text:
        return ""
    text = re.sub(r'[*_#`~]', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[\U00010000-\U0010ffff]|[\u200d\uFE0E\uFE0F]|[\u2600-\u27bf]|[\u2300-\u23ff]', '', text)
    text = text.replace('…', '. ')
    text = re.sub(r'\s+', ' ', text).strip()

    # efendim hitabını tekilleştir
    matches = list(re.finditer(r'\befendim\b', text, flags=re.IGNORECASE))
    if len(matches) > 1:
        new_text = ""
        last_idx = 0
        for m in matches[:-1]:
            new_text += text[last_idx:m.start()]
            last_idx = m.end()
        new_text += text[last_idx:]
        text = re.sub(r'\s+', ' ', new_text).strip()

    if not text.rstrip(" .!?,;").lower().endswith("efendim"):
        text = text.rstrip(" .!?,;") + " efendim."
    elif not text.endswith("."):
        text = text.rstrip(" .!?,;") + "."

    return text


class GmailManagerTool(BaseTool):
    """Gmail gelen kutusu özetleme, otomatik etiketleme ve bülten aboneliği yönetim aracı."""

    name = "manage_gmail"
    description = (
        "Gmail gelen kutusunu inceler; e-postaları konusuna göre (Finans, Sosyal Medya, İş & Proje, Eğitim & Gelişim, Alışveriş & Kargo) "
        "otomatik sınıflandırır, Gmail hesabınızda etiketlerini oluşturup basar ve ne anlattıklarını akıllıca özetler; bülten aboneliklerini iptal eder. "
        "'Maillerimi etiketle', 'Son gelen mailim ne', 'Finans maillerim var mı', 'Sosyal medya bildirimlerimi özetle' gibi taleplerde bu aracı çağır."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]

    def __init__(
        self,
        auth_manager: Optional[GoogleAuthManager] = None,
        api_key: Optional[str] = None,
        model: str = "gemini-3.5-flash",
        timeout_ms: int = 10000,
        client: Optional[Any] = None,
    ):
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self._client = client
        self._labels_cache: Dict[str, str] = {}

    def _get_client(self):
        if self._client is not None:
            return self._client

        effective_key = self.api_key or settings.GEMINI_API_KEY
        if not effective_key:
            return None

        try:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=effective_key,
                http_options=types.HttpOptions(timeout=self.timeout_ms),
            )
            return self._client
        except Exception as e:
            logger.warning(f"Gemini client başlatılamadı: {e}")
            return None

    def _get_or_create_label_id(self, label_name: str, headers: Dict[str, str]) -> Optional[str]:
        """Gmail'de belirtilen isimdeki etiketin ID'sini döner; yoksa yeni etiket oluşturur."""
        name_clean = label_name.strip()
        name_key = name_clean.lower()

        # 1. Önbellekte varsa doğrudan dön
        if name_key in self._labels_cache:
            return self._labels_cache[name_key]

        # 2. Gmail'deki mevcut etiketleri çek
        try:
            resp = requests.get(GMAIL_LABELS_URL, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for lbl in data.get("labels", []):
                    self._labels_cache[lbl.get("name", "").lower()] = lbl.get("id")

                if name_key in self._labels_cache:
                    return self._labels_cache[name_key]
        except Exception as e:
            logger.warning(f"Gmail etiketleri listelenirken hata: {e}")

        # 3. Etiket yoksa yeni etiket oluştur
        try:
            payload = {
                "name": name_clean,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            create_resp = requests.post(GMAIL_LABELS_URL, headers=headers, json=payload, timeout=10)
            if create_resp.status_code in (200, 201):
                new_lbl = create_resp.json()
                lbl_id = new_lbl.get("id")
                if lbl_id:
                    self._labels_cache[name_key] = lbl_id
                    logger.info(f"Gmail'de yeni etiket oluşturuldu: '{name_clean}' (ID: {lbl_id})")
                    return lbl_id
            elif create_resp.status_code == 409:
                return self._labels_cache.get(name_key)
        except Exception as e:
            logger.error(f"Gmail'de etiket oluşturulurken hata ({name_clean}): {e}")

        return None

    def _apply_label_to_message(self, message_id: str, label_name: str, headers: Dict[str, str]) -> bool:
        """Belirtilen e-postaya Gmail etiketi ekler."""
        if not label_name or not message_id:
            return False

        label_id = self._get_or_create_label_id(label_name, headers)
        if not label_id:
            return False

        try:
            modify_url = f"{GMAIL_MESSAGES_URL}/{message_id}/modify"
            resp = requests.post(
                modify_url,
                headers=headers,
                json={"addLabelIds": [label_id]},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"E-posta ({message_id}) '{label_name}' olarak etiketlendi.")
                return True
        except Exception as e:
            logger.warning(f"E-posta etiketlenirken hata ({message_id} -> {label_name}): {e}")

        return False

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
                            "'summarize_inbox' (gelen kutusundaki e-postaları konusuna göre etiketler ve akıllı sesli özet sunar), "
                            "'categorize_and_label' (gelen e-postaları konularına [Finans, Sosyal Medya, İş, Eğitim vb.] göre etiketleyip Gmail'de etiketlerini basar), "
                            "'list_newsletters' (reklam ve bülten aboneliklerini listele), "
                            "'unsubscribe' (belirli bir bülten veya reklam aboneliğinden çık)"
                        ),
                        "enum": ["summarize_inbox", "categorize_and_label", "list_newsletters", "unsubscribe"],
                    },
                    "category": {
                        "type": "STRING",
                        "description": "Filtrelenecek kategori (örn: 'Finans', 'Sosyal Medya', 'İş & Proje', 'Eğitim & Gelişim', 'Alışveriş & Kargo').",
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
                        "description": "İncelenecek maksimum e-posta sayısı (varsayılan: 5, en fazla 15).",
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

    def _synthesize_with_gemini(self, emails: List[Dict[str, Any]], user_query: str) -> Optional[str]:
        """Gemini modelini kullanarak e-postaları zeki bir yönetici sekreteri gibi okur ve mantıklı özet üretir."""
        client = self._get_client()
        if client is None or not emails:
            return None

        from google.genai import types

        prompt_parts = [
            f"Kullanıcının Talebi: {user_query or 'Gelen e-postaları etiketle ve özetle'}\n\n",
            f"Gelen Kutusu ({len(emails)} e-posta, etiketleri atandı):\n",
        ]
        for idx, e in enumerate(emails, start=1):
            body_preview = (e.get("body") or e.get("snippet") or "İçerik yok").strip()
            body_preview = body_preview[:1200]
            cat_label = e.get("category", "Genel")
            prompt_parts.append(
                f"[{idx}] Gönderen: {e['sender']}\n"
                f"Konu: {e['subject']}\n"
                f"Atanan Kategori/Etiket: {cat_label}\n"
                f"Tarih: {e.get('date', '')}\n"
                f"İçerik:\n{body_preview}\n\n"
            )

        system_instruction = (
            "Sen Jarvis adında son derece zeki, yetenekli ve saygılı bir masaüstü kişisel sekreterisin.\n"
            "Kullanıcının gelen kutusundaki e-postaları okuyup kategorilerine göre (Finans, Sosyal Medya, İş & Proje, Eğitim & Gelişim, Alışveriş & Kargo, Bülten & Tanıtım, Kişisel) "
            "organize ediyor ve sesli olarak raporluyorsun.\n\n"
            "ÖZETLEME VE ANALİZ KURALLARI:\n"
            "1. KESİNLİKLE e-postaların ham metnini veya başlığını dümdüz okuma. Kullanıcı bunu kesinlikle istemiyor.\n"
            "2. E-postaları dikkatle oku; kimin gönderdiğini, ne ile alakalı olduğunu, ana fikrini, teklif veya talep olup olmadığını anla.\n"
            "3. Raporunda kategorileri (Örn: Finans, Sosyal Medya, Eğitim) belirterek, e-postaların Gmail'de etiketlendiğini ve ne anlattıklarını 2-3 akıcı Türkçe cümleyle özetle.\n"
            "   - Örnek: 'Gelen kutunuzda 3 yeni e-posta var ve etiketlendi efendim. Finans kategorisinde; Garanti Bankası hesap ekstresi gönderilmiş. Sosyal Medya'da; Zafer Ayan kullanıcı arayüzü örnekleri paylaşmış. Eğitim kategorisinde ise; İman Gadzhi müşteri bulma stratejileri üzerine bir rehber aktarmış.'\n"
            "4. Asla emoji, link, teknik URL veya teknik kodları seslendirme. Tamamen doğal konuşma dili üret.\n"
            "5. Cümlenin sonunu saygılı bir şekilde tek bir 'efendim.' ile bitir."
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
        )

        models_to_try = [self.model]
        for m in self.FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        for candidate_model in models_to_try:
            try:
                logger.info(f"Gmail Gemini zeki özetleme deneniyor ({candidate_model})...")
                response = client.models.generate_content(
                    model=candidate_model,
                    contents="".join(prompt_parts),
                    config=config,
                )
                text = getattr(response, "text", "") or ""
                if text.strip():
                    cleaned = _clean_summary_for_tts(text.strip())
                    return cleaned
            except Exception as e:
                logger.warning(f"Model ({candidate_model}) ile özetleme başarısız: {e}")
                continue

        return None

    def execute(
        self,
        action: str = "summarize_inbox",
        query: str = "is:unread",
        category: Optional[str] = None,
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
            if action in ("summarize_inbox", "categorize_and_label"):
                return self._handle_summarize_and_label(
                    query=query,
                    category_filter=category,
                    max_results=max_results,
                    headers=headers,
                    is_categorize_only=(action == "categorize_and_label"),
                )
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

    def _handle_summarize_and_label(
        self,
        query: str,
        category_filter: Optional[str],
        max_results: int,
        headers: Dict[str, str],
        is_categorize_only: bool = False,
    ) -> ToolResult:
        search_query = query or "is:unread"
        limit = min(max(1, max_results), 15)
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
                message="Gelen kutunuzda okunmamış yeni bir e-posta bulunmuyor efendim.",
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
                payload = data.get("payload", {})
                h_list = payload.get("headers", [])
                from_hdr = self._extract_header(h_list, "From")
                subj_hdr = self._extract_header(h_list, "Subject") or "Konusuz"
                date_hdr = self._extract_header(h_list, "Date")
                unsub_hdr = self._extract_header(h_list, "List-Unsubscribe")
                label_ids = data.get("labelIds", [])
                snippet = data.get("snippet", "")
                body_text = _extract_body_text(payload)

                sender_clean = self._clean_sender_name(from_hdr)
                subject_clean = _clean_text_for_speech(subj_hdr)
                snippet_clean = _clean_text_for_speech(snippet)

                # Semantik Kategori Tespiti (Finans, Sosyal Medya, İş, Eğitim, vb.)
                category_name = _determine_category(
                    sender=sender_clean,
                    subject=subject_clean,
                    snippet=snippet_clean,
                    label_ids=label_ids,
                )

                # Gmail hesabında etiketi oluştur ve e-postaya bas
                self._apply_label_to_message(msg_id, category_name, headers)

                is_important = category_name in ("Finans", "İş & Proje", "Kişisel")

                emails.append({
                    "id": msg_id,
                    "sender": sender_clean,
                    "subject": subject_clean,
                    "snippet": snippet_clean,
                    "body": body_text or snippet_clean,
                    "date": date_hdr,
                    "category": category_name,
                    "is_important": is_important,
                })

        count = len(messages_meta)
        if not emails:
            return ToolResult(
                success=True,
                message=f"Gelen kutunuzda {count} yeni e-posta var efendim.",
                data={"count": count, "emails": []},
            )

        # Kategori filtresi varsa uygula (örn: "Finans maillerim")
        if category_filter:
            cf_lower = category_filter.strip().lower()
            emails = [e for e in emails if cf_lower in e["category"].lower()]
            if not emails:
                return ToolResult(
                    success=True,
                    message=f"'{category_filter}' kategorisinde yeni bir e-posta bulunmuyor efendim.",
                    data={"count": 0, "emails": []},
                )

        # Sadece etiketleme raporu istendiyse
        if is_categorize_only:
            cat_counts = Counter(e["category"] for e in emails)
            breakdown_list = [f"{count_val} adet {cat_name}" for cat_name, count_val in cat_counts.items()]
            breakdown_str = ", ".join(breakdown_list)
            spoken = (
                f"Gelen kutunuzdaki {len(emails)} e-posta başarıyla incelendi ve Gmail'de etiketlendi: "
                f"{breakdown_str} olarak düzenlendi efendim."
            )
            return ToolResult(
                success=True,
                message=spoken,
                data={"count": len(emails), "categories": dict(cat_counts), "emails": emails},
            )

        # 1. Öncelik: Gemini ile kategorileri de içeren zeki yönetici özeti al
        gemini_summary = self._synthesize_with_gemini(emails, search_query)
        if gemini_summary:
            spoken = gemini_summary
        else:
            # 2. Yedek: Gemini offline veya mock ortamında ise temiz kategorik özet
            cat_counts = Counter(e["category"] for e in emails)
            parts = []
            for cat_name, count_val in cat_counts.items():
                cat_emails = [e for e in emails if e["category"] == cat_name]
                senders = list(dict.fromkeys(e["sender"] for e in cat_emails))
                parts.append(f"{cat_name} kategorisinde {count_val} e-posta ({', '.join(senders[:2])})")
            body_summary = ". ".join(parts)
            spoken = f"Gelen kutunuzdaki {len(emails)} e-posta etiketlendi efendim: {body_summary}."

            if not spoken.rstrip(" .!?,;").lower().endswith("efendim"):
                spoken = spoken.rstrip(" .!?,;") + " efendim."
            elif not spoken.endswith("."):
                spoken = spoken.rstrip(" .!?,;") + "."

        return ToolResult(
            success=True,
            message=spoken,
            data={"count": len(emails), "emails": emails},
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

        logger.info(f"Kullanıcı onayı ile '{target}' abonelikten çıkarma işlemi icra ediliyor...")
        return ToolResult(
            success=True,
            message=f"{target} aboneliğiniz sonlandırıldı ve e-postalar temizlendi efendim.",
            data={"sender": target, "status": "unsubscribed"},
        )
