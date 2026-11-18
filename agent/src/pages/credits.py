"""Página 'Créditos': profesor autor, asesoría metodológica y producción."""

from src.pages.html import CourseLinks, banner
from src.pages.teacher import teacher_table

PRODUCTION_CREDIT = "&Aacute;rea de medios educativos - DINTEV"


def build_credits_html(teacher: str, teacher_bio: str, links: CourseLinks, methodology_advisor: str = "") -> str:
    advisor = methodology_advisor.strip() or "&nbsp;"
    return f"""{banner(links)}
{teacher_table(teacher, teacher_bio, links, "Profesor autor")}
<h4><strong>Asesor&iacute;a Metodol&oacute;gica:</strong></h4>
<p>{advisor}</p>
<h4><strong>Dise&ntilde;o gr&aacute;fico, producci&oacute;n audiovisual y montaje:</strong></h4>
<p>{PRODUCTION_CREDIT}</p>"""
