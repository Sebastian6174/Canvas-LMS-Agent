import re
import os
from typing import Dict, Any, List

# Mapping from old template file IDs to their normalized filenames
TEMPLATE_FILE_ID_TO_FILENAME = {
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
        if key in files_map:
            new_url = files_map[key]
            # Extract new ID from the new_url
            try:
                new_id = new_url.split('/files/')[1].split('/')[0]
                return f"/files/{new_id}"
            except Exception:
                pass
        return match.group(0)
        
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
            if attr == "href" and not val.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                try:
                    new_id = new_url.split('/files/')[1].split('/')[0]
                    resolved_val = f"https://{domain}/courses/{course_id}/files/{new_id}/download?wrap=1"
                except Exception:
                    resolved_val = new_url
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
            if key in files_map:
                new_url = files_map[key]
                try:
                    new_id = new_url.split('/files/')[1].split('/')[0]
                    new_endpoint = f"https://{domain}/api/v1/courses/{course_id}/files/{new_id}"
                    return f'data-api-endpoint={quote}{new_endpoint}{quote}'
                except Exception:
                    pass
        new_val = re.sub(r'/courses/\d+', f'/courses/{course_id}', val)
        return f'data-api-endpoint={quote}{new_val}{quote}'
        
    html_content = re.compile(r'data-api-endpoint=(["\'])(.*?)\1', re.IGNORECASE).sub(replace_api_endpoint, html_content)
    
    return html_content
