"""Fotos del evento (origin: local): búsqueda, orientación EXIF y reducción de tamaño."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .settings import CACHE_DIR, log, resolve_path

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_SIDE_PX = 1800      # suficiente para 15 cm a ~300 dpi, mantiene el .docx liviano


def collect_photos(root: str, max_photos: int = 20) -> tuple[list[str], list[str]]:
    """
    Devuelve (rutas_preparadas, avisos). Las fotos se rotan según EXIF y se
    reducen a MAX_SIDE_PX en output/.cache/ (los originales no se tocan).
    """
    folder = resolve_path(root)
    if folder is None or not folder.is_dir():
        return [], [f"No existe la carpeta de fotos '{root}' (se buscó en el proyecto y en data/)."]

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXTS)
    if not files:
        return [], [f"La carpeta de fotos '{folder}' está vacía."]
    warnings = []
    if len(files) > max_photos:
        warnings.append(f"Se usaron las primeras {max_photos} de {len(files)} fotos.")
        files = files[:max_photos]

    out_dir = CACHE_DIR / "photos"
    out_dir.mkdir(parents=True, exist_ok=True)
    prepared = []
    for i, src in enumerate(files, 1):
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
                dst = out_dir / f"foto_{i:02d}.jpg"
                im.save(dst, "JPEG", quality=85)
                prepared.append(str(dst))
        except Exception as e:
            warnings.append(f"Foto ignorada {Path(src).name}: {e}")
    log.info("Fotos preparadas: %d", len(prepared))
    return prepared, warnings
