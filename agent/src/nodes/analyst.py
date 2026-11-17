from langchain_core.messages import HumanMessage, SystemMessage

from config import config
from src.activities.rules import ACTIVITY_TYPE_DEFAULT, ACTIVITY_TYPES
from src.analysis.chunking import (
    document_text,
    is_truncation_error,
    split_chunk,
    split_into_chunks,
)
from src.analysis.enrichment import finalize_structure
from src.analysis.merge import merge_partial
from src.nodes.base import fail, proceed
from src.state import CourseState, CourseStructure, PartialCourseStructure
from src.tools.doc_parser import read_google_doc

TEACHER_CONTEXT_MAX_CHARS = 2000


SYSTEM_PROMPT = (
    "Analiza SOLO el fragmento recibido de un documento curricular. Devuelve un fragmento parcial "
    "compatible con el esquema. Extrae únicamente datos explícitos; no inventes ni completes con conocimiento externo. "
    "Incluye actividades, módulos, resultados, cronograma y rúbricas sólo cuando aparezcan en este fragmento. "
    "En 'name' guarda sólo el título corto de la actividad, sin el prefijo 'Actividad N.'. "
    "Copia en 'description' el texto completo de la actividad (instrucciones y pasos) y en "
    "'delivery_form' la forma de entrega sólo si el documento la indica; si no, déjala vacía. "
    f"Clasifica 'activity_type' con uno de: {', '.join(ACTIVITY_TYPES)} "
    f"(si no encaja, usa '{ACTIVITY_TYPE_DEFAULT}'). "
    "En 'evaluation_type' indica 'Formativa' o 'Evaluativa' según el documento; si no está claro, "
    "usa Evaluativa cuando la ponderación (weight) sea mayor que 0. "
    "Completa module_name y resources. "
    "Usa textos compactos, sin saltos de línea dentro de valores. Devuelve sólo la estructura solicitada."
)


def _human_prompt(chunks: list[str], index: int, teacher_info: str | None) -> str:
    prompt = f"Fragmento {index + 1} de {len(chunks)}:\n{chunks[index]}"
    if teacher_info:
        prompt += (
            "\n\nDatos del docente (contexto adicional):\n"
            f"{teacher_info[:TEACHER_CONTEXT_MAX_CHARS]}"
        )
    return prompt


def _load_teacher_info(state: CourseState) -> str | None:
    teacher_info = state.get("teacher_info")
    if teacher_info is None and config.teacher_doc:
        teacher_content = read_google_doc(config.teacher_doc)
        teacher_info = document_text(teacher_content) if teacher_content else ""
    return teacher_info


def _as_partial(result) -> PartialCourseStructure:
    if isinstance(result, PartialCourseStructure):
        return result
    data = result.model_dump() if hasattr(result, "model_dump") else result
    return PartialCourseStructure.model_validate(data)


def analyst_node(state: CourseState) -> CourseState:
    """Procesa un fragmento del documento y acumula su estructura en el estado."""
    doc_id = state.get("doc_id")
    if not doc_id:
        return fail(state, "No doc_id provided in state", is_valid=False)

    chunks = state.get("analysis_chunks")
    index = state.get("analysis_chunk_index", 0)
    if not chunks:
        print(f"Reading document {doc_id}...")
        doc_content = read_google_doc(doc_id)
        if not doc_content:
            return fail(state, "Failed to read Google Doc", is_valid=False)
        chunks = split_into_chunks(document_text(doc_content))
        index = 0

    if index >= len(chunks):
        return fail(state, "No quedan fragmentos para analizar", is_valid=False)

    teacher_info = _load_teacher_info(state)

    try:
        structured_llm = config.get_llm().with_structured_output(PartialCourseStructure)
        result = structured_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=_human_prompt(chunks, index, teacher_info)),
        ])
        if isinstance(result, CourseStructure):
            # El LLM devolvió la estructura completa: no hace falta seguir troceando.
            merged = result.model_dump()
            next_index = len(chunks)
        else:
            merged = merge_partial(state.get("analysis_partial_structure") or {}, _as_partial(result))
            next_index = index + 1

        progress = {
            "analysis_chunks": chunks,
            "analysis_chunk_index": next_index,
            "analysis_partial_structure": merged,
            "teacher_info": teacher_info,
        }
        if next_index < len(chunks):
            return proceed(state, **progress, is_valid=False, course_structure=None)

        structure = finalize_structure(merged)
        print("Course structure inferred successfully from all document fragments.")
        return proceed(state, **progress, course_structure=structure, is_valid=True)
    except Exception as e:
        halves = split_chunk(chunks[index]) if is_truncation_error(e) else None
        if halves:
            chunks[index:index + 1] = list(halves)
            print(
                f"Respuesta truncada en el fragmento {index + 1}; "
                "se divide el fragmento y se reintenta."
            )
            return proceed(
                state,
                analysis_chunks=chunks,
                analysis_chunk_index=index,
                teacher_info=teacher_info,
                is_valid=False,
                course_structure=None,
            )
        print(f"Error during LLM inference: {str(e)}")
        return fail(state, f"Error during LLM inference: {str(e)}", is_valid=False)
