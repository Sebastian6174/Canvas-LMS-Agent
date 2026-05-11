from langgraph.graph import StateGraph, START, END
from src.state import CourseState
from src.nodes.analyst import analyst_node

def create_graph():
    # Se inicializa el grafo con el estado definido en state.py
    workflow = StateGraph(CourseState)

    # Se define el nodo del analista
    workflow.add_node("analyst", analyst_node)

    # Se define el punto de entrada
    workflow.add_edge(START, "analyst")

    # El grafo termina después del analista por ahora
    workflow.add_edge("analyst", END)

    return workflow.compile()

app = create_graph()
