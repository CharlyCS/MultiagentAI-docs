"""Utilidades de texto y HTTP."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional
from urllib.parse import urlparse

import requests

from .config import HTTP_HEADERS, HTTP_TIMEOUT

log = logging.getLogger("image_agent")

_STOPWORDS = {"sac", "s", "a", "c", "eirl", "srl", "sa", "inc", "ltd", "llc",
              "the", "de", "la", "el", "y", "and", "co", "corp", "group"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def name_tokens(name: str) -> list[str]:
    return [t for t in normalize(name).split() if t not in _STOPWORDS and len(t) > 1]


def slugify(name: str) -> str:
    return "".join(name_tokens(name)) or "empresa"


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def name_match(name: str, text: str) -> float:
    """Fracción de tokens del nombre presentes en `text` (0..1)."""
    toks = name_tokens(name)
    if not toks:
        return 0.0
    norm = normalize(text).replace(" ", "")
    return sum(t in norm for t in toks) / len(toks)


def unwrap_cdn_url(url: str) -> str:
    """
    Muchos CDNs de optimización envuelven la URL original, p.ej.
    https://sp-ao.shortpixel.ai/client/to_auto,w_501/https://empresa.com/logo.png
    -> devuelve https://empresa.com/logo.png (calidad original).
    """
    m = re.search(r".(https?://.+)$", url)
    return m.group(1) if m else url


def url_variants(url: str) -> list[str]:
    """URL original + reparaciones típicas (CDN, rutas de WordPress movidas)."""
    variants = [url]
    inner = unwrap_cdn_url(url)
    if inner != url:
        variants.insert(0, inner)  # primero la original, sin recompresión
    for u in list(variants):
        parsed = urlparse(u)
        if "/wp-content/" in parsed.path and not parsed.path.startswith("/wp-content/"):
            # p.ej. /nueva/wp-content/... (sitio migrado) -> /wp-content/...
            fixed = parsed.path[parsed.path.index("/wp-content/"):]
            variants.append(f"{parsed.scheme}://{parsed.netloc}{fixed}")
    return list(dict.fromkeys(variants))


def http_get(url: str, **kwargs) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        log.debug("GET %s falló: %s", url, e)
        return None
