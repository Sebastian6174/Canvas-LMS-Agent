from src.state import CourseState, CourseStructure
from src.tools.doc_parser import read_google_doc
from config import config
from langchain_core.messages import HumanMessage, SystemMessage

def analyst_node(state: CourseState) -> CourseState:
    """
    Analyst node that reads a Google Doc and infers the course structure.
    """
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "is_valid": False, "errors": ["No doc_id provided in state"]}

    # Read the document
    print(f"Reading document {doc_id}...")
    doc_content = read_google_doc(doc_id)
    if not doc_content:
        return {**state, "is_valid": False, "errors": ["Failed to read Google Doc"]}

    # Prepare the text for the LLM
    import re
    full_text = ""
    for tab in doc_content:
        full_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"
    
    # Preprocesamiento agresivo: Eliminar todos los caracteres de control (0x00 a 0x1F)
    full_text = re.sub(r'[\x00-\x1F\x7F]', ' ', full_text)
        
    # Read teacher document if configured
    teacher_info_text = None
    if config.teacher_doc:
        print(f"Reading teacher document {config.teacher_doc}...")
        teacher_content = read_google_doc(config.teacher_doc)
        if teacher_content:
            teacher_info_text = ""
            for tab in teacher_content:
                teacher_info_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"
            teacher_info_text = re.sub(r'[\x00-\x1F\x7F]', ' ', teacher_info_text)

    # Initialize LLM with structured output
    print("Inferring course structure using LLM...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(CourseStructure)

    system_prompt = (
        "Eres un experto en diseño instruccional y análisis de currículo. "
        "Tu tarea es analizar el contenido de un documento que describe un curso y extraer su estructura. "
        "Debes identificar al docente, descripción del curso, resultados de aprendizaje, módulos, actividades y cronograma. "
        "IMPORTANTE: NO asumas ni inventes información. Extrae la información EXACTA proporcionada en el documento. "
        "Para la descripción del curso y otros campos descriptivos, extrae el texto de forma íntegra y completa, tal como aparece en el documento original, SIN RESUMIR. "
        "Si algún dato requerido no se encuentra en el documento, omítelo o déjalo en blanco; bajo ningún concepto debes inventarlo. "
        "En el cronograma ('schedule'), solo usa el 'activity_name' que coincida con el nombre de una actividad definida en la lista de 'activities'. "
        "No repitas el objeto Activity completo dentro del schedule. "
        "En 'modules' incluye solo las unidades de contenido del programa académico (Unidad 1, Unidad 2, etc.). "
        "REGLA CRÍTICA PARA EL JSON: Para evitar errores de formato (Invalid JSON control character), DEBES REEMPLAZAR todos los saltos de línea físicos por un simple espacio en blanco dentro de cualquier texto que extraigas. NO dejes saltos de línea literales (enters) ni uses '\\n' en los valores de texto."
    )

    human_prompt = f"Aquí está el contenido del documento:\n\n{full_text}"

    try:
        inferred_structure = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        print("Course structure inferred successfully.")
        return {
            **state,
            "course_structure": inferred_structure,
            "teacher_info": teacher_info_text,
            "is_valid": True,
            "errors": []
        }
    except Exception as e:
        print(f"Error during LLM inference: {str(e)}")
        return {
            **state,
            "is_valid": False,
            "errors": [f"Error during LLM inference: {str(e)}"]
        }
