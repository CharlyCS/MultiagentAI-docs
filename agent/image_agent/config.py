"""Configuración compartida del image_agent (rutas, límites, entorno)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGE_DIR = PROJECT_ROOT / "data" / "image"
load_dotenv(PROJECT_ROOT / ".env")

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "es,en;q=0.8",
}
HTTP_TIMEOUT = 12

# Workflow determinista
WORKFLOW_STRATEGIES = ["official_site", "wikidata", "image_search", "favicon"]
MAX_CANDIDATES = 6          # candidatos a evaluar por estrategia

# Validación de imágenes
MIN_SIDE = 48               # px mínimos del lado menor
MIN_ASPECT, MAX_ASPECT = 0.15, 8.0

# Agente ReAct (solo se usa si el workflow no encuentra el logo completo)
REACT_MAX_STEPS = int(os.getenv("LOGO_REACT_MAX_STEPS", "12"))

# Si el buscador falla, se prueban dominios directos <empresa><tld>, en este orden
# (clientes principalmente de Perú). Ej.: LOGO_DOMAIN_TLDS=".com,.pe"
DOMAIN_GUESS_TLDS = tuple(os.getenv(
    "LOGO_DOMAIN_TLDS", ".pe,.com.pe,.com,.net,.org,.es,.com.mx,.co").split(","))

# Dominios que nunca son "la web oficial" de una empresa.
NON_OFFICIAL_DOMAINS = (
    "facebook.", "instagram.", "linkedin.", "twitter.", "x.com", "youtube.",
    "tiktok.", "wikipedia.", "pinterest.", "yelp.", "tripadvisor.", "google.",
    "bing.", "amazon.", "mercadolibre.", "glassdoor.", "indeed.", "solo.to",
    "linktr.ee", "universidadperu.", "datosperu.", "dnb.com",
)


def llm_enabled() -> bool:
    """El LLM se usa para verificar logos y para el agente ReAct."""
    return os.getenv("LOGO_VERIFY_WITH_LLM", "1") != "0" and bool(os.getenv("OPENAI_API_KEY"))


def llm_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
