"""Tabla del profesor (foto, nombre y perfil), compartida por la portada y los créditos."""

from src.pages.html import CourseLinks, esc, text_to_html

PHOTO_SIZE = 'width="165"'


def teacher_table(name: str, bio: str, links: CourseLinks, caption: str) -> str:
    photo = links.image([name, f"Profesor {name}"], f"Profesor {name}", PHOTO_SIZE) if name else ""
    bio_html = text_to_html(bio, indent="                ") or "                <p>&nbsp;</p>"
    return f"""<table class="ic-Table ic-Table--hover-row ic-Table--striped" style="width: 100%; border-collapse: collapse; border-style: none;" border="0">
    <caption>
        <h3 style="text-align: left;"><strong>&nbsp;{caption}</strong></h3>
    </caption>
    <tbody>
        <tr>
            <th style="width: 27%; text-align: center; vertical-align: middle;" scope="row">
                <p>{photo or "&nbsp;"}</p>
                <p><span style="font-size: 14pt;"><strong>{esc(name)}</strong></span></p>
            </th>
            <td style="width: 67%; text-align: left; vertical-align: middle;">
{bio_html}
            </td>
            <td style="width: 6%;"><p>&nbsp;</p></td>
        </tr>
    </tbody>
</table>"""
