from langgraph.graph import StateGraph, START, END
from src.state import CourseState
from src.nodes.analyst import analyst_node
from src.nodes.setup_course import setup_course_node
from src.nodes.page_creator import page_creator_node
from src.nodes.module_generator import module_generator_node
from src.nodes.activity_creator import activity_creator_node
from config import config

def create_graph():
    # Se inicializa el grafo con el estado definido en state.py
    workflow = StateGraph(CourseState)

    # Se definen los nodos
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("setup_course", setup_course_node)
    workflow.add_node("page_creator", page_creator_node)
    workflow.add_node("module_generator", module_generator_node)
    workflow.add_node("activity_creator", activity_creator_node)

    # Se definen las aristas (flujo condicional y secuencial)
    workflow.add_edge(START, "analyst")
    
    workflow.add_edge("analyst", "setup_course")    
    workflow.add_edge("setup_course", "page_creator")
    workflow.add_edge("page_creator", "module_generator")
    workflow.add_edge("module_generator", "activity_creator")
    workflow.add_edge("activity_creator", END)

    return workflow.compile()

app = create_graph()
