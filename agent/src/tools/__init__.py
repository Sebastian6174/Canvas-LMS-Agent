from .doc_parser import read_google_doc
from .canvas_api import (
    create_course,
    import_base_course_files,
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    create_page,
    create_discussion_topic,
    set_module_position,
    list_course_files,
)

canvas_tools = [
    create_course,
    import_base_course_files,
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    create_page,
    create_discussion_topic,
    set_module_position,
    list_course_files,
]
