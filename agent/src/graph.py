from langgraph.graph import StateGraph, START, END

from src.state import CourseState
from src.routing import (
    CONTENT_CREATOR_NODES,
    route_after_analyst,
    route_after_setup,
    route_after_modules,
)
from src.nodes.analyst import (
    analyst_node,
    extract_modules_node,
    extract_activities_list_node,
    extract_schedule_node,
    extract_rubrics_list_node,
    enrich_activities_node,
)
from src.nodes.setup_course import setup_course_node
from src.nodes.page_creator import page_creator_node
from src.nodes.agenda_creator import agenda_creator_node
from src.nodes.alignment_creator import alignment_creator_node
from src.nodes.forum_creator import forum_creator_node
from src.nodes.credits_creator import credits_creator_node
from src.nodes.module_generator import module_generator_node
from src.nodes.populate_special_modules import populate_special_modules_node
from src.nodes.activity_creator import activity_creator_node
from src.nodes.unit_pages_creator import unit_pages_creator_node
from src.nodes.rubrics_creator import rubrics_creator_node
from src.nodes.syllabus_creator import syllabus_creator_node


def create_graph():
    workflow = StateGraph(CourseState)

    workflow.add_node("analyst", analyst_node)
    workflow.add_node("extract_modules", extract_modules_node)
    workflow.add_node("extract_activities_list", extract_activities_list_node)
    workflow.add_node("extract_schedule", extract_schedule_node)
    workflow.add_node("extract_rubrics_list", extract_rubrics_list_node)
    workflow.add_node("enrich_activities", enrich_activities_node)

    workflow.add_node("setup_course", setup_course_node)
    workflow.add_node("module_generator", module_generator_node)
    workflow.add_node("page_creator", page_creator_node)
    workflow.add_node("agenda_creator", agenda_creator_node)
    workflow.add_node("alignment_creator", alignment_creator_node)
    workflow.add_node("forum_creator", forum_creator_node)
    workflow.add_node("credits_creator", credits_creator_node)
    workflow.add_node("populate_special_modules", populate_special_modules_node)
    workflow.add_node("unit_pages_creator", unit_pages_creator_node)
    workflow.add_node("activity_creator", activity_creator_node)
    workflow.add_node("rubrics_creator", rubrics_creator_node)
    workflow.add_node("syllabus_creator", syllabus_creator_node)

    # Linear extraction sequence
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", "extract_modules")
    workflow.add_edge("extract_modules", "extract_activities_list")
    workflow.add_edge("extract_activities_list", "extract_schedule")
    workflow.add_edge("extract_schedule", "extract_rubrics_list")
    
    # Conditional loops and routing
    workflow.add_conditional_edges("extract_rubrics_list", route_after_analyst)
    workflow.add_conditional_edges("enrich_activities", route_after_analyst)
    
    workflow.add_conditional_edges("setup_course", route_after_setup)
    workflow.add_conditional_edges("module_generator", route_after_modules)

    for creator in CONTENT_CREATOR_NODES:
        workflow.add_edge(creator, "populate_special_modules")

    workflow.add_edge("populate_special_modules", "page_creator")
    workflow.add_edge("page_creator", "unit_pages_creator")
    workflow.add_edge("unit_pages_creator", "activity_creator")
    workflow.add_edge("activity_creator", "rubrics_creator")
    workflow.add_edge("rubrics_creator", "syllabus_creator")
    workflow.add_edge("syllabus_creator", END)
        
    return workflow.compile()


app = create_graph()
