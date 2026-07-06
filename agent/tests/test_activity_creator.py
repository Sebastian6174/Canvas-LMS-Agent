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
    created_groups = []
    created_assignments = []

    def mock_list_assignments(self, kwargs):
        return [
            {"id": 1, "name": "Actividad vieja"},
            {"id": 2, "name": "Actividad actual"},
        ]

    def mock_delete_assignment(self, kwargs):
        deleted.append(kwargs)
        return {"id": kwargs["assignment_id"]}

    def mock_create_assignment(self, kwargs):
        created_assignments.append(kwargs)
        return {"id": 2}

    def mock_add_item_to_module(self, kwargs):
        return {"id": 99}

    def mock_enable_assignment_group_weights(self, kwargs):
        return {"id": kwargs["course_id"]}

    def mock_create_or_update_assignment_group(self, kwargs):
        created_groups.append(kwargs)
        return {"id": 7}

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
        "src.nodes.activity_creator.enable_assignment_group_weights",
        type("T", (), {"invoke": mock_enable_assignment_group_weights})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.create_or_update_assignment_group",
        type("T", (), {"invoke": mock_create_or_update_assignment_group})(),
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
    assert created_groups == [{
        "name": "Evaluativas 10% c/u",
        "group_weight": 10.0,
        "course_id": "100",
    }]
    assert created_assignments[0]["points_possible"] == 5.0
    assert created_assignments[0]["assignment_group_id"] == 7
    assert created_assignments[0]["grading_type"] == "points"
    assert created_assignments[0]["omit_from_final_grade"] is False


def test_activity_creator_groups_evaluatives_by_weight(monkeypatch):
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
        activities=[
            Activity(
                name="Actividad 10 A",
                description="Contenido",
                duration=4,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=10,
                module_name="Unidad 1",
            ),
            Activity(
                name="Actividad 10 B",
                description="Contenido",
                duration=4,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=10,
                module_name="Unidad 1",
            ),
            Activity(
                name="Actividad 20",
                description="Contenido",
                duration=4,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=20,
                module_name="Unidad 1",
            ),
            Activity(
                name="Actividad formativa",
                description="Contenido",
                duration=4,
                activity_type="Foro",
                evaluation_type="Formativa",
                related_learning_outcome="RA1",
                weight=0,
                module_name="Unidad 1",
            ),
        ],
        schedule=[],
    )
    created_groups = []
    created_assignments = []
    group_ids = {
        "Evaluativas 10% c/u": 10,
        "Evaluativas 20% c/u": 20,
        "Formativas": 30,
    }

    monkeypatch.setattr(
        "src.nodes.activity_creator.list_assignments",
        type("T", (), {"invoke": lambda self, kwargs: []})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.enable_assignment_group_weights",
        type("T", (), {"invoke": lambda self, kwargs: {"id": kwargs["course_id"]}})(),
    )

    def mock_create_or_update_assignment_group(self, kwargs):
        created_groups.append(kwargs)
        return {"id": group_ids[kwargs["name"]]}

    def mock_create_assignment(self, kwargs):
        created_assignments.append(kwargs)
        return {"id": len(created_assignments)}

    monkeypatch.setattr(
        "src.nodes.activity_creator.create_or_update_assignment_group",
        type("T", (), {"invoke": mock_create_or_update_assignment_group})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.create_assignment",
        type("T", (), {"invoke": mock_create_assignment})(),
    )
    monkeypatch.setattr(
        "src.nodes.activity_creator.add_item_to_module",
        type("T", (), {"invoke": lambda self, kwargs: {"id": 99}})(),
    )

    activity_creator_node(
        {
            "course_structure": structure,
            "canvas_course_id": "100",
            "module_mapping": {"Unidad 1": 1},
            "errors": [],
        }
    )

    assert created_groups == [
        {"name": "Formativas", "group_weight": 0.0, "course_id": "100"},
        {"name": "Evaluativas 10% c/u", "group_weight": 20.0, "course_id": "100"},
        {"name": "Evaluativas 20% c/u", "group_weight": 20.0, "course_id": "100"},
    ]
    assert [a["points_possible"] for a in created_assignments] == [5.0, 5.0, 5.0, 0.0]
    assert [a["assignment_group_id"] for a in created_assignments] == [10, 10, 20, 30]
    assert [a["grading_type"] for a in created_assignments] == ["points", "points", "points", "not_graded"]
    assert [a["omit_from_final_grade"] for a in created_assignments] == [False, False, False, True]
