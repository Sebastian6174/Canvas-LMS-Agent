import sys

from config import config
from src.graph import app
from src.routing import CREATOR_NODES


def _status(ok: bool) -> str:
    return "OK" if ok else "FALLÓ"


def _print_course_summary(structure) -> None:
    print(f"  Programa: {structure.academic_program}")
    print(f"  Semestre: {structure.semester}")
    print(f"  Docente: {structure.teacher}")
    print(f"  Unidades: {len(structure.modules)}")
    print(f"  Actividades: {len(structure.activities)}")


def _print_pipeline_report(final_state: dict) -> int:
    """Imprime el resultado de cada etapa. Retorna código de salida (0=éxito)."""
    errors = final_state.get("errors") or []
    structure = final_state.get("course_structure")

    print("\n" + "=" * 60)
    print("REPORTE DEL PIPELINE — Canvas LMS Agent")
    print("=" * 60)

    # 1. Analista
    analyst_ok = final_state.get("is_valid") and structure is not None
    print(f"\n[1] Analista (inferencia desde Google Doc): {_status(analyst_ok)}")
    if structure:
        _print_course_summary(structure)
    if final_state.get("teacher_info"):
        print("  Info docente adicional: cargada")
    elif config.teacher_doc:
        print("  Info docente adicional: no disponible (revisar permisos TEACHER_DOC)")

    if not analyst_ok:
        print("\nPipeline detenido tras el analista.")
        _print_errors(errors)
        return 1

    # 2. Setup Canvas
    course_id = final_state.get("canvas_course_id")
    setup_ok = bool(course_id) and not any(
        e.startswith("Error al crear curso") or e.startswith("COURSE_ID")
        for e in errors
    )
    print(f"\n[2] Configuración del curso en Canvas: {_status(setup_ok)}")
    if course_id:
        print(f"  Curso Canvas ID: {course_id}")
    if config.base_course_id:
        print(f"  Curso base configurado: {config.base_course_id}")

    if not setup_ok:
        print("\nPipeline detenido tras la configuración del curso.")
        _print_errors(errors)
        return 1

    # 3. Creadores de contenido (paralelo)
    print(f"\n[3] Contenido en Canvas ({len(CREATOR_NODES) - 1} nodos en paralelo + página de inicio):")
    content_checks = {
        "Página de inicio": not any("page_creator" in e.lower() for e in errors),
        "Agenda de actividades": bool(final_state.get("agenda_page_url")),
        "Alineación de actividades": bool(final_state.get("alignment_page_url")),
        "Foro de dudas": final_state.get("forum_discussion_id") is not None,
        "Página de créditos": bool(final_state.get("credits_page_url")),
    }
    for label, ok in content_checks.items():
        print(f"  - {label}: {_status(ok)}")
    if final_state.get("agenda_page_url"):
        print(f"    URL agenda: {final_state['agenda_page_url']}")
    if final_state.get("alignment_page_url"):
        print(f"    URL alineación: {final_state['alignment_page_url']}")
    if final_state.get("credits_page_url"):
        print(f"    URL créditos: {final_state['credits_page_url']}")
    if final_state.get("forum_discussion_id"):
        print(f"    ID foro: {final_state['forum_discussion_id']}")

    content_errors = [e for e in errors if "Pipeline detenido" not in e]
    if content_errors and any(
        kw in e.lower()
        for e in content_errors
        for kw in ("agenda", "alineación", "alineacion", "foro", "créditos", "creditos", "page_creator", "html")
    ):
        print("\nPipeline detenido: fallos en la creación de contenido.")
        _print_errors(errors)
        return 1

    # 4. Módulos
    module_mapping = final_state.get("module_mapping") or {}
    modules_ok = len(module_mapping) > 0
    print(f"\n[4] Unidades en Canvas: {_status(modules_ok)}")
    if module_mapping:
        for name, mod_id in module_mapping.items():
            print(f"  - {name} (id={mod_id})")

    if not modules_ok:
        print("\nPipeline detenido: no se crearon unidades.")
        _print_errors(errors)
        return 1

    # 5. Actividades
    activities_count = len(structure.activities) if structure else 0
    activities_ok = modules_ok and not any(
        "actividades" in e.lower() and "faltan" in e.lower() for e in errors
    )
    print(f"\n[5] Actividades (assignments): {_status(activities_ok)}")
    print(f"  Actividades definidas en el syllabus: {activities_count}")

    # Resumen final
    print("\n" + "-" * 60)
    if errors:
        _print_errors(errors)
        print("Pipeline completado con advertencias o errores parciales.")
        return 1

    print("Pipeline completado correctamente.")
    return 0


def _print_errors(errors: list) -> None:
    if not errors:
        return
    print("\nErrores registrados:")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")


def main() -> None:
    doc_id = config.doc_id

    if not doc_id:
        print("Error: No DOC_ID encontrado en el archivo .env.")
        sys.exit(1)

    print(f"Iniciando pipeline para documento: {doc_id}")

    initial_state = {
        "doc_id": doc_id,
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

    final_state = app.invoke(initial_state)
    exit_code = _print_pipeline_report(final_state)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
