from src.nodes.activity_creator import activity_creator_node
from src.state import Activity, CourseStructure, Module


def test_activity_creator_deletes_stale_assignments(monkeypatch):
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
        modules=[Module(name="Unidad 1", description="U1", activities=["Actividad actual"])],
        activities=[
            Activity(
                name="Actividad actual",
                description="Contenido",
                duration=4,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=10,
                module_name="Unidad 1",
            )
        ],
        schedule=[],
    )
    deleted = []

    def mock_list_assignments(self, kwargs):
        return [
            {"id": 1, "name": "Actividad vieja"},
            {"id": 2, "name": "Actividad actual"},
        ]

    def mock_delete_assignment(self, kwargs):
        deleted.append(kwargs)
        return {"id": kwargs["assignment_id"]}

    def mock_create_assignment(self, kwargs):
        return {"id": 2}

    def mock_add_item_to_module(self, kwargs):
        return {"id": 99}

    monkeypatch.setattr(
        "src.nodes.activity_creator.list_assignments",
        type("T", (), {"invoke": mock_list_assignments})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.delete_assignment",
        type("T", (), {"invoke": mock_delete_assignment})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.create_assignment",
        type("T", (), {"invoke": mock_create_assignment})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.add_item_to_module",
        type("T", (), {"invoke": mock_add_item_to_module})(),
    )

    result = activity_creator_node(
        {
            "course_structure": structure,
            "canvas_course_id": "100",
            "module_mapping": {"Unidad 1": 10},
            "errors": [],
        }
    )

    assert result["canvas_assignment_ids"] == {"Actividad actual": 2}
    assert deleted == [{"assignment_id": 1, "course_id": "100"}]
