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
            
        return ChatOpenAI(
            api_key=cls.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=cls.openrouter_model,
            max_tokens=4096,
            default_headers={
                "HTTP-Referer": "https://github.com/sebas/canvas-lms-agent",
                "X-Title": "Canvas LMS Agent",
            }
        )