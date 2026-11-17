"""Archivos del curso en Canvas: mapa de archivos y resolución de enlaces en HTML."""

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

SYNONYMS = {
    "banner": "bannercurso",
    "foro": "botonforodudas",
    "dudas": "botonforodudas",
    "agenda": "agendaactividades",
    "cronograma": "agendaactividades",
    "preliminares": "botonactivpre",
    "actividadespreliminares": "botonactivpre",
    "u1": "botonu1",
    "u2": "botonu2",
    "u3": "botonu3",
    "u4": "botonu4",
    "u5": "botonu5",
    "u6": "botonu6",
    "resultados": "iconosresultadosap",
    "resultadosaprendizaje": "iconosresultadosap",
    "guia": "botonguiacurso",
    "guiacurso": "botonguiacurso",
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


def resolve_html_links(html_content: str, files_map: Dict[str, str], domain: str, course_id: str) -> str:
    """
    Parses the HTML and replaces placeholder URLs / filenames with actual Canvas URLs.
    Also updates any old course references (e.g. /courses/862 or /courses/863) to the new course_id.
    """
    if not html_content:
        return html_content
        
    # 1. Update course IDs in URLs (e.g. /courses/862 or /courses/863 or courses/146 -> /courses/course_id)
    html_content = re.sub(r'/courses/\d+', f'/courses/{course_id}', html_content)
    
    if not files_map:
        return html_content

    # 2. Resolve template file IDs (like /files/67711 or /files/66540) using files_map
    def replace_file_ref(match):
        old_id = match.group(1)
        key = f"old_id_{old_id}"
        new_id = file_id_from_url(files_map.get(key))
        return f"/files/{new_id}" if new_id else match.group(0)
        
    html_content = re.sub(r'/files/(\d+)', replace_file_ref, html_content)
    
    # 3. Resolve any filenames or local paths in src or href attributes
    def replace_src_href(match):
        attr = match.group(1) # src or href
        quote = match.group(2) # " or '
        val = match.group(3) # the path/url
        
        # If it's already a resolved canvas file path, skip it
        if "/files/" in val and not any(f"old_id_{old_id}" in files_map for old_id in TEMPLATE_FILE_ID_TO_FILENAME):
            return match.group(0)
            
        # Try to extract a filename
        normalized = normalize_filename(val)
        # Apply synonym mapping
        normalized = SYNONYMS.get(normalized, normalized)
        
        if normalized in files_map:
            new_url = files_map[normalized]
            new_id = file_id_from_url(new_url)
            if attr == "href" and new_id and not val.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                resolved_val = f"https://{domain}/courses/{course_id}/files/{new_id}/download?wrap=1"
            else:
                resolved_val = new_url
            return f'{attr}={quote}{resolved_val}{quote}'
            
        return match.group(0)
        
    html_content = re.compile(r'(src|href)=(["\'])(.*?)\2', re.IGNORECASE).sub(replace_src_href, html_content)
    
    # 4. Fix data-api-endpoint attributes
    def replace_api_endpoint(match):
        quote = match.group(1)
        val = match.group(2)
        
        # Check if it contains a file ID
        file_match = re.search(r'/files/(\d+)', val)
        if file_match:
            old_id = file_match.group(1)
            key = f"old_id_{old_id}"
            new_id = file_id_from_url(files_map.get(key))
            if new_id:
                new_endpoint = f"https://{domain}/api/v1/courses/{course_id}/files/{new_id}"
                return f'data-api-endpoint={quote}{new_endpoint}{quote}'
        new_val = re.sub(r'/courses/\d+', f'/courses/{course_id}', val)
        return f'data-api-endpoint={quote}{new_val}{quote}'
        
    html_content = re.compile(r'data-api-endpoint=(["\'])(.*?)\1', re.IGNORECASE).sub(replace_api_endpoint, html_content)
    
    return html_content


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
