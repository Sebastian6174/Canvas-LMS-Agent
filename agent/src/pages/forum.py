"""Mensaje de bienvenida del foro de dudas."""

from src.pages.html import CourseLinks, banner


def build_forum_html(links: CourseLinks) -> str:
    return f"""{banner(links)}
<h2><strong>Foro de dudas</strong></h2>
<p><em><strong>Este foro de discusi&oacute;n es utilizado para recopilar y responder las preguntas de estudiantes.&nbsp;</strong></em></p>
<p>Este es un foro sin calificaci&oacute;n usado para publicar preguntas generales de la clase. Si no est&aacute; seguro de las instrucciones, tareas, etc., no dude en publicar sus preguntas a continuaci&oacute;n.</p>
<p><strong>Tenga en cuenta:</strong> si su pregunta est&aacute; relacionada con una calificaci&oacute;n que recibi&oacute; u otro asunto personal, no la publique aqu&iacute;. Para esto, p&oacute;ngase en contacto conmigo directamente a trav&eacute;s del correo o dir&iacute;jase a su consejero.</p>"""
