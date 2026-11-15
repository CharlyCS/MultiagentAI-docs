"""
Resuelve picture_logo según config.yaml:

    picture_logo: { origin: web,   url: "*" }                  -> ImageWebAgent (busca en la web)
    picture_logo: { origin: web,   url: "https://.../logo.png" } -> descarga directa
    picture_logo: { origin: local, root: "logos/cliente.png" }   -> archivo local
"""

from __future__ import annotations

from typing import Any

from agent.image_agent import ImageWebAgent
from agent.image_agent.imaging import download_image, save_png

from .settings import PROJECT_ROOT, log, resolve_path


def resolve_logo(client_name: str, cfg: dict[str, Any]) -> tuple[str, dict]:
    """Devuelve (ruta_absoluta_logo, info)."""
    origin = (cfg.get("origin") or "web").lower()
    url = str(cfg.get("url") or "*").strip()

    if origin == "local":
        path = resolve_path(cfg.get("root") or cfg.get("path") or "")
        if path and path.is_file():
            return str(path), {"found_by": "local", "source": str(path)}
        log.warning("Logo local no encontrado (%s); se busca en la web.", cfg.get("root"))

    if origin == "web" and url not in ("*", ""):
        img = download_image(url)
        if img is not None:
            rel = save_png(img, client_name)
            return str(PROJECT_ROOT / rel), {"found_by": "url_config", "source": url}
        log.warning("No se pudo descargar el logo de %s; se busca con el agente.", url)

    agent = ImageWebAgent(client_name)
    rel = agent.run()
    return str(PROJECT_ROOT / rel), {k: agent.result.get(k) for k in ("found_by", "source", "is_placeholder")}
