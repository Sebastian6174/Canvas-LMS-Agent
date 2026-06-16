from contextlib import contextmanager
from typing import Any

from config import config
from src.graph import app
from src.reporting import print_pipeline_report


def initial_state(doc_id: str) -> dict:
    return {
        "doc_id": doc_id,
        "course_structure": None,
        "canvas_course_id": None,
        "module_mapping": None,
        "teacher_info": None,
        "alignment_page_url": None,
        "agenda_page_url": None,
        "forum_discussion_id": None,
        "credits_page_url": None,
        "syllabus_page_url": None,
        "is_valid": False,
        "errors": [],
        "downloadable_program": "",
        "course_files_map": None,
        "canvas_assignment_ids": None,
    }


@contextmanager
def temporary_config(overrides: dict[str, Any] | None):
    """Apply one-run config values and restore the global config afterwards."""
    clean_overrides = {
        key: value
        for key, value in (overrides or {}).items()
        if value is not None and hasattr(config, key)
    }
    previous = {key: getattr(config, key) for key in clean_overrides}

    try:
        for key, value in clean_overrides.items():
            setattr(config, key, value)
        yield
    finally:
        for key, value in previous.items():
            setattr(config, key, value)


def run_agent(overrides: dict[str, Any] | None = None) -> tuple[dict, int]:
    """Run the Canvas pipeline with optional values received from API/UI."""
    with temporary_config(overrides):
        doc_id = config.doc_id

        if not doc_id:
            print("Error: No DOC_ID encontrado en la configuracion.")
            return initial_state(""), 1

        print(f"Iniciando pipeline para documento: {doc_id}")

        final_state = app.invoke(initial_state(doc_id))
        exit_code = print_pipeline_report(final_state)
        return final_state, exit_code
