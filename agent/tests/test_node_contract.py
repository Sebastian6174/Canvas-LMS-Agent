"""Los nodos secuenciales sólo deben devolver errores nuevos (el reducer los acumula)."""

from src.nodes.activity_creator import activity_creator_node
from src.nodes.base import fail, proceed
from src.nodes.rubrics_creator import rubrics_creator_node
from src.nodes.syllabus_creator import syllabus_creator_node
from src.nodes.unit_pages_creator import unit_pages_creator_node


def test_proceed_never_repeats_existing_errors():
    state = {"doc_id": "d", "errors": ["previo"]}

    result = proceed(state, canvas_course_id="1")

    assert result["errors"] == []
    assert result["canvas_course_id"] == "1"
    assert result["doc_id"] == "d"


def test_fail_reports_only_the_new_error():
    result = fail({"errors": ["previo"]}, "nuevo", is_valid=False)

    assert result["errors"] == ["nuevo"]
    assert result["is_valid"] is False


def test_skipped_nodes_do_not_duplicate_prior_errors():
    state = {"errors": ["Error en page_creator"]}

    for node in (
        unit_pages_creator_node,
        activity_creator_node,
        rubrics_creator_node,
        syllabus_creator_node,
    ):
        assert node(state)["errors"] == []
