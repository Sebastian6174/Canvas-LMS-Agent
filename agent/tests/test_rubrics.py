from src.state import CourseState, CourseStructure, Activity, Module, ScheduleItem, Rubric, RubricCriterion
from src.nodes.analyst import analyst_node
from src.nodes.rubrics_creator import rubrics_creator_node
from config import config

class MockStructuredLLM:
    def __init__(self, return_value):
        self.return_value = return_value

    def invoke(self, messages):
        return self.return_value

class MockLLM:
    def __init__(self, return_value):
        self.return_value = return_value

    def with_structured_output(self, schema):
        return MockStructuredLLM(self.return_value)

def test_rubrics_workflow(monkeypatch):
    # 1. Setup mock course structure with rubrics
    mock_rubric = Rubric(
        name="Rúbrica N. 1",
        criteria=[
            RubricCriterion(
                name="Criterio 1: Calidad",
                points=20.0,
                excelente="Trabajo excelente",
                en_desarrollo="Trabajo en desarrollo",
                basico="Trabajo básico",
                insuficiente="Trabajo insuficiente"
            )
        ]
    )
    
    mock_structure = CourseStructure(
        name="Curso de Prueba",
        academic_program="Ingeniería",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Profesor de Prueba",
        description="Descripción del curso",
        learning_outcomes=["RA1"],
        modules=[
            Module(name="Unidad 1. Introducción", description="U1 desc", activities=["Actividad 3"])
        ],
        activities=[
            Activity(
                name="Actividad 3",
                description="Hacer un reel sobre el conflicto",
                duration=10,
                activity_type="Otros",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=20.0,
                module_name="Unidad 1. Introducción",
                rubric="Rúbrica N. 1"
            )
        ],
        schedule=[
            ScheduleItem(week=1, activity_name="Actividad 3", time_commitment="10 horas")
        ],
        rubrics=[mock_rubric]
    )

    # 2. Mock analyst dependencies
    monkeypatch.setattr(
        "src.nodes.analyst.read_google_doc",
        lambda doc_id: [{"title": "1. INFO", "content": "algun contenido"}, {"title": "No1", "content": "tabla de rubrica"}]
    )
    
    # Mock LLM structure inference
    mock_llm = MockLLM(mock_structure)
    monkeypatch.setattr(config, "get_llm", lambda: mock_llm)

    # Execute analyst_node
    initial_state = {
        "doc_id": "mock_doc_id",
        "course_structure": None,
        "canvas_course_id": None,
        "module_mapping": None,
        "teacher_info": None,
        "is_valid": False,
        "errors": [],
    }
    
    analyst_result = analyst_node(initial_state)
    
    assert analyst_result["is_valid"] is True
    assert len(analyst_result["errors"]) == 0
    
    inferred = analyst_result["course_structure"]
    assert inferred is not None
    assert len(inferred.rubrics) == 1
    assert inferred.rubrics[0].name == "Rúbrica N. 1"
    assert inferred.rubrics[0].criteria[0].name == "Criterio 1: Calidad"

    # 3. Mock Canvas API for rubrics page creation
    created_pages = []
    added_items = []

    def mock_create_page(self, kwargs):
        created_pages.append(kwargs)
        return {"url": "rubricas-slug"}

    def mock_add_item_to_module(self, kwargs):
        added_items.append(kwargs)
        return {"id": 12345}

    # Inject tools mocks
    monkeypatch.setattr("src.nodes.rubrics_creator.create_page", type("T", (), {"invoke": mock_create_page})())
    monkeypatch.setattr("src.nodes.rubrics_creator.add_item_to_module", type("T", (), {"invoke": mock_add_item_to_module})())

    # Prepare state for rubrics_creator_node
    creator_state = {
        **analyst_result,
        "canvas_course_id": "canvas_123",
        "module_mapping": {"Introducción al curso y ayuda": 999},
        "course_files_map": {"bannercurso": "https://canvas/banner.png"}
    }

    # Execute rubrics_creator_node
    creator_result = rubrics_creator_node(creator_state)

    # Verify Rúbricas page was created
    assert creator_result.get("rubrics_page_url") == "rubricas-slug"
    assert len(created_pages) == 1
    assert created_pages[0]["title"] == "Rúbricas"
    
    body = created_pages[0]["body"]
    assert "RÚBRICAS DE EVALUACIÓN" in body
    assert "Criterio 1: Calidad" in body
    assert "Excelente" in body
    assert "Trabajo excelente" in body
    assert "20.0 pts" in body
    assert "https://canvas/banner.png" in body
    assert "Actividad 3" in body  # Must associate Rubric N. 1 to Actividad 3

    # Verify Rúbricas page was added to the introductory module
    assert len(added_items) == 1
    assert added_items[0]["module_id"] == 999
    assert added_items[0]["title"] == "Rúbricas"
    assert added_items[0]["type"] == "Page"
    assert added_items[0]["page_url"] == "rubricas-slug"
