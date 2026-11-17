"""Construcción del cliente LLM: Gemini directo o OpenRouter con reintento reducido."""

from langchain_openai import ChatOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/sebas/canvas-lms-agent",
    "X-Title": "Canvas LMS Agent",
}
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_MAX_RETRIES = 6
MIN_FALLBACK_TOKENS = 512


def _is_placeholder(value: str | None, placeholder: str) -> bool:
    return not value or placeholder in value


def _is_token_budget_error(error: Exception) -> bool:
    message = str(error)
    return "402" in message or "requires more credits" in message or "max_tokens" in message


class _FallbackRunnable:
    """Invoca el cliente principal y, si falla por créditos/tokens, reintenta con el reducido."""

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback

    def invoke(self, messages):
        try:
            return self._primary.invoke(messages)
        except Exception as error:
            if _is_token_budget_error(error):
                return self._fallback.invoke(messages)
            raise


class OpenRouterLLM:
    """Cliente OpenRouter que reintenta una vez con la mitad de tokens ante un 402."""

    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float = 0):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def invoke(self, messages):
        return _FallbackRunnable(self._client(), self._reduced_client()).invoke(messages)

    def with_structured_output(self, schema):
        return _FallbackRunnable(
            self._client().with_structured_output(schema),
            self._reduced_client().with_structured_output(schema),
        )

    def _reduced_client(self) -> ChatOpenAI:
        return self._client(max(MIN_FALLBACK_TOKENS, self.max_tokens // 2))

    def _client(self, max_tokens: int | None = None) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=OPENROUTER_BASE_URL,
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature,
            default_headers=OPENROUTER_HEADERS,
        )


def build_llm(settings):
    """Crea el LLM según las credenciales disponibles en `settings` (Gemini tiene prioridad)."""
    if not _is_placeholder(settings.google_api_key, "your_google_api_key"):
        print("Conectando directamente a Google AI Studio (Gemini)...")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            api_key=settings.google_api_key,
            model=settings.google_model.removeprefix("google/"),
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            max_retries=GEMINI_MAX_RETRIES,
        )

    if _is_placeholder(settings.openrouter_api_key, "your_openrouter_api_key"):
        raise ValueError("Debe configurar GOOGLE_API_KEY o OPENROUTER_API_KEY en el archivo .env")

    return OpenRouterLLM(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        max_tokens=settings.llm_max_tokens,
    )
