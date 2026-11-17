import os
from pathlib import Path

from dotenv import load_dotenv

from .llm import build_llm

load_dotenv()

# Definir la raíz del proyecto para rutas absolutas
BASE_DIR = Path(__file__).parent.parent


def _env(*keys: str, default: str | None = None):
    """Primer valor no vacío entre las variables de entorno `keys`; si no hay, `default`."""
    for key in keys:
        val = os.getenv(key)
        if val is not None and val != "":
            return val
    return default


class Config:
    # Canvas
    domain = _env("DOMAIN", default="univallecolombia.instructure.com")
    course_id = _env("COURSE_ID", default="")
    base_course_id = _env("BASE_COURSE_ID", default="")
    canvas_api_token = _env("CANVAS_API_TOKEN", default="")

    create_new_course = _env("CREATE_NEW_COURSE", default="false").strip().lower() == "true"

    # Google Docs
    doc_id = _env("DOC_ID", default="")
    teacher_doc = _env("TEACHER_DOC", default="")
    credentials_path = BASE_DIR / "config" / "credentials.json"

    # LLM
    openrouter_api_key = _env("OPENROUTER_API_KEY")
    openrouter_model = _env("OPENROUTER_MODEL", default="inclusionai/ring-2.6-1t")
    # Valores por defecto reducidos para evitar errores por límite de créditos/tokens
    llm_max_tokens = int(_env("LLM_MAX_TOKENS", default="3000"))
    analysis_chunk_size = int(_env("ANALYSIS_CHUNK_SIZE", default="6000"))
    analysis_min_chunk_size = int(_env("ANALYSIS_MIN_CHUNK_SIZE", default="1200"))

    google_api_key = _env("GOOGLE_API_KEY")
    google_model = _env("GOOGLE_MODEL", default="gemini-2.5-flash")

    def get_llm(self):
        """Crea el LLM con los valores vigentes (incluye los overrides de una ejecución)."""
        return build_llm(self)
