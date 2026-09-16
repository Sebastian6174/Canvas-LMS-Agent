import time
import requests
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from config import config

MIGRATION_POLL_INTERVAL_SEC = 3
MIGRATION_TIMEOUT_SEC = 300

# Canvas API Helper
def _canvas_request(method: str, endpoint: str, data: Optional[Dict] = None, custom_course_id: Optional[str] = None) -> Dict:
    """
    Función auxiliar que permite realizar peticiones a la API de Canvas
    """
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

def _list_all_course_files(course_id: str) -> List[Dict[str, Any]] | Dict[str, Any]:
    """
    Lista todos los archivos del curso (paginado).
    """
    all_files: List[Dict[str, Any]] = []
    page = 1
    while True:
        batch = _canvas_request(
            "GET",
            f"/files?per_page=100&page={page}",
            custom_course_id=course_id,
        )
        if isinstance(batch, dict) and "error" in batch:
            return batch
        if not isinstance(batch, list):
            break
        all_files.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return all_files


def _wait_for_content_migration(course_id: str, migration_id: int) -> Dict[str, Any]:
    """
    Espera a que se importen los recursos del curso base.
    """
    deadline = time.monotonic() + MIGRATION_TIMEOUT_SEC
    while time.monotonic() < deadline:
        status = _canvas_request(
            "GET",
            f"/content_migrations/{migration_id}",
            custom_course_id=course_id,
        )
        if "error" in status:
            return status

        state = status.get("workflow_state")
        if state == "completed":
            return status
        if state == "failed":
            return {
                "error": status.get("migration_issues_url") or "Content migration failed",
                "workflow_state": state,
            }

        time.sleep(MIGRATION_POLL_INTERVAL_SEC)

    return {"error": "Content migration timed out", "migration_id": migration_id}


@tool
def import_base_course_files(target_course_id: str, source_course_id: str) -> Dict:
    """
    Copia solo los archivos (imágenes, recursos) del curso plantilla al curso destino.
    No importa módulos, páginas, tareas ni foros.
    """
    source_files = _list_all_course_files(source_course_id)
    if isinstance(source_files, dict):
        return source_files

    file_ids = [f["id"] for f in source_files if f.get("id")]
    if not file_ids:
        print(f"No hay archivos en el curso plantilla {source_course_id}; se omite la migración.")
        return {"workflow_state": "skipped", "files_copied": 0}

    print(f"Importando {len(file_ids)} archivo(s) del curso plantilla {source_course_id}...")
    payload = {
        "migration_type": "course_copy_importer",
        "settings": {"source_course_id": str(source_course_id)},
        "select": {"files": file_ids},
    }
    migration = _canvas_request(
        "POST",
        "/content_migrations",
        payload,
        custom_course_id=target_course_id,
    )
    if "error" in migration:
        return migration

    migration_id = migration.get("id")
    if not migration_id:
        return {"error": "La migración no devolvió un ID"}

    result = _wait_for_content_migration(target_course_id, migration_id)
    if "error" not in result:
        result["files_copied"] = len(file_ids)
    return result

@tool
def create_module(name: str, course_id: Optional[str] = None) -> Dict:
    """
    Crea un nuevo módulo en el curso de Canvas.
    """
    payload = {"module": {"name": name, "published": True}}
    return _canvas_request("POST", "/modules", payload, custom_course_id=course_id)

@tool
def list_modules(course_id: Optional[str] = None) -> List[Dict]:
    """
    Lista todos los módulos existentes en el curso.
    """
    return _canvas_request("GET", "/modules", custom_course_id=course_id)

@tool
def publish_module(module_id: int, course_id: Optional[str] = None) -> Dict:
    """
    Publica un modulo existente en Canvas.
    """
    payload = {"module": {"published": True}}
    return _canvas_request("PUT", f"/modules/{module_id}", payload, custom_course_id=course_id)

@tool
def create_assignment(
    name: str,
    description: str,
    course_id: Optional[str] = None,
    points_possible: float = 0.0,
    submission_types: List[str] = ["online_upload"],
    assignment_group_id: Optional[int] = None,
    grading_type: str = "points",
    omit_from_final_grade: bool = False,
) -> Dict:
    """
    Crea o actualiza una actividad (assignment) en el curso de Canvas.
    Si ya existe una actividad con el mismo nombre, la actualiza para evitar duplicados.
    """
    assignments = _canvas_request("GET", "/assignments?per_page=100", custom_course_id=course_id)
    
    if isinstance(assignments, list):
        for a in assignments:
            if a.get("name", "").strip().lower() == name.strip().lower():
                assignment_id = a.get("id")
                print(f"La actividad '{name}' ya existe (ID: {assignment_id}). Actualizándola...")
                payload = {
                    "assignment": {
                        "description": description,
                        "points_possible": points_possible,
                        "submission_types": submission_types,
                        "grading_type": grading_type,
                        "omit_from_final_grade": omit_from_final_grade,
                        "published": True
                    }
                }
                if assignment_group_id is not None:
                    payload["assignment"]["assignment_group_id"] = assignment_group_id
                return _canvas_request("PUT", f"/assignments/{assignment_id}", payload, custom_course_id=course_id)
                
    payload = {
        "assignment": {
            "name": name,
            "description": description,
            "points_possible": points_possible,
            "submission_types": submission_types,
            "grading_type": grading_type,
            "omit_from_final_grade": omit_from_final_grade,
            "published": True
        }
    }
    if assignment_group_id is not None:
        payload["assignment"]["assignment_group_id"] = assignment_group_id
    return _canvas_request("POST", "/assignments", payload, custom_course_id=course_id)

@tool
def list_assignments(course_id: Optional[str] = None) -> List[Dict]:
    """
    Lista las actividades (assignments) existentes en el curso.
    """
    return _canvas_request("GET", "/assignments?per_page=100", custom_course_id=course_id)


@tool
def list_assignment_groups(course_id: Optional[str] = None) -> List[Dict]:
    """
    Lista los grupos de actividades del curso.
    """
    return _canvas_request("GET", "/assignment_groups?per_page=100", custom_course_id=course_id)


@tool
def enable_assignment_group_weights(course_id: Optional[str] = None) -> Dict:
    """
    Activa la ponderacion por grupos de actividades en el curso.
    """
    target_course_id = course_id or config.course_id
    payload = {"course": {"apply_assignment_group_weights": True}}
    return _canvas_request("PUT", f"/courses/{target_course_id}", payload, custom_course_id=target_course_id)


@tool
def create_or_update_assignment_group(
    name: str,
    group_weight: float,
    course_id: Optional[str] = None,
) -> Dict:
    """
    Crea o actualiza un grupo de actividades de Canvas.
    """
    groups = list_assignment_groups.invoke({"course_id": course_id})
    payload = {"name": name, "group_weight": group_weight}

    if isinstance(groups, list):
        for group in groups:
            if group.get("name", "").strip().lower() == name.strip().lower():
                group_id = group.get("id")
                print(f"El grupo de actividades '{name}' ya existe (ID: {group_id}). Actualizandolo...")
                return _canvas_request(
                    "PUT",
                    f"/assignment_groups/{group_id}",
                    payload,
                    custom_course_id=course_id,
                )

    return _canvas_request("POST", "/assignment_groups", payload, custom_course_id=course_id)


@tool
def delete_assignment(assignment_id: int, course_id: Optional[str] = None) -> Dict:
    """
    Elimina una actividad (assignment) del curso de Canvas.
    """
    return _canvas_request("DELETE", f"/assignments/{assignment_id}", custom_course_id=course_id)

def _rubric_creation_criteria(criteria: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Canvas creates real criterion/rating IDs. Sending synthetic IDs can make the
    Rubrics endpoint fail with a 500 instead of returning a validation error.
    Ratings must also be an indexed hash, not a JSON list; Canvas reads
    criterion_data[:ratings].values internally.
    """
    cleaned_criteria = {}
    for index, criterion in enumerate(criteria):
        cleaned = {
            key: value
            for key, value in criterion.items()
            if key not in {"id", "ratings"}
        }
        cleaned["ratings"] = {
            str(rating_index): {
                key: value
                for key, value in rating.items()
                if key not in {"id", "criterion_id"}
            }
            for rating_index, rating in enumerate(criterion.get("ratings", []))
        }
        cleaned_criteria[str(index)] = cleaned
    return cleaned_criteria

@tool
def create_or_update_assignment_rubric(
    title: str,
    criteria: List[Dict[str, Any]],
    assignment_id: int,
    course_id: Optional[str] = None,
    use_for_grading: bool = True,
) -> Dict:
    """
    Crea o actualiza una rúbrica de Canvas y la asocia a un assignment.
    """
    rubrics = _canvas_request("GET", "/rubrics?per_page=100", custom_course_id=course_id)
    rubric_id = None
    if isinstance(rubrics, list):
        for rubric in rubrics:
            if rubric.get("title", "").strip().lower() == title.strip().lower():
                rubric_id = rubric.get("id")
                break

    payload = {
        "rubric": {
            "title": title,
            "free_form_criterion_comments": False,
            "criteria": _rubric_creation_criteria(criteria),
        },
        "rubric_association": {
            "association_id": assignment_id,
            "association_type": "Assignment",
            "use_for_grading": use_for_grading,
            "purpose": "grading",
        },
    }

    if rubric_id:
        print(f"La rúbrica '{title}' ya existe (ID: {rubric_id}). Actualizándola...")
        return _canvas_request("PUT", f"/rubrics/{rubric_id}", payload, custom_course_id=course_id)

    return _canvas_request("POST", "/rubrics", payload, custom_course_id=course_id)

@tool
def add_item_to_module(module_id: int, title: str, type: str, content_id: Optional[Any] = None, page_url: Optional[str] = None, course_id: Optional[str] = None) -> Dict:
    """
    Agrega un ítem a un módulo existente.
    Si el tipo es 'Page', se debe proporcionar 'page_url' (el slug de la página).
    Para 'Assignment' o 'Discussion', se proporciona 'content_id'.
    Si el ítem ya existe en el módulo, retorna el ítem existente para evitar duplicidad.
    """
    existing_items = _canvas_request("GET", f"/modules/{module_id}/items?per_page=100", custom_course_id=course_id)
    if isinstance(existing_items, list):
        for item in existing_items:
            match = False
            if item.get("type") == type:
                if type == "Page" and page_url:
                    if item.get("page_url") == page_url or item.get("title", "").strip().lower() == title.strip().lower():
                        match = True
                elif content_id is not None:
                    if str(item.get("content_id")) == str(content_id) or item.get("title", "").strip().lower() == title.strip().lower():
                        match = True
                else:
                    if item.get("title", "").strip().lower() == title.strip().lower():
                        match = True
            if match:
                print(f"El ítem '{title}' de tipo '{type}' ya existe en el módulo {module_id}. Omitiendo adición.")
                return item

    payload = {
        "module_item": {
            "title": title,
            "type": type
        }
    }
    if type == "Page" and page_url:
        payload["module_item"]["page_url"] = page_url
    elif type == "SubHeader":
        pass
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
            "title": "Página de inicio",
            "body": body,
            "published": True
        }
    }
    return _canvas_request("PUT", "/front_page", payload, custom_course_id=course_id)


@tool
def update_course_syllabus(
    body: str,
    course_id: Optional[str] = None,
    make_default_view: bool = False,
    show_course_summary: bool = False,
) -> Dict:
    """
    Actualiza el contenido del Syllabus/Programa del curso en Canvas.
    """
    target_course_id = course_id or config.course_id
    payload = {
        "course": {
            "syllabus_body": body,
            "syllabus_course_summary": show_course_summary,
        }
    }
    if make_default_view:
        payload["course"]["default_view"] = "syllabus"

    return _canvas_request("PUT", f"/courses/{target_course_id}", payload, custom_course_id=target_course_id)


@tool
def create_page(title: str, body: str, course_id: Optional[str] = None) -> Dict:
    """
    Crea o actualiza una página wiki en el curso de Canvas.
    Si ya existe una página con el mismo título, la actualiza para evitar duplicados.
    """
    pages = _canvas_request("GET", "/pages?per_page=100", custom_course_id=course_id)
    
    if isinstance(pages, list):
        for p in pages:
            if p.get("title", "").strip().lower() == title.strip().lower():
                url_slug = p.get("url")
                print(f"La página '{title}' ya existe (slug: {url_slug}). Actualizándola...")
                payload = {
                    "wiki_page": {
                        "body": body,
                        "published": True
                    }
                }
                return _canvas_request("PUT", f"/pages/{url_slug}", payload, custom_course_id=course_id)
                
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
    Crea o actualiza un foro de discusión en el curso de Canvas.
    Si ya existe un foro con el mismo título, lo actualiza para evitar duplicados.
    """
    topics = _canvas_request("GET", "/discussion_topics?per_page=100", custom_course_id=course_id)
    
    if isinstance(topics, list):
        for t in topics:
            if t.get("title", "").strip().lower() == title.strip().lower():
                topic_id = t.get("id")
                print(f"El foro '{title}' ya existe (ID: {topic_id}). Actualizándolo...")
                payload = {
                    "message": message,
                    "published": True
                }
                return _canvas_request("PUT", f"/discussion_topics/{topic_id}", payload, custom_course_id=course_id)
                
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

@tool
def list_course_files(course_id: Optional[str] = None) -> List[Dict]:
    """
    Lista todos los archivos en el curso de Canvas.
    """
    return _list_all_course_files(course_id or config.course_id)
