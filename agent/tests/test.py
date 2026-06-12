from agent.src.tools.doc_parser import read_google_doc
from typing import List, Optional, Dict, Any
from agent.config import config
from agent.src.tools.canvas_api import _canvas_request

def _rubric_creation_criteria(criteria: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    cleaned_criteria = {}
    for index, criterion in enumerate(criteria):
        cleaned = {
            key: value
            for key, value in criterion.items()
            if key not in {"id", "ratings"}
        }
        cleaned["ratings"] = {
            str(rating_index): {
                key: value
                for key, value in rating.items()
                if key not in {"id", "criterion_id"}
            }
            for rating_index, rating in enumerate(criterion.get("ratings", []))
        }
        cleaned_criteria[str(index)] = cleaned
    return cleaned_criteria

def create_or_update_assignment_rubric(
    title: str,
    criteria: List[Dict[str, Any]],
    assignment_id: int,
    course_id: Optional[str] = None,
    use_for_grading: bool = True,
) -> Dict:
    """
    Crea o actualiza una rúbrica de Canvas y la asocia a un assignment.
    """
    rubrics = _canvas_request("GET", "/rubrics?per_page=100", custom_course_id=course_id)
    rubric_id = None
    if isinstance(rubrics, list):
        for rubric in rubrics:
            if rubric.get("title", "").strip().lower() == title.strip().lower():
                rubric_id = rubric.get("id")
                break

    payload = {
        "rubric": {
            "title": title,
            "free_form_criterion_comments": False,
            "criteria": _rubric_creation_criteria(criteria),
        },
        "rubric_association": {
            "association_id": assignment_id,
            "association_type": "Assignment",
            "use_for_grading": use_for_grading,
            "purpose": "grading",
        },
    }

    if rubric_id:
        print(f"La rúbrica '{title}' ya existe (ID: {rubric_id}). Actualizándola...")
        return _canvas_request("PUT", f"/rubrics/{rubric_id}", payload, custom_course_id=course_id)
    
    return _canvas_request("POST", "/rubrics", payload, custom_course_id=course_id)

def test_canvas():
    response = create_or_update_assignment_rubric(
        title='Rúbrica N. 1',
        criteria=[{'id': 'criterion_1', 'description': 'Criterio 1: Comprensión del concepto de Galtung', 'long_description': 'Criterio 1: Comprensión del concepto de Galtung', 'points': 4.0, 'criterion_use_range': False, 'ratings': [{'id': 'criterion_1_excelente', 'description': 'Excelente', 'long_description': 'Explica el concepto con claridad, precisión y uso adecuado del lenguaje teórico; demuestra comprensión profunda.', 'points': 4.0}, {'id': 'criterion_1_en_desarrollo', 'description': 'En desarrollo', 'long_description': 'Explica correctamente el concepto, aunque con detalles generales o poco profundos.', 'points': 3.0}, {'id': 'criterion_1_basico', 'description': 'Basico', 'long_description': 'La explicación es superficial, incompleta o poco clara.', 'points': 2.0}, {'id': 'criterion_1_insuficiente', 'description': 'Insuficiente', 'long_description': 'No explica correctamente el concepto o lo usa de forma equivocada.', 'points': 0}]}, {'id': 'criterion_2', 'description': 'Criterio 2. Aplicación del concepto al contexto real', 'long_description': 'Criterio 2. Aplicación del concepto al contexto real', 'points': 4.0, 'criterion_use_range': False, 'ratings': [{'id': 'criterion_2_excelente', 'description': 'Excelente', 'long_description': 'Presenta un ejemplo claramente vinculado al concepto; explica cómo se manifiesta de manera pertinente y reflexiva.', 'points': 4.0}, {'id': 'criterion_2_en_desarrollo', 'description': 'En desarrollo', 'long_description': 'El ejemplo es adecuado, pero la conexión teoría-contexto es limitada o poco desarrollada.', 'points': 3.0}, {'id': 'criterion_2_basico', 'description': 'Basico', 'long_description': 'El ejemplo es general o la relación con el concepto es débil.', 'points': 2.0}, {'id': 'criterion_2_insuficiente', 'description': 'Insuficiente', 'long_description': 'No aplica el concepto al contexto o la aplicación es incorrecta.', 'points': 0}]}, {'id': 'criterion_3', 'description': 'Criterio 3. Claridad, síntesis y comunicación del reel', 'long_description': 'Criterio 3. Claridad, síntesis y comunicación del reel', 'points': 4.0, 'criterion_use_range': False, 'ratings': [{'id': 'criterion_3_excelente', 'description': 'Excelente', 'long_description': 'El reel es claro, coherente, sintético y comunica la idea de forma efectiva dentro del tiempo.', 'points': 4.0}, {'id': 'criterion_3_en_desarrollo', 'description': 'En desarrollo', 'long_description': 'El mensaje es claro, aunque presenta repeticiones o leves problemas de organización.', 'points': 3.0}, {'id': 'criterion_3_basico', 'description': 'Basico', 'long_description': 'El reel presenta dificultades de claridad o síntesis.', 'points': 2.0}, {'id': 'criterion_3_insuficiente', 'description': 'Insuficiente', 'long_description': 'El mensaje no se entiende o no cumple con el tiempo establecido.', 'points': 0}]}, {'id': 'criterion_4', 'description': 'Criterio 4. Creatividad y producción del reel', 'long_description': 'Criterio 4. Creatividad y producción del reel', 'points': 4.0, 'criterion_use_range': False, 'ratings': [{'id': 'criterion_4_excelente', 'description': 'Excelente', 'long_description': 'Presenta creatividad en la forma de comunicar (uso de imágenes, audio, texto o narrativa).', 'points': 4.0}, {'id': 'criterion_4_en_desarrollo', 'description': 'En desarrollo', 'long_description': 'El reel cumple, pero es simple o sin elementos creativos destacados.', 'points': 3.0}, {'id': 'criterion_4_basico', 'description': 'Basico', 'long_description': 'Escaso uso de recursos visuales o narrativos.', 'points': 2.0}, {'id': 'criterion_4_insuficiente', 'description': 'Insuficiente', 'long_description': 'Producción deficiente o sin edición mínima.', 'points': 0}]}, {'id': 'criterion_5', 'description': 'Criterio 5. Reflexión final', 'long_description': 'Criterio 5. Reflexión final', 'points': 4.0, 'criterion_use_range': False, 'ratings': [{'id': 'criterion_5_excelente', 'description': 'Excelente', 'long_description': 'Acompaña la presentación del reel, con una reflexión sólida, clara y bien argumentada sobre el Conflicto, incluye relaciones con el trabajo de la semana anterior.', 'points': 4.0}, {'id': 'criterion_5_en_desarrollo', 'description': 'En desarrollo', 'long_description': 'Acompaña la presentación del reel, con una reflexión sólida, clara y bien argumentada sobre el Conflicto, no incluye relaciones con el trabajo de la semana anterior.', 'points': 3.0}, {'id': 'criterion_5_basico', 'description': 'Basico', 'long_description': 'Acompaña la presentación del reel, con una reflexión que carece de argumentos, no es clara y no hay relación con los aprendizajes de la semana anterior.', 'points': 2.0}, {'id': 'criterion_5_insuficiente', 'description': 'Insuficiente', 'long_description': 'No acompaña la presentación del reel con la reflexión escrita solicitada.', 'points': 0}]}],
        assignment_id=11446,
        course_id='862',
        use_for_grading=True)
    
    print(response) 

def test_reader():    
    SAMPLE_DOC_ID = config.doc_id
    text = read_google_doc(SAMPLE_DOC_ID)
    if text:
        print("--- Document Content ---")
        print(text)
        print("------------------------")
        
test_canvas()
