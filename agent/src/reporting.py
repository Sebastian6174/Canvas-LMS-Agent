from config import config
from src.routing import CREATOR_NODES


CONTENT_ERROR_KEYWORDS = (
    "agenda",
    "alineacion",
    "alineaci",
    "foro",
    "creditos",
    "credit",
    "page_creator",
    "html",
)


def print_pipeline_report(final_state: dict) -> int:
    """Print each pipeline stage result. Returns exit code: 0 means success."""
    errors = final_state.get("errors") or []
    structure = final_state.get("course_structure")

    _print_report_header()

    if not _report_analyst(final_state, structure, errors):
        return 1
    if not _report_canvas_setup(final_state, errors):
        return 1
    if not _report_content(final_state, errors):
        return 1
    if not _report_modules(final_state, errors):
        return 1

    _report_activities(final_state, structure, errors)
    return _report_final_status(errors)


def print_errors(errors: list) -> None:
    if not errors:
        return
    print("\nErrores registrados:")
    for index, error in enumerate(errors, 1):
        print(f"  {index}. {error}")


def _status(ok: bool) -> str:
    return "OK" if ok else "FALLO"


def _print_report_header() -> None:
    print("\n" + "=" * 60)
    print("REPORTE DEL PIPELINE - Canvas LMS Agent")
    print("=" * 60)


def _print_course_summary(structure) -> None:
    print(f"  Programa: {structure.academic_program}")
    print(f"  Semestre: {structure.semester}")
    print(f"  Docente: {structure.teacher}")
    print(f"  Unidades: {len(structure.modules)}")
    print(f"  Actividades: {len(structure.activities)}")


def _report_analyst(final_state: dict, structure, errors: list) -> bool:
    analyst_ok = final_state.get("is_valid") and structure is not None
    print(f"\n[1] Analista (inferencia desde Google Doc): {_status(analyst_ok)}")
    if structure:
        _print_course_summary(structure)
    if final_state.get("teacher_info"):
        print("  Info docente adicional: cargada")
    elif config.teacher_doc:
        print("  Info docente adicional: no disponible (revisar permisos TEACHER_DOC)")

    if analyst_ok:
        return True

    print("\nPipeline detenido tras el analista.")
    print_errors(errors)
    return False


def _report_canvas_setup(final_state: dict, errors: list) -> bool:
    course_id = final_state.get("canvas_course_id")
    setup_ok = bool(course_id) and not any(
        error.startswith("Error al crear curso") or error.startswith("COURSE_ID")
        for error in errors
    )
    print(f"\n[2] Configuracion del curso en Canvas: {_status(setup_ok)}")
    if course_id:
        print(f"  Curso Canvas ID: {course_id}")
    if config.base_course_id:
        print(f"  Curso base configurado: {config.base_course_id}")

    if setup_ok:
        return True

    print("\nPipeline detenido tras la configuracion del curso.")
    print_errors(errors)
    return False


def _report_content(final_state: dict, errors: list) -> bool:
    print(f"\n[3] Contenido en Canvas ({len(CREATOR_NODES) - 1} nodos en paralelo + pagina de inicio):")
    content_checks = {
        "Pagina de inicio": not any("page_creator" in error.lower() for error in errors),
        "Agenda de actividades": bool(final_state.get("agenda_page_url")),
        "Alineacion de actividades": bool(final_state.get("alignment_page_url")),
        "Foro de dudas": final_state.get("forum_discussion_id") is not None,
        "Pagina de creditos": bool(final_state.get("credits_page_url")),
    }
    for label, ok in content_checks.items():
        print(f"  - {label}: {_status(ok)}")

    _print_content_details(final_state)

    content_errors = [error for error in errors if "Pipeline detenido" not in error]
    if _has_content_errors(content_errors):
        print("\nPipeline detenido: fallos en la creacion de contenido.")
        print_errors(errors)
        return False
    return True


def _print_content_details(final_state: dict) -> None:
    if final_state.get("agenda_page_url"):
        print(f"    URL agenda: {final_state['agenda_page_url']}")
    if final_state.get("alignment_page_url"):
        print(f"    URL alineacion: {final_state['alignment_page_url']}")
    if final_state.get("credits_page_url"):
        print(f"    URL creditos: {final_state['credits_page_url']}")
    if final_state.get("forum_discussion_id"):
        print(f"    ID foro: {final_state['forum_discussion_id']}")


def _has_content_errors(errors: list) -> bool:
    return any(
        keyword in error.lower()
        for error in errors
        for keyword in CONTENT_ERROR_KEYWORDS
    )


def _report_modules(final_state: dict, errors: list) -> bool:
    module_mapping = final_state.get("module_mapping") or {}
    modules_ok = len(module_mapping) > 0
    print(f"\n[4] Unidades en Canvas: {_status(modules_ok)}")
    for name, module_id in module_mapping.items():
        print(f"  - {name} (id={module_id})")

    if modules_ok:
        return True

    print("\nPipeline detenido: no se crearon unidades.")
    print_errors(errors)
    return False


def _report_activities(final_state: dict, structure, errors: list) -> None:
    module_mapping = final_state.get("module_mapping") or {}
    activities_count = len(structure.activities) if structure else 0
    activities_ok = bool(module_mapping) and not any(
        "actividades" in error.lower() and "faltan" in error.lower()
        for error in errors
    )
    print(f"\n[5] Actividades (assignments): {_status(activities_ok)}")
    print(f"  Actividades definidas en el syllabus: {activities_count}")


def _report_final_status(errors: list) -> int:
    print("\n" + "-" * 60)
    if errors:
        print_errors(errors)
        print("Pipeline completado con advertencias o errores parciales.")
        return 1

    print("Pipeline completado correctamente.")
    return 0
