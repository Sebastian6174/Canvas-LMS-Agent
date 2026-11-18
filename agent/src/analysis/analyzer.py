"""Orquesta el análisis del documento: extracción por secciones y ensamblado."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from src.analysis.assembly import build_course_structure
from src.analysis.extraction import Extractor
from src.analysis.sections import DocumentSections
from src.state import CourseStructure

Tab = Dict[str, Any]


def analyze_course(
    llm,
    tabs: List[Tab],
    teacher_tabs: Optional[List[Tab]] = None,
    max_workers: int = 4,
) -> Tuple[CourseStructure, str, List[str]]:
    """
    Infiere la estructura completa del curso.
    Devuelve (estructura, perfil del docente, advertencias).
    """
    sections = DocumentSections(tabs)
    extractor = Extractor(llm, sections)

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        overview_job = pool.submit(extractor.overview)
        modules_job = pool.submit(extractor.modules)
        schedule_job = pool.submit(extractor.schedule)

        rubric_blocks = extractor.rubric_blocks()
        if rubric_blocks:
            rubric_jobs = [pool.submit(extractor.rubric, block) for block in rubric_blocks]
            full_rubrics_job = None
        else:
            rubric_jobs = []
            full_rubrics_job = pool.submit(extractor.rubrics_from_full_document)

        # Las actividades dependen de la secuencia, que fija cuáles son y en qué orden.
        schedule = schedule_job.result()
        if not schedule:
            raise RuntimeError("No se encontraron actividades en la secuencia del documento.")
        detail_jobs = [pool.submit(extractor.activity, row) for row in schedule]

        overview = overview_job.result()
        teacher_job = None
        if teacher_tabs:
            teacher_text = DocumentSections(teacher_tabs).full_text()
            teacher_job = pool.submit(extractor.teacher_bio, overview.teacher, teacher_text)

        modules = modules_job.result()
        details = [job.result() for job in detail_jobs]
        rubrics = (
            [job.result() for job in rubric_jobs]
            if full_rubrics_job is None
            else full_rubrics_job.result()
        )
        teacher_bio = teacher_job.result() if teacher_job else ""

    structure, warnings = build_course_structure(overview, modules, schedule, details, rubrics)
    return structure, teacher_bio, warnings
