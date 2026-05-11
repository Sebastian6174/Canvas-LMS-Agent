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
    full_text = ""
    for tab in doc_content:
        full_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"

    # Initialize LLM with structured output
    print("Inferring course structure using LLM...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(CourseStructure)

    system_prompt = (
        "Eres un experto en diseño instruccional y análisis de currículo. "
        "Tu tarea es analizar el contenido de un documento que describe un curso y extraer su estructura de forma concisa. "
        "Debes identificar al docente, descripción del curso, resultados de aprendizaje, módulos, actividades y cronograma. "
        "IMPORTANTE: Sé extremadamente conciso en las descripciones y rubros de las actividades. "
        "En el cronograma ('schedule'), solo usa el 'activity_name' que coincida con el nombre de una actividad definida en la lista de 'activities'. "
        "No repitas el objeto Activity completo dentro del schedule."
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
