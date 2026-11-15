"""
Tools LangChain para el agente ReAct (las ejecuta un ToolNode).
Envuelven las funciones puras de `image_agent.tools` y devuelven texto compacto
para el LLM. `try_save_logo` actualiza el estado del grafo con un Command.
"""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated

from ..imaging import download_image, is_valid_logo_image, save_png
from ..tools import images_search, scrape_logo_candidates
from ..tools import web_search as _web_search
from ..verifier import choose_logo
from ..utils import log


def _compact(rows: list[dict]) -> str:
    return json.dumps(rows, ensure_ascii=False) if rows else "Sin resultados."


@tool
def web_search(query: str) -> str:
    """Busca páginas web. Devuelve título, url y resumen de cada resultado."""
    rows = [{"title": r.get("title", "")[:90], "url": r.get("href", ""),
             "snippet": r.get("body", "")[:140]} for r in _web_search(query, max_results=8)]
    return _compact(rows)


@tool
def image_search(query: str) -> str:
    """Busca imágenes. Devuelve url de la imagen, título, página de origen y tamaño."""
    rows = [{"image_url": r.get("image", ""), "title": r.get("title", "")[:90],
             "page": r.get("url", ""), "size": f"{r.get('width')}x{r.get('height')}"}
            for r in images_search(query, max_results=10)]
    return _compact(rows)


@tool
def list_page_images(page_url: str, state: Annotated[dict, InjectedState]) -> str:
    """Lista imágenes candidatas a logo de una página (JSON-LD, <img> logo, iconos, og:image)."""
    cands = scrape_logo_candidates(page_url, state.get("client_name", ""), source="react")
    rows = [{"image_url": c["url"], "hint": c["context"][:80], "score": c["score"]}
            for c in cands[:10]]
    return _compact(rows)


@tool
def try_save_logo(
    image_url: str,
    context: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Verifica la imagen con visión. Si es el logo completo de la empresa, lo guarda y la
    tarea termina. `context` = de dónde salió la imagen (página, título)."""
    name = state["client_name"]

    def reply(text: str, **update) -> Command:
        return Command(update={**update, "messages": [ToolMessage(text, tool_call_id=tool_call_id)]})

    img = download_image(image_url)
    if img is None:
        return reply("No se pudo descargar o no es una imagen. Prueba otra.")
    if not is_valid_logo_image(img):
        return reply(f"Imagen descartada: tamaño/proporción inválidos {img.size}. Prueba otra.")

    choice = choose_logo([({"url": image_url, "context": context}, img)], name)
    if choice is None:
        return reply("Verificador no disponible.")
    if choice["index"] is None:
        return reply(f"No es el logo de {name}: {choice['reason']}. Sigue buscando.")
    if choice["kind"] != "full":
        update = {} if state.get("backup_url") else {"backup_url": image_url}
        return reply("Es solo un ícono de la empresa (guardado como respaldo). "
                     "Sigue buscando el logo completo.", **update)

    path = save_png(img, name)
    log.info("[react] logo guardado desde %s", image_url)
    return reply(f"LOGO GUARDADO en {path}. Tarea completada.", image_path=path, source=image_url)


REACT_TOOLS = [web_search, image_search, list_page_images, try_save_logo]
