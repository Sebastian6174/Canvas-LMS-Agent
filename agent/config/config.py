import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Definir la raíz del proyecto para rutas absolutas
BASE_DIR = Path(__file__).parent.parent

def _env(*keys: str, default: str | None = None):
    for key in keys:
        val = os.getenv(key)
        if val is not None and val != "":
            return val
    return default

class Config:
    # Canvas
    domain = _env("DOMAIN", "univallecolombia.instructure.com")
    course_id = _env("COURSE_ID", "")
    base_course_id = _env("BASE_COURSE_ID", "")
    canvas_api_token = _env("CANVAS_API_TOKEN", "")
    
    create_new_course = _env("CREATE_NEW_COURSE", "false") == "true"

    # Google Docs
    doc_id = _env("DOC_ID", "")
    teacher_doc = _env("TEACHER_DOC", "")
    credentials_path = BASE_DIR / "config" / "credentials.json"
    
    # LLM
    openrouter_api_key = _env("OPENROUTER_API_KEY")
    openrouter_model = _env("OPENROUTER_MODEL", "inclusionai/ring-2.6-1t")
    # Reducir el valor por defecto para evitar errores por límite de créditos/tokens
    llm_max_tokens = int(_env("LLM_MAX_TOKENS", default="4000"))
    analysis_chunk_size = int(_env("ANALYSIS_CHUNK_SIZE", default="12000"))
    
    google_api_key = _env("GOOGLE_API_KEY")
    google_model = _env("GOOGLE_MODEL", "gemini-2.5-flash")
    
    # Método para crear una instancia del modelo de lenguaje
    @classmethod
    def get_llm(cls):
        if cls.google_api_key and "your_google_api_key" not in cls.google_api_key:
            print("Conectando directamente a Google AI Studio (Gemini)...")
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = cls.google_model
            if model_name.startswith("google/"):
                model_name = model_name[7:]
            return ChatGoogleGenerativeAI(
                api_key=cls.google_api_key,
                model=model_name,
                max_output_tokens=4096,
                max_retries=6,
            )

        if not cls.openrouter_api_key or "your_openrouter_api_key" in cls.openrouter_api_key:
            raise ValueError("Debe configurar GOOGLE_API_KEY o OPENROUTER_API_KEY en el archivo .env")
        class LLMWrapper:
            def __init__(self, api_key, model, max_tokens, temperature, headers):
                self.api_key = api_key
                self.model = model
                self.max_tokens = max_tokens
                self.temperature = temperature
                self.headers = headers

            def invoke(self, messages):
                # Intentar con el límite de tokens configurado; si falla por 402, reintentar con menos tokens
                try:
                    return self._client().invoke(messages)
                except Exception as e:
                    msg = str(e)
                    if "402" in msg or "requires more credits" in msg or "max_tokens" in msg:
                        # Reducir tokens a la mitad (pero no por debajo de 512) y reintentar una vez
                        reduced = max(512, int(self.max_tokens // 2))
                        try:
                            return self._client(reduced).invoke(messages)
                        except Exception:
                            raise
                    raise

            def with_structured_output(self, schema):
                structured = self._client().with_structured_output(schema)
                fallback = self._client(max(512, self.max_tokens // 2)).with_structured_output(schema)

                class StructuredWrapper:
                    def invoke(self, messages):
                        try:
                            return structured.invoke(messages)
                        except Exception as e:
                            message = str(e)
                            if "402" in message or "requires more credits" in message or "max_tokens" in message:
                                return fallback.invoke(messages)
                            raise

                return StructuredWrapper()

            def _client(self, max_tokens=None):
                return ChatOpenAI(
                    api_key=cls.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    model=cls.openrouter_model,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=self.temperature,
                    default_headers=self.headers,
                )

        return LLMWrapper(
            api_key=cls.openrouter_api_key,
            model=cls.openrouter_model,
            max_tokens=cls.llm_max_tokens,
            temperature=0,
            headers={
                "HTTP-Referer": "https://github.com/sebas/canvas-lms-agent",
                "X-Title": "Canvas LMS Agent",
            },
        )
