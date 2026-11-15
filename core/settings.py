"""Rutas del proyecto y carga de config.yaml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "data" / "config.yaml"
TEMPLATE_PATH = PROJECT_ROOT / "template" / "template.docx"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = OUTPUT_DIR / ".cache"

load_dotenv(PROJECT_ROOT / ".env")
log = logging.getLogger("mas_docs")

REQUIRED_KEYS = ("client", "engineer", "sales_team", "table")


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    missing = [k for k in REQUIRED_KEYS if not data.get(k)]
    if missing:
        raise ValueError(f"Faltan claves en {path}: {', '.join(missing)}")
    data.setdefault("images", {})
    data.setdefault("description", "")
    return data


def resolve_path(p: str | Path) -> Optional[Path]:
    """Ruta absoluta para rutas de config.yaml: tal cual, relativa al proyecto o a data/."""
    p = Path(p).expanduser()
    for candidate in (p, PROJECT_ROOT / p, PROJECT_ROOT / "data" / p):
        if candidate.exists():
            return candidate.resolve()
    return None


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "ddgs", "primp", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
