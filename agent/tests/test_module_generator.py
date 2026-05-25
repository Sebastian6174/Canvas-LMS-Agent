from src.nodes.module_generator import module_generator_node


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
