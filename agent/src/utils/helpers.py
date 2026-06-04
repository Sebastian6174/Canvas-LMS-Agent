import re
import os
from typing import Dict, Any, List, Optional, Sequence

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


def build_home_page_nav_links(
    *,
    course_id: str,
    domain: str,
    module_mapping: Dict[str, int],
    course_module_names: Sequence[str],
    agenda_page_url: Optional[str],
    forum_discussion_id: Optional[int],
    intro_module_name: str,
) -> Dict[str, Any]:
    """URLs de navegación de la portada a módulos y páginas ya creados en Canvas."""
    base = f"https://{domain}/courses/{course_id}"
    links: Dict[str, Any] = {"units": []}

    if agenda_page_url:
        links["agenda"] = f"{base}/pages/{agenda_page_url}"
    if forum_discussion_id:
        links["forum"] = f"{base}/discussion_topics/{forum_discussion_id}"

    intro_id = module_mapping.get(intro_module_name)
    if intro_id:
        links["intro_module"] = f"{base}/modules/{intro_id}"

    for name in course_module_names:
        mod_id = module_mapping.get(name)
        if mod_id:
            links["units"].append(f"{base}/modules/{mod_id}")

    return links


def _replace_first_href_in_anchor(anchor: str, new_href: str) -> str:
    return re.sub(
        r'(\bhref=)(["\'])([^"\']*)(\2)',
        lambda m: f"{m.group(1)}{m.group(2)}{new_href}{m.group(2)}",
        anchor,
        count=1,
        flags=re.IGNORECASE,
    )


def _replace_href_in_anchors_with_markers(
    html: str, markers: Sequence[str], new_href: str
) -> str:
    pattern = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        anchor = match.group(0)
        anchor_lower = anchor.lower()
        if not any(marker in anchor_lower for marker in markers):
            continue
        new_anchor = _replace_first_href_in_anchor(anchor, new_href)
        return html[: match.start()] + new_anchor + html[match.end() :]
    return html


def apply_home_page_nav_links(
    html: str,
    nav_links: Dict[str, Any],
    course_id: str,
    domain: str,
) -> str:
    """Sustituye href de botones de portada por módulos/páginas/foro del curso actual."""
    if not html or not nav_links:
        return html

    if nav_links.get("forum"):
        forum_id = str(nav_links["forum"]).rstrip("/").split("/")[-1]
        html = re.sub(
            rf'href=(["\'])https?://{re.escape(domain)}/courses/\d+/discussion_topics/\d+\1',
            rf'href=\1{nav_links["forum"]}\1',
            html,
            flags=re.IGNORECASE,
        )
        html = re.sub(
            rf'data-api-endpoint=(["\'])https?://{re.escape(domain)}/api/v1/courses/\d+/discussion_topics/\d+\1',
            rf'data-api-endpoint=\1https://{domain}/api/v1/courses/{course_id}/discussion_topics/{forum_id}\1',
            html,
            flags=re.IGNORECASE,
        )
        html = _replace_href_in_anchors_with_markers(
            html,
            ("botonforodudas", "boton foro", "foro de dudas", "foro- preguntas"),
            nav_links["forum"],
        )

    if nav_links.get("agenda"):
        slug = nav_links["agenda"].rstrip("/").split("/")[-1]
        html = re.sub(
            rf'href=(["\'])https?://{re.escape(domain)}/courses/\d+/pages/[^"\']+\1',
            lambda m: (
                f'href={m.group(1)}{nav_links["agenda"]}{m.group(1)}'
                if "agenda" in m.group(0).lower()
                else m.group(0)
            ),
            html,
            flags=re.IGNORECASE,
        )
        html = re.sub(
            rf'data-api-endpoint=(["\'])https?://{re.escape(domain)}/api/v1/courses/\d+/pages/[^"\']+\1',
            lambda m: (
                f'data-api-endpoint={m.group(1)}https://{domain}/api/v1/courses/{course_id}/pages/{slug}{m.group(1)}'
                if "agenda" in m.group(0).lower()
                else m.group(0)
            ),
            html,
            flags=re.IGNORECASE,
        )
        html = _replace_href_in_anchors_with_markers(
            html,
            ("agendaactividades", "agenda de actividades"),
            nav_links["agenda"],
        )

    if nav_links.get("intro_module"):
        html = _replace_href_in_anchors_with_markers(
            html,
            ("botonactivpre", "actividades preliminares", "activpre", "boton_-activpre"),
            nav_links["intro_module"],
        )

    unit_markers = [
        ("botonu1", "unidad 1", 'alt="unidad 1"'),
        ("botonu2", "unidad 2", 'alt="unidad 2"'),
        ("botonu3", "unidad 3", 'alt="unidad 3"'),
        ("botonu4", "unidad 4", 'alt="unidad 4"'),
        ("botonu5", "unidad 5", 'alt="unidad 5"'),
        ("botonu6", "unidad 6", 'alt="unidad 6"'),
    ]
    units: List[str] = nav_links.get("units") or []
    for idx, unit_url in enumerate(units):
        if idx < len(unit_markers):
            html = _replace_href_in_anchors_with_markers(html, unit_markers[idx], unit_url)

    if units:
        module_href = re.compile(
            rf'(<a\b[^>]*\bhref=)(["\'])https?://{re.escape(domain)}/courses/\d+/modules/(\d+)\2',
            re.IGNORECASE,
        )
        unit_iter = iter(units)

        def _swap_module_href(match: re.Match) -> str:
            anchor_start = html.rfind("<a", 0, match.start())
            anchor_end = html.find("</a>", match.end())
            if anchor_start == -1 or anchor_end == -1:
                return match.group(0)
            anchor = html[anchor_start : anchor_end + 4]
            if (
                'data-api-returntype="Module"' not in anchor
                and "data-api-returntype='Module'" not in anchor
                and not re.search(r"unidad\s*\d", anchor, re.IGNORECASE)
            ):
                return match.group(0)
            try:
                new_url = next(unit_iter)
            except StopIteration:
                return match.group(0)
            return f"{match.group(1)}{match.group(2)}{new_url}{match.group(2)}"

        html = module_href.sub(_swap_module_href, html)

    return html


def extract_unit_number(label: str) -> Optional[int]:
    """Extrae el número de unidad de un texto (p. ej. 'Unidad 2. La negociación' -> 2)."""
    if not label:
        return None
    match = re.search(r"unidad\s*(\d+)", label, re.IGNORECASE)
    return int(match.group(1)) if match else None


def canonical_unit_names_by_number(modules: Sequence[Any]) -> Dict[int, str]:
    """Mapa número de unidad -> nombre canónico del módulo en el syllabus."""
    by_number: Dict[int, str] = {}
    for mod in modules:
        name = getattr(mod, "name", None) or (
            mod.get("name", "") if isinstance(mod, dict) else ""
        )
        num = extract_unit_number(name)
        if num is not None:
            by_number[num] = name
    return by_number


def activity_belongs_to_unit(activity_module_name: str, unit_name: str) -> bool:
    """
    Indica si una actividad pertenece a una unidad.
    Tolera 'Unidad 2' frente a 'Unidad 2. La negociación'.
    """
    act_ref = activity_module_name.strip().lower()
    unit_ref = unit_name.strip().lower()
    if not act_ref:
        return False
    if act_ref == unit_ref or act_ref in unit_ref or unit_ref in act_ref:
        return True
    act_num = extract_unit_number(activity_module_name)
    unit_num = extract_unit_number(unit_name)
    return act_num is not None and unit_num is not None and act_num == unit_num


def activities_for_unit(activities: Sequence[Any], unit_name: str) -> List[Any]:
    """Actividades de una unidad según module_name (fuente de verdad para asignación)."""
    matched = [
        act
        for act in activities
        if activity_belongs_to_unit(
            getattr(act, "module_name", "") or (
                act.get("module_name", "") if isinstance(act, dict) else ""
            ),
            unit_name,
        )
    ]
    return sorted(matched, key=lambda act: getattr(act, "number", 0))


def resolve_canonical_module_name(
    module_name: str,
    canonical_by_number: Dict[int, str],
) -> str:
    """Unifica module_name al nombre exacto del módulo definido en modules[]."""
    if not module_name.strip():
        return module_name
    for canonical in canonical_by_number.values():
        if activity_belongs_to_unit(module_name, canonical):
            return canonical
    num = extract_unit_number(module_name)
    if num is not None and num in canonical_by_number:
        return canonical_by_number[num]
    return module_name


def unit_intro_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Introducción y Resultados de Aprendizaje"


def unit_materials_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Materiales de estudio"


def build_course_banner_html(
    files_map: Dict[str, str],
    domain: str,
    course_id: str,
) -> str:
    """HTML del banner del curso para páginas de unidad."""
    banner_url = (
        files_map.get("bannercurso")
        or files_map.get("old_id_67711")
        or files_map.get("old_id_66540")
    )
    if banner_url:
        return (
            f'<h2><img style="display: block; margin-left: auto; margin-right: auto;" '
            f'src="{banner_url}" alt="Banner curso" width="100%" height="100%" /></h2>'
        )
    return (
        f'<h2><img style="display: block; margin-left: auto; margin-right: auto;" '
        f'src="https://{domain}/courses/{course_id}/files/67711/preview" '
        f'alt="Banner curso" width="100%" height="100%" '
        f'data-api-endpoint="https://{domain}/api/v1/courses/{course_id}/files/67711" '
        f'data-api-returntype="File" /></h2>'
    )


def collect_unit_resources(activities: Sequence[Any], unit_name: str) -> List[str]:
    """Recursos únicos de todas las actividades de una unidad, en orden de aparición."""
    seen: set[str] = set()
    resources: List[str] = []
    for act in activities_for_unit(activities, unit_name):
        act_resources = getattr(act, "resources", None) or (
            act.get("resources", []) if isinstance(act, dict) else []
        )
        for resource in act_resources or []:
            text = str(resource).strip()
            if text and text not in seen:
                seen.add(text)
                resources.append(text)
    return resources


def build_unit_intro_page_body(title: str) -> str:
    return f"<h1>{title}</h1>"


def build_unit_materials_page_body(banner_html: str, resources: Sequence[str]) -> str:
    items = "".join(f"<li>{r}</li>" for r in resources)
    list_html = f"<ul>{items}</ul>" if items else "<p><em>Sin recursos registrados para esta unidad.</em></p>"
    return f"{banner_html}\n{list_html}"
