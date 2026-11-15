"""Descarga, validación, normalización y guardado de imágenes."""

from __future__ import annotations

import base64
import io
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from .config import IMAGE_DIR, MAX_ASPECT, MIN_ASPECT, MIN_SIDE, PROJECT_ROOT
from .utils import http_get, log, slugify, url_variants

try:
    import cairosvg  # logos SVG
except Exception:  # pragma: no cover
    cairosvg = None

DARK_BG = (24, 28, 36, 255)   # placa para logos blancos


def _decode(data: bytes, url: str, ctype: str) -> Optional[Image.Image]:
    is_svg = ("svg" in ctype or url.lower().split("?")[0].endswith(".svg")
              or data.lstrip()[:5] in (b"<svg ", b"<?xml"))
    if is_svg:
        if cairosvg is None:
            return None
        data = cairosvg.svg2png(bytestring=data, output_width=800)
    img = Image.open(io.BytesIO(data))
    if getattr(img, "n_frames", 1) > 1:  # .ico / gif: el frame más grande
        frames = []
        for i in range(img.n_frames):
            img.seek(i)
            frames.append(img.copy())
        img = max(frames, key=lambda f: f.size[0] * f.size[1])
    img.load()
    return img.convert("RGBA")


def download_image(url: str) -> Optional[Image.Image]:
    """
    Descarga una imagen (PNG/JPG/WEBP/ICO/GIF/SVG) en RGBA. Prueba antes la URL
    original sin CDN y reparaciones de rutas rotas (ver utils.url_variants).
    """
    for candidate in url_variants(url):
        r = http_get(candidate)
        if r is None or len(r.content) < 200:
            continue
        try:
            img = _decode(r.content, candidate, r.headers.get("Content-Type", "").lower())
            if img is not None:
                return img
        except Exception as e:
            log.debug("Imagen inválida %s: %s", candidate, e)
    return None


def is_valid_logo_image(img: Image.Image) -> bool:
    """Filtro barato: tamaño mínimo, proporción razonable y que no sea de un solo color."""
    w, h = img.size
    if min(w, h) < MIN_SIDE or not (MIN_ASPECT <= w / h <= MAX_ASPECT):
        return False
    lum = img.convert("L").getextrema()
    alpha = img.getchannel("A").getextrema()
    return (lum[1] - lum[0]) > 10 and alpha[1] > 0


def light_ratio(img: Image.Image) -> float:
    """Fracción de píxeles visibles casi blancos (0..1)."""
    small = img.copy()
    small.thumbnail((160, 160))
    px = [lum for lum, a in zip(small.convert("L").getdata(), small.getchannel("A").getdata())
          if a > 128]
    return sum(lum > 215 for lum in px) / len(px) if px else 0.0


def has_transparency(img: Image.Image) -> bool:
    return img.getchannel("A").getextrema()[0] < 250


def needs_dark_plate(img: Image.Image) -> bool:
    """Logo transparente pensado para fondo oscuro (texto blanco): se perdería sobre papel."""
    return has_transparency(img) and light_ratio(img) > 0.35


def preview_b64(img: Image.Image, max_side: int = 260) -> str:
    """Vista para el LLM: la imagen sobre fondo BLANCO | fondo OSCURO, lado a lado."""
    thumb = img.copy()
    thumb.thumbnail((max_side, max_side))
    w, h = thumb.size
    pad = 10
    canvas = Image.new("RGB", (2 * w + 3 * pad, h + 2 * pad), (200, 200, 200))
    canvas.paste(Image.new("RGB", (w, h), "white"), (pad, pad))
    canvas.paste(Image.new("RGB", (w, h), DARK_BG[:3]), (2 * pad + w, pad))
    canvas.paste(thumb, (pad, pad), thumb)
    canvas.paste(thumb, (2 * pad + w, pad), thumb)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def trim_borders(img: Image.Image, margin: int = 8) -> Image.Image:
    """Recorta bordes sobrantes: por transparencia (alfa) o por el color del fondo."""
    if has_transparency(img):
        # Con alfa: así no se recortan partes blancas del logo (texto blanco, etc.)
        bbox = img.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    else:
        ref = img.getpixel((0, 0))[:3]
        diff = ImageChops.difference(img.convert("RGB"), Image.new("RGB", img.size, ref))
        bbox = diff.convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    return img.crop((max(left - margin, 0), max(top - margin, 0),
                     min(right + margin, img.width), min(bottom + margin, img.height)))


def on_dark_plate(img: Image.Image) -> Image.Image:
    """Coloca el logo sobre una placa oscura redondeada (para logos blancos)."""
    pad = max(12, int(0.12 * min(img.size)))
    w, h = img.width + 2 * pad, img.height + 2 * pad
    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle((0, 0, w - 1, h - 1), radius=pad, fill=DARK_BG)
    plate.alpha_composite(img, (pad, pad))
    return plate


def prepare_for_document(img: Image.Image) -> Image.Image:
    """Recorta y garantiza que el logo se vea sobre el papel blanco del Word."""
    img = trim_borders(img)
    if img.width < 400:  # logos pequeños: escalar para que no se pixelen al imprimir
        ratio = 400 / img.width
        img = img.resize((400, max(1, int(img.height * ratio))), Image.LANCZOS)
    return on_dark_plate(img) if needs_dark_plate(img) else img


def save_png(img: Image.Image, client_name: str) -> str:
    """
    Guarda data/image/logo_<slug>.png (listo para el documento) y
    data/image/logo_<slug>_original.png. Devuelve la ruta relativa del primero.
    """
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(client_name)
    img.save(IMAGE_DIR / f"logo_{slug}_original.png", format="PNG")
    path = IMAGE_DIR / f"logo_{slug}.png"
    prepare_for_document(img).save(path, format="PNG")
    return str(path.relative_to(PROJECT_ROOT))


def placeholder_logo(client_name: str) -> Image.Image:
    """Logo de texto generado localmente: garantiza que siempre haya imagen."""
    width, height = 800, 300
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    text = client_name.upper()
    font = ImageFont.load_default()
    for font_file in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            size = 120
            while size > 20:
                font = ImageFont.truetype(font_file, size)
                if draw.textlength(text, font=font) <= width - 60:
                    break
                size -= 4
            break
        except OSError:
            continue
    draw.rounded_rectangle((5, 5, width - 5, height - 5), radius=30,
                           outline=(30, 30, 30, 255), width=6)
    draw.text((width / 2, height / 2), text, fill=(30, 30, 30, 255), font=font, anchor="mm")
    return img
