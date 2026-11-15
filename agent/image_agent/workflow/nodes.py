"""Nodos del workflow determinista: plan -> search -> evaluate."""

from __future__ import annotations

from PIL import Image

from ..config import MAX_CANDIDATES, WORKFLOW_STRATEGIES
from ..imaging import download_image, is_valid_logo_image, save_png
from ..tools import (
    favicon_candidates,
    find_official_site,
    image_search_candidates,
    scrape_logo_candidates,
    wikidata_logo_candidates,
)
from ..utils import log
from ..verifier import choose_logo, heuristic_choice
from .state import WorkflowState


def plan_node(state: WorkflowState) -> WorkflowState:
    """Elige la siguiente estrategia; None = se agotaron."""
    idx = state.get("strategy_idx", 0)
    if idx >= len(WORKFLOW_STRATEGIES):
        return {"current_strategy": None}
    return {"current_strategy": WORKFLOW_STRATEGIES[idx], "strategy_idx": idx + 1}


def search_node(state: WorkflowState) -> WorkflowState:
    """Ejecuta la estrategia actual y produce candidatos nuevos."""
    name, strategy = state["client_name"], state["current_strategy"]
    update: WorkflowState = {}
    site = state.get("official_site")
    if strategy in ("official_site", "favicon") and not state.get("site_searched"):
        site = find_official_site(name)
        update.update(official_site=site, site_searched=True)

    if strategy == "official_site":
        cands = scrape_logo_candidates(site, name) if site else []
    elif strategy == "wikidata":
        cands = wikidata_logo_candidates(name)
    elif strategy == "image_search":
        cands = image_search_candidates(name)
    elif strategy == "favicon":
        cands = favicon_candidates(site) if site else []
    else:
        cands = []

    tried = set(state.get("tried_urls", []))
    update["candidates"] = [c for c in cands if c["url"] not in tried][:MAX_CANDIDATES]
    log.info("[workflow:%s] %d candidatos", strategy, len(update["candidates"]))
    return update


def evaluate_node(state: WorkflowState) -> WorkflowState:
    """Descarga y valida candidatos; el verificador elige. Logo completo => objetivo cumplido."""
    name = state["client_name"]
    tried = list(state.get("tried_urls", []))
    valid: list[tuple[dict, Image.Image]] = []
    for cand in state.get("candidates", []):
        tried.append(cand["url"])
        img = download_image(cand["url"])
        if img is not None and is_valid_logo_image(img):
            valid.append((cand, img))
    update: WorkflowState = {"tried_urls": tried}
    if not valid:
        return update

    choice = choose_logo(valid, name) or heuristic_choice(valid)
    if choice["index"] is None:
        return update
    cand, img = valid[choice["index"]]
    if choice["kind"] == "full":
        update.update(image_path=save_png(img, name), source=cand["url"])
    elif not state.get("backup_url"):
        update["backup_url"] = cand["url"]
    return update
