from src.nodes.module_generator import module_generator_node
from src.state import CourseStructure, Module


def _state_with_errors():
    return {
        "doc_id": "x",
        "course_structure": None,
        "canvas_course_id": "862",
        "module_mapping": None,
        "errors": ["Error en page_creator"],
        "is_valid": True,
    }


def test_module_generator_skips_when_prior_errors(monkeypatch):
    monkeypatch.setattr(
        "src.nodes.module_generator.create_module",
        type("T", (), {"invoke": lambda *a, **k: {"id": 1}})(),
    )
    result = module_generator_node(_state_with_errors())
    assert any("Pipeline detenido" in e for e in result.get("errors", []))
    assert result.get("module_mapping") is None


def test_module_generator_publishes_existing_modules(monkeypatch):
    structure = CourseStructure(
        name="Curso",
        academic_program="Prog",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Docente",
        description="Desc",
        learning_outcomes=["RA1"],
        modules=[Module(name="Unidad 1", description="U1", activities=[])],
        activities=[],
        schedule=[],
    )
    published = []

    def mock_list_modules(self, kwargs):
        return [
            {"id": 1, "name": "Introducción al curso y ayuda"},
            {"id": 2, "name": "Créditos"},
            {"id": 3, "name": "Unidad 1"},
        ]

    def mock_publish_module(self, kwargs):
        published.append(kwargs)
        return {"id": kwargs["module_id"], "published": True}

    monkeypatch.setattr(
        "src.nodes.module_generator.list_modules",
        type("T", (), {"invoke": mock_list_modules})(),
    )
    monkeypatch.setattr(
        "src.nodes.module_generator.publish_module",
        type("T", (), {"invoke": mock_publish_module})(),
    )

    result = module_generator_node(
        {
            "course_structure": structure,
            "canvas_course_id": "100",
            "errors": [],
        }
    )

    assert result["module_mapping"]["Unidad 1"] == 3
    assert published == [
        {"module_id": 1, "course_id": "100"},
        {"module_id": 2, "course_id": "100"},
        {"module_id": 3, "course_id": "100"},
    ]
