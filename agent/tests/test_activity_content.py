from src.activities.content import (
    SYSTEM_PROMPT,
    ActivityContent,
    generate_activity_content,
)
from src.activities.template import render_activity_html
from src.state import Activity


def _activity(**kwargs) -> Activity:
    data = {
        "name": "Actividad 1. Videoconferencia: Presentación del curso",
        "description": "Hoy damos inicio a la formación.",
        "duration": 3,
        "activity_type": "Videoconferencia",
        "evaluation_type": "Formativa",
        "related_learning_outcome": "RA1",
        "weight": 0,
        "resources": ["Ley 100 de 1993."],
    }
    data.update(kwargs)
    return Activity(**data)


class _LLM:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.messages = result, error, None

    def with_structured_output(self, schema):
        assert schema is ActivityContent
        return self

    def invoke(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.result


def test_prompt_includes_example_and_asks_to_infer_delivery():
    assert "Participe del encuentro sincr&oacute;nico." in SYSTEM_PROMPT
    assert "Resumen para el desarrollo de la actividad" in SYSTEM_PROMPT
    assert "infiérela" in SYSTEM_PROMPT


def test_missing_delivery_form_is_flagged_to_the_model():
    llm = _LLM(ActivityContent(description_html="<p>x</p>", delivery_form="Participe.", resources=[]))

    generate_activity_content(llm, _activity(delivery_form=""), week=2)

    human = llm.messages[1].content
    assert "NO INDICADA (debes inferirla)" in human
    assert "Semana: 2" in human


def test_model_output_is_used_and_cleaned():
    llm = _LLM(ActivityContent(
        description_html="```html\n<h2>Titulo</h2><p><span>Uno</span></p>\n<script>x</script>```",
        delivery_form="Participe del encuentro sincrónico.",
        resources=["Act1_Pres.pdf", ""],
    ))

    content = generate_activity_content(llm, _activity())

    assert "<h2>" not in content.description_html
    assert "<script>" not in content.description_html
    assert "<p><span>Uno</span></p>" in content.description_html
    assert content.delivery_form == "Participe del encuentro sincrónico."
    assert content.resources == ["Act1_Pres.pdf"]


def test_fallback_infers_delivery_from_activity_type():
    content = generate_activity_content(_LLM(error=RuntimeError("caído")), _activity(activity_type="Tarea"))

    assert content.delivery_form == "Envíe el documento a través de esta actividad en Canvas."
    assert content.description_html == "    <p><span>Hoy damos inicio a la formación.</span></p>"


def test_explicit_delivery_form_wins_in_fallback():
    content = generate_activity_content(None, _activity(delivery_form="Suba un video corto."))

    assert content.delivery_form == "Suba un video corto."


def test_render_matches_example_structure_and_links_course_files():
    files_map = {
        "bannercurso": "https://canvas.test/courses/5/files/10/preview",
        "act1presevolucionseguridadsocial": "https://canvas.test/courses/5/files/20/preview",
    }

    html = render_activity_html(
        description_html="    <p><span>Texto</span></p>",
        delivery_form="Participe del encuentro sincrónico.",
        resources=["Act1_Pres-EvolucionSeguridadSocial.pdf", "Ley 100 de 1993."],
        weight=0,
        evaluation_type="Formativa",
        duration=3,
        week=1,
        files_map=files_map,
        domain="canvas.test",
        course_id="5",
    )

    assert html.startswith('<h2><img id="13808"')
    assert 'src="https://canvas.test/courses/5/files/10/preview"' in html
    assert '<div style="text-align: justify;">' in html
    assert "</strong></span>&nbsp;</span>0%</p>" in html
    assert "<p>Participe del encuentro sincrónico.</p>" in html
    assert 'href="https://canvas.test/courses/5/files/20?wrap=1"' in html
    assert "<li>Ley 100 de 1993.</li>" in html
    assert "<ul>" in html and "<ol>" not in html
    assert html.count("Semana No. 1") == 2
    assert '<td style="text-align: center; border-style: dotted;">3</td>' in html
