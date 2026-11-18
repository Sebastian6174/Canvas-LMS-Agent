from config import config
from src.analysis.analyzer import analyze_course
from src.nodes.base import fail, proceed
from src.state import CourseState
from src.tools.doc_parser import read_google_doc


def analyst_node(state: CourseState) -> CourseState:
    """
    Lee el documento curricular e infiere toda la estructura del curso.
    Es el único nodo que interpreta el documento: los demás sólo usan el estado.
    """
    doc_id = state.get("doc_id")
    if not doc_id:
        return fail(state, "No doc_id provided in state", is_valid=False)

    print(f"Reading document {doc_id}...")
    tabs = read_google_doc(doc_id)
    if not tabs:
        return fail(state, "Failed to read Google Doc", is_valid=False)

    teacher_tabs = None
    if config.teacher_doc and config.teacher_doc != doc_id:
        teacher_tabs = read_google_doc(config.teacher_doc)

    try:
        print("Inferring course structure...")
        structure, teacher_bio, warnings = analyze_course(
            config.get_llm(),
            tabs,
            teacher_tabs,
            max_workers=config.analysis_concurrency,
        )
    except Exception as e:
        print(f"Error during LLM inference: {str(e)}")
        return fail(state, f"Error during LLM inference: {str(e)}", is_valid=False)

    for warning in warnings:
        print(f"Advertencia del analista: {warning}")
    print(
        f"Course structure inferred successfully: {len(structure.modules)} unidades, "
        f"{len(structure.activities)} actividades, {len(structure.rubrics)} rúbricas."
    )
    return proceed(state, course_structure=structure, teacher_info=teacher_bio, is_valid=True)
