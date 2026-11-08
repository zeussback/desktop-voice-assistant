"""Web browser opening and Google search tool."""

import logging
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


class WebBrowserTool(BaseTool):
    """Opens URLs or performs web searches in the user's default browser."""

    name = "open_web_browser"
    description = (
        "Varsayılan web tarayıcısında belirtilen web adresini (URL) açar veya "
        "Google'da arama yapar."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "description": "Tarayıcı eylemi: 'open_url' veya 'search_google'",
                        "enum": ["open_url", "search_google"]
                    },
                    "url": {
                        "type": "STRING",
                        "description": "Açılacak web adresi (örn: 'https://www.youtube.com' veya 'github.com')."
                    },
                    "query": {
                        "type": "STRING",
                        "description": "Google'da aranacak kelime veya soru."
                    }
                },
                "required": ["action"]
            }
        }

    def execute(
        self,
        action: str,
        url: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        try:
            if action == "open_url":
                if not url or not url.strip():
                    return ToolResult(
                        success=False,
                        message="Açmak için bir web adresi (URL) belirtmelisiniz efendim."
                    )
                clean_url = url.strip()
                if not clean_url.startswith(("http://", "https://")):
                    clean_url = "https://" + clean_url

                logger.info(f"Opening URL: {clean_url}")
                webbrowser.open(clean_url)
                return ToolResult(
                    success=True,
                    message=f"{clean_url} adresi tarayıcınızda açıldı efendim.",
                    data={"url": clean_url}
                )

            elif action == "search_google":
                if not query or not query.strip():
                    return ToolResult(
                        success=False,
                        message="Arama yapmak için bir arama ifadesi belirtmelisiniz efendim."
                    )
                clean_query = query.strip()
                encoded = urllib.parse.quote_plus(clean_query)
                search_url = f"https://www.google.com/search?q={encoded}"

                logger.info(f"Searching Google for '{clean_query}' via {search_url}")
                webbrowser.open(search_url)
                return ToolResult(
                    success=True,
                    message=f"'{clean_query}' için arama sonuçları açıldı efendim.",
                    data={"query": clean_query, "url": search_url}
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen tarayıcı eylemi: '{action}' efendim."
                )

        except Exception as e:
            logger.error(f"WebBrowserTool hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"Tarayıcı açılırken bir hata oluştu efendim: {str(e)}"
            )
