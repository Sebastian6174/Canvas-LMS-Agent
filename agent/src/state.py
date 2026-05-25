import operator
from typing import TypedDict, Optional, List, Dict, Annotated
from pydantic import BaseModel, Field


class Activity(BaseModel):
    name: str
    description: str
    duration : int
    type: str 
    rubric: Optional[str]
    related_learning_outcome: str
    weight: float    
    
class ScheduleItem(BaseModel):
    week: int
    activity_name: str = Field(description="Nombre de la actividad (debe coincidir con uno en la lista de actividades)")
    time_commitment: str

class Module(BaseModel):
    name: str
    description: str
    activities: List[str] # Lista de nombres de actividades

class CourseStructure(BaseModel):
    name: str
    academic_program: str
    semester: int
    academic_level: str
    credits: int
    prerequisites: List[str]
    teacher: str
    description: str = Field(description="Descripción concisa del curso")
    learning_outcomes: List[str]
    modules: List[Module]
    activities: List[Activity]
    schedule: List[ScheduleItem]

class CourseState(TypedDict):
    doc_id: str
    course_structure: Optional[CourseStructure]
    canvas_course_id: Optional[str]
    module_mapping: Optional[Dict[str, int]]
    teacher_info: Optional[str]
    alignment_page_url: Optional[str]
    agenda_page_url: Optional[str]
    forum_discussion_id: Optional[int]
    credits_page_url: Optional[str]
    is_valid: bool
    errors: Annotated[List[str], operator.add]
    