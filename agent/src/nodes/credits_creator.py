from src.state import CourseState
from src.tools.canvas_api import create_page
from config import config
from langchain_core.messages import SystemMessage, HumanMessage

def credits_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Créditos del curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de créditos"]}

    print(f"Generando página de créditos para el curso {course_id}...")
    
    llm = config.get_llm()
    
    system_prompt = """Eres un experto en diseño instruccional y Canvas LMS.
Tu tarea es generar el código HTML para la página de "Créditos" de un curso virtual, basándote en la plantilla y la información proporcionada.

Debes usar exactamente esta estructura HTML:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/862/files/66540/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/862/files/66540" data-api-returntype="File" /></h2>

<table class="ic-Table ic-Table--hover-row ic-Table--striped" style="width: 100%; border-collapse: collapse; border-style: none;" border="0">
    <caption>
        <h3 style="text-align: left;"><strong>&nbsp;Profesor autor</strong></h3>
    </caption>
    <tbody>
        <tr>
            <th style="width: 27.2394%; text-align: center; vertical-align: middle;" scope="row">
                <p><span style="font-size: 14pt;">[Nombre del profesor]</span></p>
            </th>
            <td style="width: 66.8502%; text-align: left; vertical-align: middle;">
                <p style="padding-left: 40px;">[Perfil del profesor/Biografía corta - Si se proporciona en la información de entrada, de lo contrario colocar una descripción concisa basada en el docente del curso]</p>
            </td>
            <td style="width: 5.9104%; text-align: left; vertical-align: middle;">
                <p style="padding-left: 40px;">&nbsp;</p>
            </td>
        </tr>
    </tbody>
</table>

<h4><strong>Asesoría Metodológica:</strong></h4>
<p>[Nombre del Asesor Metodológico si viene en el documento, de lo contrario dejar como: Profesional de diseño instruccional - DINTEV]</p>

<h4><strong>Diseño gráfico, producción audiovisual y montaje:</strong></h4>
<p>Área de medios educativos - DINTEV</p>

REGLAS DE GENERACIÓN:
1. Reemplaza [Nombre del profesor] con el docente real.
2. Si viene información del perfil del docente en el 'teacher_info' de la entrada, utilízala de forma íntegra sin resumir para llenar la biografía/perfil.
3. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
"""

    human_prompt = f"""Docente del curso: {structure.teacher}
Programa Académico: {structure.academic_program}
Nivel Académico: {structure.academic_level}
Créditos del Curso: {structure.credits}
Información adicional del docente (teacher_info): {state.get('teacher_info', 'No disponible')}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        html_content = response.content.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generando HTML de Créditos con LLM: {e}")
        return {"errors": [f"Error generando Créditos: {str(e)}"]}
    
    result = create_page.invoke({
        "title": "Créditos",
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al crear la página de créditos: {result['error']}")
        return {"errors": ["Error creando créditos"]}

    page_url = result.get("url")
    print(f"Página de créditos creada exitosamente: {page_url}")
    
    return {"credits_page_url": page_url}
