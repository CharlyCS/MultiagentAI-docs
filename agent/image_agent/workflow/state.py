from __future__ import annotations

from typing import Optional

from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    client_name: str
    strategy_idx: int              # siguiente estrategia a probar
    current_strategy: Optional[str]
    official_site: Optional[str]
    site_searched: bool
    candidates: list[dict]
    tried_urls: list[str]
    # Salidas
    image_path: Optional[str]      # logo completo encontrado
    source: Optional[str]
    backup_url: Optional[str]      # ícono válido, por si no aparece el logo completo
