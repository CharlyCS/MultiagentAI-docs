"""Búsqueda de imágenes: candidatos a logo filtrados por el nombre de la empresa."""

from __future__ import annotations

from typing import Optional

from ..utils import name_match
from .search_engine import images_search


def image_search_candidates(client_name: str, queries: Optional[list[str]] = None) -> list[dict]:
    queries = queries or [f"{client_name} logo", f'"{client_name}" logo png']
    cands = []
    for query in queries:
        for rank, r in enumerate(images_search(query)):
            title = r.get("title", "")
            match = max(name_match(client_name, title), name_match(client_name, r.get("url", "")))
            if match < 0.99:  # todas las palabras del nombre deben aparecer
                continue
            w, h = int(r.get("width") or 0), int(r.get("height") or 0)
            score = 0.6 - rank * 0.01
            if "logo" in (title + r.get("image", "")).lower():
                score += 0.15
            if w and h and 0.33 <= w / h <= 3.5:
                score += 0.05
            cands.append({"url": r["image"], "source": "image_search", "score": round(score, 3),
                          "context": f"{title} | {r.get('url', '')}"})
        if cands:
            break
    return sorted(cands, key=lambda c: -c["score"])
