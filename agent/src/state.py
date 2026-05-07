from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class CourseState(TypedDict):
    is_valid : bool
    structure : list
    