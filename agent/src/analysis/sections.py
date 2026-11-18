"""
Localiza las secciones del documento curricular y las convierte en texto para el LLM.

Los documentos siguen una plantilla con pestañas (información básica, alineación,
secuencia, actividades, rúbricas). Cuando una sección no se puede identificar por
el título de su pestaña, se usa el documento completo como respaldo.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from src.tools.doc_parser import blocks_to_text

Block = Dict[str, Any]
Tab = Dict[str, Any]

# Palabras del título de la pestaña que identifican cada sección.
SECTION_KEYWORDS = {
    "info": ("informacion",),
    "alignment": ("alineacion",),
    "sequence": ("secuencia", "experiencia"),
    "activities": ("actividades",),
    "rubrics": ("rubrica",),
}


def normalize(text: str) -> str:
    """Minúsculas, sin acentos ni signos: para comparar nombres."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def similarity(a: str, b: str) -> float:
    """Parecido entre dos nombres (0 a 1), tolerante a que uno contenga al otro."""
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.9 + 0.1 * (min(len(a), len(b)) / max(len(a), len(b)))
    return SequenceMatcher(None, a, b).ratio()


class DocumentSections:
    """Acceso por sección a las pestañas de un documento leído con `read_google_doc`."""

    def __init__(self, tabs: List[Tab]):
        self.tabs = tabs
        self._by_section: Dict[str, List[Tab]] = {name: [] for name in SECTION_KEYWORDS}
        for tab in tabs:
            section = self._classify(tab.get("title", ""))
            if section:
                self._by_section[section].append(tab)

    @staticmethod
    def _classify(title: str) -> Optional[str]:
        normalized = normalize(title)
        # "Alineación RA + AF + AE" no debe confundirse con la sección de actividades.
        for section in ("info", "alignment", "sequence", "rubrics", "activities"):
            if any(keyword in normalized for keyword in SECTION_KEYWORDS[section]):
                return section
        return None

    def has(self, section: str) -> bool:
        return bool(self._by_section.get(section))

    def blocks(self, *sections: str) -> List[Block]:
        """Bloques de las secciones pedidas; si falta alguna, los de todo el documento."""
        if not all(self.has(section) for section in sections):
            return [block for tab in self.tabs for block in _tab_blocks(tab)]
        return [
            block
            for section in sections
            for tab in self._by_section[section]
            for block in _tab_blocks(tab)
        ]

    def text(self, *sections: str) -> str:
        """Texto de las secciones pedidas; si falta alguna, el documento completo."""
        if not all(self.has(section) for section in sections):
            return self.full_text()
        return "\n\n".join(
            _tab_text(tab) for section in sections for tab in self._by_section[section]
        )

    def full_text(self) -> str:
        return "\n\n".join(_tab_text(tab) for tab in self.tabs)

    def tables(self, section: str) -> List[Block]:
        """Tablas de una sección identificada (lista vacía si no se identificó)."""
        if not self.has(section):
            return []
        return [
            block
            for tab in self._by_section[section]
            for block in _tab_blocks(tab)
            if block["type"] == "table"
        ]


def _tab_blocks(tab: Tab) -> List[Block]:
    if tab.get("blocks") is not None:
        return tab["blocks"]
    # Documentos sin estructura (p. ej. exportados de Office): cada línea es un párrafo.
    return [
        {"type": "paragraph", "text": line.strip()}
        for line in (tab.get("content") or "").splitlines()
        if line.strip()
    ]


def _tab_text(tab: Tab) -> str:
    return f"## {tab.get('title', '')}\n{blocks_to_text(_tab_blocks(tab))}"


def block_to_plain(block: Block) -> str:
    """Un bloque como texto corrido: cada celda en sus propias líneas."""
    if block["type"] == "paragraph":
        return block["text"]
    rows = ["\n".join(cell for cell in row if cell) for row in block["rows"]]
    return "\n\n".join(row for row in rows if row)


def first_cell(block: Block) -> str:
    """Primera celda no vacía de una tabla (suele ser su título)."""
    for row in block.get("rows", []):
        for cell in row:
            if cell.strip():
                return cell
    return ""


def labeled_cell(block: Block, label: str) -> Optional[str]:
    """Contenido de la fila cuya primera celda empieza por `label` (p. ej. 'Descripción')."""
    target = normalize(label)
    for row in block.get("rows", []):
        if row and normalize(row[0]).startswith(target):
            content = "\n".join(cell for cell in row[1:] if cell.strip())
            return content or None
    return None


def find_activity_block(tables: List[Block], number: int, name: str) -> Optional[Block]:
    """Tabla que describe la actividad: por número en el título y, si no, por nombre."""
    numbered = [
        table for table in tables if re.match(rf"\s*{number}\s*[.)]", first_cell(table))
    ]
    if len(numbered) == 1:
        return numbered[0]
    candidates = numbered or tables
    best = max(candidates, key=lambda table: similarity(first_cell(table), name), default=None)
    if best is not None and similarity(first_cell(best), name) >= 0.6:
        return best
    return None
