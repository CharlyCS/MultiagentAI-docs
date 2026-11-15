"""Renderizado del informe Word con docxtpl."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from docxtpl import DocxTemplate, InlineImage, Listing
from PIL import Image

from .settings import log

LOGO_MAX_HEIGHT_CM = 4.0


def _inject_description_placeholder(tpl: DocxTemplate) -> None:
    """
    La plantilla no tiene {{ description }}: se agrega EN MEMORIA (no se modifica
    template.docx) justo después de la primera tabla (sección "Detalles del evento").
    """
    body = tpl.docx.element.body
    tables = body.findall(body.tag.replace("body", "tbl"))
    anchor = tables[0] if tables else body[-2]
    p = OxmlElement("w:p")
    anchor.addnext(p)
    para = Paragraph(p, tpl.docx._body)
    para.paragraph_format.space_before = Cm(0.3)
    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para.add_run("{{ description }}")


def _patch_subdoc_tag(tpl: DocxTemplate, var: str) -> None:
    """
    Un Subdoc (varios párrafos/imágenes) debe insertarse con {{p var }}; la plantilla
    usa {{ var }}. Se corrige EN MEMORIA para no tocar template.docx.
    """
    pattern = re.compile(r"\{\{\s*" + re.escape(var) + r"\s*\}\}")
    for para in tpl.docx.paragraphs:
        if pattern.fullmatch(para.text.strip()):
            for run in para.runs[1:]:
                run._r.getparent().remove(run._r)
            para.runs[0].text = "{{p " + var + " }}"


def _strip_trailing_empty_paragraphs(tpl: DocxTemplate) -> None:
    """Quita párrafos vacíos al final (evitan una página en blanco si el texto llena la hoja)."""
    body = tpl.docx.element.body
    W = body.tag.split("}")[0] + "}"
    for el in reversed(list(body)):
        if el.tag == W + "sectPr":
            continue
        is_empty_p = (el.tag == W + "p" and not "".join(t.text or "" for t in el.iter(W + "t")).strip()
                      and next(el.iter(W + "drawing"), None) is None)
        if not is_empty_p:
            break
        body.remove(el)


def _logo_image(tpl: DocxTemplate, path: str, width_cm: float) -> InlineImage:
    """Ancho pedido en config, pero sin pasar LOGO_MAX_HEIGHT_CM de alto (logos cuadrados)."""
    with Image.open(path) as im:
        w, h = im.size
    if width_cm * h / w > LOGO_MAX_HEIGHT_CM:
        return InlineImage(tpl, path, height=Cm(LOGO_MAX_HEIGHT_CM))
    return InlineImage(tpl, path, width=Cm(width_cm))


def _photos_subdoc(tpl: DocxTemplate, photos: list[str], width_cm: float):
    sd = tpl.new_subdoc()
    if not photos:
        sd.add_paragraph("No se adjuntaron fotos del evento.")
        return sd
    for i, photo in enumerate(photos, 1):
        with Image.open(photo) as im:
            w, h = im.size
        size = {"width": Cm(width_cm)} if w >= h else {"height": Cm(width_cm * 0.9)}
        sd.add_picture(photo, **size)
        sd.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption = sd.add_paragraph(f"Foto {i}")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return sd


def render_report(template_path: Path | str, output_path: Path | str, *, data: dict[str, Any],
                  description: str, raw: list[dict], logo_path: str, photos: list[str]) -> str:
    images = data.get("images", {})
    logo_cfg = images.get("picture_logo", {}) or {}
    photos_cfg = images.get("pictures_event", {}) or {}

    tpl = DocxTemplate(str(template_path))
    declared = tpl.get_undeclared_template_variables()
    tpl.init_docx()
    if "description" not in declared:
        _inject_description_placeholder(tpl)
    _patch_subdoc_tag(tpl, "pictures_event")

    context = {
        "client": data["client"],
        "engineer": data["engineer"],
        "sales_team": data["sales_team"],
        "table": data["table"],
        # Listing: respeta los saltos de línea / párrafos del texto del writer
        "description": Listing(description.strip()),
        "raw": raw,
        "picture_logo": _logo_image(tpl, logo_path, float(logo_cfg.get("ancho_cm", 10))),
        "pictures_event": _photos_subdoc(tpl, photos, float(photos_cfg.get("ancho_cm", 15))),
    }
    if "raw" not in declared:
        log.info("La plantilla no tiene tabla 'raw': se usa solo la descripción.")
    tpl.render(context, autoescape=True)
    _strip_trailing_empty_paragraphs(tpl)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(output_path)
    log.info("Informe generado: %s", output_path)
    return str(output_path)
