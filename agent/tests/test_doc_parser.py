from src.tools.doc_parser import blocks_to_text, parse_document


def _run(text, **style):
    return {"textRun": {"content": text, "textStyle": style}}


def _paragraph(*elements, bullet=None):
    paragraph = {"elements": list(elements)}
    if bullet:
        paragraph["bullet"] = bullet
    return {"paragraph": paragraph}


def _cell(*paragraphs, row_span=1):
    return {"content": list(paragraphs), "tableCellStyle": {"rowSpan": row_span}}


def test_parses_tables_dropdowns_links_bullets_and_merged_cells():
    dropdown = {"dropdown": {"dropdownProperties": {"displayValue": "A. Evaluativa"}}}
    doc = {
        "tabs": [{
            "tabProperties": {"title": "3. SECUENCIA"},
            "documentTab": {
                "lists": {"L1": {"listProperties": {"nestingLevels": [{"glyphType": "DECIMAL", "startNumber": 1}]}}},
                "body": {"content": [
                    _paragraph(_run("Introducción\n")),
                    {"table": {"tableRows": [
                        {"tableCells": [_cell(_paragraph(_run("1\n")), row_span=2), _cell(_paragraph(_run("Tarea\n"))), _cell(_paragraph(dropdown))]},
                        {"tableCells": [_cell(_paragraph(_run("\n"))), _cell(_paragraph(_run("Foro\n"))), _cell(_paragraph(_run("Ver guía", link={"url": "https://x.org/g"}), _run("\n")))]},
                    ]}},
                    _paragraph(_run("Primero\n"), bullet={"listId": "L1"}),
                    _paragraph(_run("Segundo\n"), bullet={"listId": "L1"}),
                    _paragraph(_run("Viñeta\n"), bullet={"listId": "otra"}),
                ]},
            },
        }],
    }

    tab = parse_document(doc)[0]

    assert tab["title"] == "3. SECUENCIA"
    table = tab["blocks"][1]["rows"]
    assert table[0] == ["1", "Tarea", "A. Evaluativa"]
    assert table[1] == ["1", "Foro", "Ver guía (https://x.org/g)"]  # semana combinada se repite
    texts = [b["text"] for b in tab["blocks"] if b["type"] == "paragraph"]
    assert texts == ["Introducción", "1. Primero", "2. Segundo", "• Viñeta"]
    assert "| 1 | Tarea | A. Evaluativa |" in tab["content"]


def test_multiline_cells_render_with_br_in_text():
    blocks = [{"type": "table", "rows": [["Descripción:", "Uno\nDos"]]}]

    assert blocks_to_text(blocks) == "| Descripción: | Uno <br> Dos |"
