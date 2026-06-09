from langgraph.graph import END

from src.graph import create_graph
from src.routing import CREATOR_NODES


def test_graph_compiles():
    graph = create_graph()
    assert graph is not None


def test_graph_has_conditional_entry_points():
    g = create_graph().get_graph()
    node_names = set(g.nodes.keys())

    assert "analyst" in node_names
    assert "setup_course" in node_names
    assert "module_generator" in node_names
    assert "populate_special_modules" in node_names
    assert "unit_pages_creator" in node_names
    assert "activity_creator" in node_names
    assert "rubrics_creator" in node_names

    for creator in CREATOR_NODES:
        assert creator in node_names


def test_analyst_failure_does_not_reach_setup(monkeypatch):
    """Con is_valid=False el grafo debe terminar sin invocar setup_course."""

    from src.nodes import analyst as analyst_module

    def fake_analyst(state):
        return {
            **state,
            "is_valid": False,
            "errors": ["Inferencia simulada fallida"],
        }

    monkeypatch.setattr(analyst_module, "analyst_node", fake_analyst)

    from src import graph as graph_module

    monkeypatch.setattr(graph_module, "analyst_node", fake_analyst)
    compiled = graph_module.create_graph()

    result = compiled.invoke(
        {
            "doc_id": "fake",
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
        }
    )

    assert result["is_valid"] is False
    assert result.get("canvas_course_id") is None
    assert "Inferencia simulada fallida" in result.get("errors", [])
