from .doc_parser import read_google_doc
from .canvas_api import (
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    set_module_position
)

canvas_tools = [
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    set_module_position
]
