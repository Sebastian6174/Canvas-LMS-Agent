from langgraph.graph import END

from src.routing import (
    CREATOR_NODES,
    has_errors,
    route_after_analyst,
    route_after_setup,
    route_after_modules,
)


def _base_state(**kwargs):
    return {
        "doc_id": "test-doc",
        "course_structure": None,
        "canvas_course_id": None,
        "module_mapping": None,
        "teacher_info": None,
        "alignment_page_url": None,
        "agenda_page_url": None,
        "forum_discussion_id": None,
        "credits_page_url": None,
        "is_valid": False,
        "errors": [],
        **kwargs,
    }


class TestHasErrors:
    def test_empty_errors(self):
        assert has_errors(_base_state()) is False

    def test_with_errors(self):
        assert has_errors(_base_state(errors=["fallo"])) is True


class TestRouteAfterAnalyst:
    def test_continue_when_valid(self):
        state = _base_state(is_valid=True, course_structure={"name": "x"})
        assert route_after_analyst(state) == "setup_course"

    def test_stop_when_invalid(self):
        assert route_after_analyst(_base_state(is_valid=False)) == END

    def test_stop_when_errors(self):
        state = _base_state(is_valid=True, course_structure={}, errors=["LLM error"])
        assert route_after_analyst(state) == END

    def test_stop_without_structure(self):
        state = _base_state(is_valid=True, course_structure=None)
        assert route_after_analyst(state) == END


class TestRouteAfterSetup:
    def test_continue_to_module_generator(self):
        state = _base_state(
            canvas_course_id="862",
            course_structure={"name": "Curso"},
        )
        assert route_after_setup(state) == "module_generator"

    def test_stop_without_course_id(self):
        state = _base_state(course_structure={"name": "Curso"})
        assert route_after_setup(state) == END

    def test_stop_with_errors(self):
        state = _base_state(
            canvas_course_id="862",
            course_structure={"name": "Curso"},
            errors=["Error al crear curso"],
        )
        assert route_after_setup(state) == END


class TestRouteAfterModules:
    def test_fan_out_to_creators(self):
        state = _base_state(module_mapping={"Introducción al curso y ayuda": 1})
        assert route_after_modules(state) == CREATOR_NODES

    def test_stop_without_mapping(self):
        assert route_after_modules(_base_state()) == END

    def test_stop_with_errors(self):
        state = _base_state(
            module_mapping={"M1": 1},
            errors=["Pipeline detenido"],
        )
        assert route_after_modules(state) == END


class TestCreatorNodes:
    def test_expected_parallel_nodes(self):
        assert len(CREATOR_NODES) == 5
        assert "page_creator" in CREATOR_NODES
        assert "module_generator" not in CREATOR_NODES
