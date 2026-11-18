"""Archivos del curso en Canvas: mapa de archivos y banner."""

import os
import re
from typing import Any, Dict, List, Optional

# Mapping from old template file IDs to their normalized filenames
TEMPLATE_FILE_ID_TO_FILENAME = {
    # Course 630 files
    "54959": "Bannercurso.png",
    
    # Course 863 files (home page template)
    "67711": "Bannercurso.png",
    "67126": "Iconos_ResultadosAp.png",
    "67114": "Boton_ForoDudas.png",
    "67113": "AgendaActividades.png",
    "67119": "Boton_-ActivPre.png",
    "67116": "Boton_U1.png",
    "67117": "Boton_U2.png",
    "67118": "Boton_U3.png",
    "67128": "Holmes Sierra Cespedes.png",
    
    # Course 862 files (agenda, alignment, credits templates)
    "66540": "Bannercurso.png",
    "66539": "Iconos_ResultadosAp.png",
    "66532": "AgendaActividades.png",
    "66529": "Boton_ForoDudas.png",
    "66533": "Boton_-ActivPre.png",
    "66537": "Boton_U1.png",
    "66534": "Boton_U2.png",
    "66536": "Boton_U3.png",
    "66535": "Boton_GuiaCurso.png",
    "66541": "Holmes Sierra Cespedes.png"
}

def normalize_filename(name: str) -> str:
    """Normalizes a filename by extracting the basename, lowercasing, and removing extension and non-alphanumeric chars."""
    basename = os.path.basename(name)
    name_without_ext, _ = os.path.splitext(basename)
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', name_without_ext.lower())
    return cleaned

def build_course_files_map(course_files: List[Dict[str, Any]], domain: str, course_id: str) -> Dict[str, str]:
    """
    Builds a map from various keys to the actual Canvas file preview URL.
    Keys include:
      - filename (lowercase)
      - display_name (lowercase)
      - normalized filename
      - old template file IDs mapped to their new URLs
    """
    files_map = {}
    
    # First, index files in the course by their normalized and exact names
    for f in course_files:
        file_id = f.get("id")
        filename = f.get("filename") or ""
        display_name = f.get("display_name") or ""
        
        if not file_id:
            continue
            
        preview_url = f"https://{domain}/courses/{course_id}/files/{file_id}/preview"
        
        if filename:
            files_map[filename.lower()] = preview_url
            files_map[normalize_filename(filename)] = preview_url
        if display_name:
            files_map[display_name.lower()] = preview_url
            files_map[normalize_filename(display_name)] = preview_url
            
        # Also store the ID and the file object itself in case we need it
        files_map[f"id_{file_id}"] = str(file_id)
        
    # Now, for any old template IDs, map them directly to the new file URLs if we found the corresponding file name
    for old_id, filename in TEMPLATE_FILE_ID_TO_FILENAME.items():
        norm_name = normalize_filename(filename)
        # Try to find the file in the new course
        new_url = files_map.get(norm_name) or files_map.get(filename.lower())
        if new_url:
            files_map[f"old_id_{old_id}"] = new_url
            
    return files_map

def file_id_from_url(url: Optional[str]) -> Optional[str]:
    """ID de archivo de una URL de Canvas ('.../files/123/preview' -> '123')."""
    if not url or "/files/" not in url:
        return None
    return url.split("/files/")[1].split("/")[0].split("?")[0] or None


BANNER_FILE_KEYS = ("bannercurso", "old_id_54959", "old_id_67711", "old_id_66540")


def find_banner_url(files_map: Optional[Dict[str, str]]) -> Optional[str]:
    """URL del banner en el curso actual, si el archivo existe en el mapa."""
    if not files_map:
        return None
    return next((files_map[key] for key in BANNER_FILE_KEYS if files_map.get(key)), None)


# Banner de la plantilla, usado si el curso todavía no tiene el archivo.
FALLBACK_BANNER_FILE_ID = "67711"


def build_course_banner_html(
    files_map: Optional[Dict[str, str]],
    domain: str,
    course_id: str,
) -> str:
    """HTML del banner del curso (páginas de unidad y actividades)."""
    banner_url = find_banner_url(files_map)
    file_id = file_id_from_url(banner_url) or FALLBACK_BANNER_FILE_ID
    if not banner_url:
        banner_url = f"https://{domain}/courses/{course_id}/files/{file_id}/preview"
    return (
        '<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" '
        f'src="{banner_url}" alt="Banner curso" width="100%" height="100%" '
        f'data-api-endpoint="https://{domain}/api/v1/courses/{course_id}/files/{file_id}" '
        'data-api-returntype="File" /></h2>'
    )
