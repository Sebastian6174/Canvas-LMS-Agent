"""Navegación de la página de inicio: enlaces a módulos, agenda y foro del curso."""

import re
from typing import Any, Dict, List, Optional, Sequence


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
