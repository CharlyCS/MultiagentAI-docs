"""Buscador web gratuito (DuckDuckGo vía `ddgs`, sin API key) con reintentos."""

from __future__ import annotations

import time

from ..utils import log

try:
    from ddgs import DDGS
except ImportError:  # paquete antiguo
    from duckduckgo_search import DDGS  # type: ignore


def _with_retries(fn, query: str, max_results: int, retries: int = 3) -> list[dict]:
    # Los buscadores gratis a veces limitan (429 / timeout): reintento con espera.
    for attempt in range(retries):
        try:
            return fn(query, max_results=max_results) or []
        except Exception as e:
            log.info("Búsqueda '%s' falló (intento %d): %s", query, attempt + 1, e)
            time.sleep(1.5 * (attempt + 1))
    return []


def web_search(query: str, max_results: int = 10) -> list[dict]:
    """Resultados: [{'title', 'href', 'body'}]"""
    return _with_retries(DDGS().text, query, max_results)


def images_search(query: str, max_results: int = 15) -> list[dict]:
    """Resultados: [{'title', 'image', 'url', 'width', 'height', 'source'}]"""
    return _with_retries(DDGS().images, query, max_results)
