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
    base_course_id = _env("BASE_COURSE_ID", "")
    canvas_api_token = _env("CANVAS_API_TOKEN", "")
    base_url = f"https://{domain}/api/v1/courses/{course_id}"
    
    # Google Docs
    doc_id = _env("DOC_ID", "")
    credentials_path = BASE_DIR / "config" / "credentials.json"
    
    # LLM
    openrouter_api_key = _env("OPENROUTER_API_KEY")
    openrouter_model = _env("OPENROUTER_MODEL", "inclusionai/ring-2.6-1t")
    
    # Método para crear una instancia del modelo de lenguaje
    @classmethod
    def get_llm(cls):
        if not cls.openrouter_api_key or "your_openrouter_api_key" in cls.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY no está configurada correctamente en el archivo .env")
            
        return ChatOpenAI(
            api_key=cls.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=cls.openrouter_model,
            default_headers={
                "HTTP-Referer": "https://github.com/sebas/canvas-lms-agent",
                "X-Title": "Canvas LMS Agent",
            }
        )