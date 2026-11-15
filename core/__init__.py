"""Utilidades del orquestador: configuración, logo, fotos y renderizado del Word."""

from .document import render_report
from .logo import resolve_logo
from .photos import collect_photos
from .settings import (CONFIG_PATH, OUTPUT_DIR, PROJECT_ROOT, TEMPLATE_PATH, load_config,
                       setup_logging)

__all__ = [
    "CONFIG_PATH", "OUTPUT_DIR", "PROJECT_ROOT", "TEMPLATE_PATH",
    "collect_photos", "load_config", "render_report", "resolve_logo", "setup_logging",
]
