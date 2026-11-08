"""Google Gemini API Provider with tool calling, timeout handling, and model fallback."""

import logging
from typing import Any, Dict, List, Optional
from src.brain.provider_base import BaseBrainProvider, BrainResponse
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class GeminiProvider(BaseBrainProvider):
    """Google Gemini API sağlayıcısı (Otomatik zaman aşımı, yedek model ve Araç Motoru / Tool Calling destekli)."""

    FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.5-flash",
        timeout_ms: int = 12000,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self.tool_registry = tool_registry
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY tanımlanmamış!")
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout_ms),
            )
        return self._client

    def _call_api(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        client = self._get_client()
        from google.genai import types

        contents = []
        if audio_bytes:
            contents.append(
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            )
        contents.append(prompt)

        # Araç motoru kayıtlıysa Gemini için fonksiyon tanımlarını hazırla
        config = None
        if self.tool_registry:
            declarations = self.tool_registry.get_declarations()
            if declarations:
                config = types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=declarations)]
                )

        # Denenecek modeller listesi: Seçilen model başa, alternatifler arkaya
        models_to_try: List[str] = [self.model]
        for m in self.FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for candidate_model in models_to_try:
            try:
                logger.info(f"Gemini API modeli deneniyor: {candidate_model}")
                kwargs = {"model": candidate_model, "contents": contents}
                if config:
                    kwargs["config"] = config

                response = client.models.generate_content(**kwargs)

                # Fonksiyon çağrısı (function call) kontrolü (Çoklu / Parallel Tool Execution)
                function_calls = getattr(response, "function_calls", None)
                if function_calls and self.tool_registry:
                    results = []
                    tool_names = []
                    needs_conf = False
                    conf_prompt = None

                    for call in function_calls:
                        tool_name = call.name
                        tool_args = dict(call.args or {})
                        tool_names.append(tool_name)
                        logger.info(f"Gemini araç çağrısı talep etti: {tool_name}({tool_args})")

                        res = self.tool_registry.execute(tool_name, tool_args)
                        results.append(res)
                        if res.needs_confirmation:
                            needs_conf = True
                            conf_prompt = res.confirmation_prompt

                    combined_messages = " ".join([r.message for r in results if r.message])
                    if len(results) == 1:
                        tool_res_dict = results[0].model_dump()
                    else:
                        tool_res_dict = {
                            "success": all(r.success for r in results),
                            "results": [r.model_dump() for r in results],
                        }

                    return BrainResponse(
                        text=combined_messages.strip(),
                        provider="gemini",
                        tool_called=", ".join(tool_names),
                        tool_result=tool_res_dict,
                        needs_confirmation=needs_conf,
                        confirmation_prompt=conf_prompt,
                    )

                text = getattr(response, "text", "") or ""
                return BrainResponse(text=text.strip(), provider="gemini")

            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                # 503, 504, 429, timeout, deadline_exceeded veya geçici sunucu yoğunluklarında diğer modele geç
                is_transient = any(
                    err_code in err_str
                    for err_code in [
                        "503",
                        "504",
                        "429",
                        "timeout",
                        "deadline",
                        "unavailable",
                        "high demand",
                        "temporary",
                        "overloaded",
                    ]
                )
                if is_transient:
                    logger.warning(
                        f"Model ({candidate_model}) yanıt vermedi veya gecikti ({e}). Bir sonraki modele geçiliyor..."
                    )
                    continue
                else:
                    raise e

        if last_error:
            raise last_error
        return BrainResponse(text="", provider="gemini")

    def generate_response(
        self, prompt: str, audio_bytes: Optional[bytes] = None
    ) -> BrainResponse:
        res = self._call_api(prompt, audio_bytes)
        if isinstance(res, BrainResponse):
            return res
        return BrainResponse(text=str(res).strip(), provider="gemini")
