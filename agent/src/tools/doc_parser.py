"""
Lectura de documentos de Google Docs conservando su estructura.

Cada pestaña se devuelve como una lista de bloques:
- {"type": "paragraph", "text": str}
- {"type": "table", "rows": [[celda, ...], ...]}

Dentro de una celda los párrafos se separan con "\\n", las viñetas se marcan
con "• ", las listas numeradas llevan su número, los desplegables aportan el
valor seleccionado y los enlaces ocultos tras un texto se anotan como
"texto (url)". Las celdas combinadas verticalmente repiten el valor superior.
"""

import os.path
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import config

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

BULLET = "• "
_NUMBERED_GLYPHS = {"DECIMAL", "ZERO_DECIMAL", "ALPHA", "UPPER_ALPHA", "ROMAN", "UPPER_ROMAN"}


def get_credentials():
    """Credenciales de la cuenta de servicio (config/credentials.json)."""
    if not os.path.exists(config.credentials_path):
        raise FileNotFoundError(
            f"Missing credentials.json at {config.credentials_path}. "
            "Please follow the Google Docs API guide to get a Service Account JSON file."
        )
    return service_account.Credentials.from_service_account_file(
        config.credentials_path, scopes=SCOPES
    )


class _TabRenderer:
    """Convierte el contenido de una pestaña en bloques de texto estructurado."""

    def __init__(self, lists: Optional[Dict[str, Any]] = None):
        self._lists = lists or {}
        self._counters: Dict[tuple, int] = {}

    # --- párrafos ---------------------------------------------------------

    def _run_text(self, element: Dict[str, Any]) -> str:
        if "textRun" in element:
            run = element["textRun"]
            text = run.get("content", "").replace("\x0b", "\n")
            url = (run.get("textStyle", {}).get("link") or {}).get("url")
            visible = text.strip()
            if url and visible and url.rstrip("/") not in visible and visible not in url:
                return text.rstrip("\n") + f" ({url})" + ("\n" if text.endswith("\n") else "")
            return text
        if "dropdown" in element:
            return element["dropdown"].get("dropdownProperties", {}).get("displayValue", "")
        if "person" in element:
            return element["person"].get("personProperties", {}).get("name", "")
        if "richLink" in element:
            props = element["richLink"].get("richLinkProperties", {})
            title, uri = props.get("title", ""), props.get("uri", "")
            return f"{title} ({uri})" if title and uri else title or uri
        return ""

    def _list_prefix(self, paragraph: Dict[str, Any]) -> str:
        bullet = paragraph.get("bullet")
        if not bullet:
            return ""
        list_id = bullet.get("listId", "")
        level = bullet.get("nestingLevel", 0)
        levels = (
            self._lists.get(list_id, {}).get("listProperties", {}).get("nestingLevels", [])
        )
        props = levels[level] if level < len(levels) else {}
        indent = "  " * level
        if props.get("glyphType") in _NUMBERED_GLYPHS:
            key = (list_id, level)
            number = self._counters.get(key, props.get("startNumber", 1) - 1) + 1
            self._counters[key] = number
            return f"{indent}{number}. "
        return f"{indent}{BULLET}"

    def paragraph(self, paragraph: Dict[str, Any]) -> str:
        text = "".join(self._run_text(el) for el in paragraph.get("elements", []))
        text = " ".join(text.replace("\n", " ").split())
        if not text:
            return ""
        return self._list_prefix(paragraph) + text

    # --- tablas -----------------------------------------------------------

    def cell(self, cell: Dict[str, Any]) -> str:
        lines = []
        for item in cell.get("content", []):
            if "paragraph" in item:
                line = self.paragraph(item["paragraph"])
                if line:
                    lines.append(line)
            elif "table" in item:
                for row in self.table(item["table"]):
                    lines.append(" | ".join(c.replace("\n", " ") for c in row))
        return "\n".join(lines)

    def table(self, table: Dict[str, Any]) -> List[List[str]]:
        rows: List[List[str]] = []
        carried: Dict[int, tuple] = {}  # columna -> (filas restantes, texto)
        for row in table.get("tableRows", []):
            cells: List[str] = []
            column = 0
            for cell in row.get("tableCells", []):
                style = cell.get("tableCellStyle", {})
                text = self.cell(cell)
                if column in carried and not text:
                    remaining, text = carried[column]
                    if remaining > 1:
                        carried[column] = (remaining - 1, text)
                    else:
                        del carried[column]
                elif style.get("rowSpan", 1) > 1:
                    carried[column] = (style["rowSpan"] - 1, text)
                cells.append(text)
                column += style.get("columnSpan", 1) or 1
            rows.append(cells)
        return rows

    def blocks(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        for element in content:
            if "paragraph" in element:
                text = self.paragraph(element["paragraph"])
                if text:
                    blocks.append({"type": "paragraph", "text": text})
            elif "table" in element:
                rows = self.table(element["table"])
                if any(any(cell for cell in row) for row in rows):
                    blocks.append({"type": "table", "rows": rows})
        return blocks


def blocks_to_text(blocks: List[Dict[str, Any]]) -> str:
    """Texto legible de los bloques: párrafos por línea y tablas con filas `| a | b |`."""
    parts: List[str] = []
    for block in blocks:
        if block["type"] == "paragraph":
            parts.append(block["text"])
        else:
            lines = [
                "| " + " | ".join(cell.replace("\n", " <br> ") for cell in row) + " |"
                for row in block["rows"]
            ]
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _tab(title: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"title": title, "content": blocks_to_text(blocks), "blocks": blocks}


def _collect_tabs(tabs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for tab in tabs:
        title = tab.get("tabProperties", {}).get("title", "Untitled Tab")
        document_tab = tab.get("documentTab")
        if document_tab:
            renderer = _TabRenderer(document_tab.get("lists"))
            results.append(_tab(title, renderer.blocks(document_tab.get("body", {}).get("content", []))))
        results.extend(_collect_tabs(tab.get("childTabs") or []))
    return results


def parse_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convierte la respuesta de la API de Docs en pestañas con bloques estructurados."""
    tabs = doc.get("tabs")
    if tabs:
        return _collect_tabs(tabs)
    # Documento sin pestañas (formato antiguo o simple)
    renderer = _TabRenderer(doc.get("lists"))
    return [_tab(doc.get("title", "Main Document"), renderer.blocks(doc.get("body", {}).get("content", [])))]


def _export_office_file(creds, doc_id: str) -> Optional[List[Dict[str, Any]]]:
    """Los archivos de Office no se pueden leer con la API de Docs; se exportan como texto."""
    print(f"El documento {doc_id} es un archivo de Office. Intentando exportar usando Drive API...")
    try:
        drive_service = build("drive", "v3", credentials=creds)
        content_bytes = drive_service.files().export_media(fileId=doc_id, mimeType="text/plain").execute()
    except Exception as export_err:
        print(
            "Advertencia: No se pudo exportar el archivo de Office (probablemente porque no es un "
            f"documento de Google Docs nativo). Se omitirá la lectura de este documento. Detalles: {export_err}"
        )
        return None
    text = content_bytes.decode("utf-8", errors="replace")
    blocks = [{"type": "paragraph", "text": line.strip()} for line in text.splitlines() if line.strip()]
    return [_tab("Documento Exportado", blocks)]


def read_google_doc(doc_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Lee un documento de Google y devuelve sus pestañas:
    [{"title": str, "content": str, "blocks": list}], o None si no se pudo leer.
    """
    try:
        creds = get_credentials()
        service = build("docs", "v1", credentials=creds)
        try:
            doc = service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        except Exception as api_err:
            if "Office file" in str(api_err):
                return _export_office_file(creds, doc_id)
            raise

        print(f"--- Document Title: {doc.get('title')} ---")
        return parse_document(doc)
    except Exception as err:
        print(f"An error occurred: {err}")
        return None
