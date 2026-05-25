import requests
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from config import config

# Canvas API Helper
def _canvas_request(method: str, endpoint: str, data: Optional[Dict] = None, custom_course_id: Optional[str] = None) -> Dict:
    """Helper to make requests to the Canvas API."""
    domain = config.domain
    # Use custom_course_id if provided, otherwise fallback to config
    target_course_id = custom_course_id or config.course_id
    
    # If the endpoint starts with /accounts or /courses (full path), we don't prepend the courses prefix
    if endpoint.startswith("/accounts") or endpoint.startswith("/courses"):
        url = f"https://{domain}/api/v1{endpoint}"
    else:
        url = f"https://{domain}/api/v1/courses/{target_course_id}{endpoint}"
        
    headers = {
        "Authorization": f"Bearer {config.canvas_api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(method, url, headers=headers, json=data)
    
    if response.status_code not in [200, 201]:
        print(f"Error in Canvas API ({method} {url}): {response.status_code} - {response.text}")
        return {"error": response.text, "status_code": response.status_code}
    
    return response.json()

@tool
def create_course(name: str, course_code: str, account_id: str = "1") -> Dict:
    """
    Crea un nuevo curso en Canvas.
    Retorna el objeto del curso creado incluyendo su ID.
    """
    payload = {
        "course": {
            "name": name,
            "course_code": course_code,
            "enrollment_term_id": None,
            "license": "private"
        },
        "offer": True
    }
    return _canvas_request("POST", f"/accounts/{account_id}/courses", payload)

@tool
def import_base_course_content(target_course_id: str, source_course_id: str) -> Dict:
    """
    Importa el contenido (estructura, configuraciones) de un curso base a un curso destino.
    """
    payload = {
        "migration_type": "course_copy_importer",
        "settings": {
            "source_course_id": source_course_id
        }
    }
    return _canvas_request("POST", "/content_migrations", payload, custom_course_id=target_course_id)

@tool
def create_module(name: str, course_id: Optional[str] = None) -> Dict:
    """
    Crea un nuevo módulo en el curso de Canvas.
    """
    payload = {"module": {"name": name}}
    return _canvas_request("POST", "/modules", payload, custom_course_id=course_id)

@tool
def list_modules(course_id: Optional[str] = None) -> List[Dict]:
    """
    Lista todos los módulos existentes en el curso.
    """
    return _canvas_request("GET", "/modules", custom_course_id=course_id)

@tool
def create_assignment(name: str, description: str, course_id: Optional[str] = None, points_possible: float = 0.0, submission_types: List[str] = ["online_upload"]) -> Dict:
    """
    Crea una nueva actividad (assignment) en el curso de Canvas.
    """
    payload = {
        "assignment": {
            "name": name,
            "description": description,
            "points_possible": points_possible,
            "submission_types": submission_types,
            "published": True
        }
    }
    return _canvas_request("POST", "/assignments", payload, custom_course_id=course_id)

@tool
def add_item_to_module(module_id: int, title: str, type: str, content_id: Optional[Any] = None, page_url: Optional[str] = None, course_id: Optional[str] = None) -> Dict:
    """
    Agrega un ítem a un módulo existente.
    Si el tipo es 'Page', se debe proporcionar 'page_url' (el slug de la página).
    Para 'Assignment' o 'Discussion', se proporciona 'content_id'.
    """
    payload = {
        "module_item": {
            "title": title,
            "type": type
        }
    }
    if type == "Page" and page_url:
        payload["module_item"]["page_url"] = page_url
    elif content_id is not None:
        payload["module_item"]["content_id"] = content_id
        
    return _canvas_request("POST", f"/modules/{module_id}/items", payload, custom_course_id=course_id)

@tool
def update_course_home_page(body: str, course_id: Optional[str] = None) -> Dict:
    """
    Actualiza el contenido de la página de inicio del curso (Front Page).
    """
    payload = {
        "wiki_page": {
            "body": body,
            "published": True
        }
    }
    return _canvas_request("PUT", "/front_page", payload, custom_course_id=course_id)

@tool
def create_page(title: str, body: str, course_id: Optional[str] = None) -> Dict:
    """
    Crea una nueva página wiki en el curso de Canvas.
    Retorna el objeto de la página creada (incluye 'url' que sirve como page_url).
    """
    payload = {
        "wiki_page": {
            "title": title,
            "body": body,
            "published": True
        }
    }
    return _canvas_request("POST", "/pages", payload, custom_course_id=course_id)

@tool
def create_discussion_topic(title: str, message: str, course_id: Optional[str] = None) -> Dict:
    """
    Crea un nuevo foro de discusión (discussion topic) en el curso de Canvas.
    Retorna el objeto del foro creado (incluye 'id').
    """
    payload = {
        "title": title,
        "message": message,
        "published": True
    }
    return _canvas_request("POST", "/discussion_topics", payload, custom_course_id=course_id)

@tool
def set_module_position(module_id: int, position: int, course_id: Optional[str] = None) -> Dict:
    """
    Cambia la posición de un módulo en el curso.
    """
    payload = {"module": {"position": position}}
    return _canvas_request("PUT", f"/modules/{module_id}", payload, custom_course_id=course_id)
