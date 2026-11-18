"""Piezas HTML compartidas por las páginas del curso en Canvas."""

import re
from html import escape
from typing import Dict, List, Optional, Sequence

from src.utils.course_files import file_id_from_url, normalize_filename

BULLET_PREFIX = re.compile(r"^\s*•\s*")
URL_IN_PARENS = re.compile(r"(?P<text>[^()\n]+?)\s*\((?P<url>https?://[^\s()]+)\)")
BARE_URL = re.compile(r"(?<![\"'=>])(https?://[^\s<]+)")


class CourseLinks:
    """Construye URLs y elementos de archivos del curso de Canvas."""

    def __init__(self, files_map: Optional[Dict[str, str]], domain: str, course_id: str):
        self.files_map = files_map or {}
        self.domain = domain
        self.course_id = course_id

    @property
    def base(self) -> str:
        return f"https://{self.domain}/courses/{self.course_id}"

    @property
    def api_base(self) -> str:
        return f"https://{self.domain}/api/v1/courses/{self.course_id}"

    def file_url(self, *names: str) -> Optional[str]:
        """URL de vista previa del primer archivo del curso que coincida con alguno de los nombres."""
        for name in names:
            url = self.files_map.get(normalize_filename(name)) or self.files_map.get(name.strip().lower())
            if url:
                return url
        return None

    def image(self, names: Sequence[str], alt: str, extra: str = "") -> str:
        """`<img>` de un archivo del curso, o cadena vacía si el archivo no existe."""
        url = self.file_url(*names)
        if not url:
            return ""
        file_id = file_id_from_url(url)
        endpoint = f' data-api-endpoint="{self.api_base}/files/{file_id}" data-api-returntype="File"' if file_id else ""
        return f'<img src="{url}" alt="{escape(alt)}"{(" " + extra) if extra else ""}{endpoint} />'

    def file_link(self, file_id: str, text: str) -> str:
        return (
            f'<a id="{file_id}" class="instructure_file_link instructure_scribd_file inline_disabled" '
            f'title="Enlace" href="{self.base}/files/{file_id}?wrap=1" target="_blank" '
            f'data-canvas-previewable="true" data-api-endpoint="{self.api_base}/files/{file_id}" '
            f'data-api-returntype="File" rel="noopener">{text}</a>'
        )


def esc(text: Optional[str]) -> str:
    return escape((text or "").strip(), quote=False)


def linkify(text: str) -> str:
    """Escapa el texto y convierte 'texto (url)' y las URL sueltas en enlaces."""
    parts: List[str] = []
    last = 0
    for match in URL_IN_PARENS.finditer(text):
        parts.append(_bare_links(escape(text[last:match.start()], quote=False)))
        url = escape(match.group("url"))
        parts.append(f'<a href="{url}" target="_blank" rel="noopener">{escape(match.group("text").strip(), quote=False)}</a>')
        last = match.end()
    parts.append(_bare_links(escape(text[last:], quote=False)))
    return "".join(parts)


def _bare_links(escaped: str) -> str:
    return BARE_URL.sub(lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', escaped)


def text_to_html(text: str, indent: str = "") -> str:
    """
    Texto del documento a HTML: cada línea es un párrafo y las líneas con '• '
    consecutivas forman una lista. Los enlaces se conservan.
    """
    out: List[str] = []
    bullets: List[str] = []

    def flush() -> None:
        if bullets:
            items = "".join(f"<li>{item}</li>" for item in bullets)
            out.append(f"{indent}<ul>{items}</ul>")
            bullets.clear()

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if BULLET_PREFIX.match(line):
            bullets.append(linkify(BULLET_PREFIX.sub("", line)))
            continue
        flush()
        out.append(f"{indent}<p><span>{linkify(line)}</span></p>")
    flush()
    return "\n".join(out)


def resource_item(resource: str, links: CourseLinks) -> str:
    """Un material de estudio: enlace al archivo del curso si existe; si no, su texto con enlaces."""
    text = BULLET_PREFIX.sub("", resource.strip())
    match = URL_IN_PARENS.fullmatch(text)
    name = match.group("text").strip() if match else text
    file_id = file_id_from_url(links.file_url(name))
    if file_id:
        return links.file_link(file_id, esc(name))
    return linkify(text)


def banner(links: CourseLinks) -> str:
    """Banner del curso centrado, igual en todas las páginas."""
    from src.utils.course_files import build_course_banner_html

    return build_course_banner_html(links.files_map, links.domain, links.course_id)


def ra_label(code: str) -> str:
    """'RA 1' -> 'R.A. 1' (formato de la tabla de alineación)."""
    match = re.search(r"(\d+)", code or "")
    return f"R.A. {match.group(1)}" if match else esc(code)


def split_indicator(indicator: str) -> tuple:
    """'1.1 Distingue…' -> ('1.1', 'Distingue…'); 'IL 2. Describe…' -> ('2', 'Describe…')."""
    match = re.match(r"^\s*(?:IL\s*)?(\d+(?:\.\d+)*)\.?\s+(.*)$", indicator or "", flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1), match.group(2).strip()
    return "", (indicator or "").strip()
