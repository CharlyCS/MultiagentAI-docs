"""
ImageWebAgent: consigue el logo de una empresa y devuelve su ruta en data/image/.

Arquitectura híbrida (grafo LangGraph de nivel superior):

    START -> workflow --(logo completo)--> END
                 |
                 +--(no, y hay LLM)--> react_agent --(logo)--> END
                 |                          |
                 +--(no, sin LLM)-----------+--(no)--> finalize --> END

- workflow/     : estrategias fijas y baratas (web oficial, Wikidata, imágenes,
                  favicon). Resuelve la mayoría de casos en segundos.
- react_agent/  : agente ReAct (LLM + ToolNode) que decide cómo seguir buscando
                  (reformula nombres, revisa redes sociales, etc.). Solo se paga
                  su costo en los casos difíciles.
- finalize      : ícono de respaldo si se encontró alguno; si no, logo de texto.

Todas las herramientas de búsqueda son gratuitas y sin API key. El LLM (OpenAI,
modelo de OPENAI_MODEL) verifica imágenes y conduce el ReAct; desactivar con
LOGO_VERIFY_WITH_LLM=0 (entonces solo workflow + heurística).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .config import llm_enabled
from .imaging import download_image, placeholder_logo, save_png
from .react_agent import run_react_agent
from .utils import log
from .workflow import run_workflow


class ImageAgentState(TypedDict, total=False):
    client_name: str
    official_site: Optional[str]
    tried_urls: list[str]
    backup_url: Optional[str]
    # Resultado
    image_path: Optional[str]
    source: Optional[str]
    found_by: Optional[str]        # "workflow" | "react_agent" | "backup_icon" | "placeholder"
    is_placeholder: bool


def workflow_node(state: ImageAgentState) -> ImageAgentState:
    res = run_workflow(state["client_name"])
    update: ImageAgentState = {
        "official_site": res.get("official_site"),
        "tried_urls": res.get("tried_urls", []),
        "backup_url": res.get("backup_url"),
    }
    if res.get("image_path"):
        update.update(image_path=res["image_path"], source=res.get("source"),
                      found_by="workflow", is_placeholder=False)
    return update


def react_node(state: ImageAgentState) -> ImageAgentState:
    log.info("Workflow sin logo completo -> se activa el agente ReAct")
    res = run_react_agent(state["client_name"], state.get("official_site"),
                          state.get("tried_urls"), state.get("backup_url"))
    update: ImageAgentState = {"backup_url": res.get("backup_url") or state.get("backup_url")}
    if res.get("image_path"):
        update.update(image_path=res["image_path"], source=res.get("source"),
                      found_by="react_agent", is_placeholder=False)
    return update


def finalize_node(state: ImageAgentState) -> ImageAgentState:
    name, backup = state["client_name"], state.get("backup_url")
    if backup:
        img = download_image(backup)
        if img is not None:
            log.info("Sin logo completo; se usa el ícono de respaldo.")
            return {"image_path": save_png(img, name), "source": backup,
                    "found_by": "backup_icon", "is_placeholder": False}
    log.warning("No se encontró logo en la web para '%s'; se genera placeholder.", name)
    return {"image_path": save_png(placeholder_logo(name), name), "source": "generated",
            "found_by": "placeholder", "is_placeholder": True}


def _after_workflow(state: ImageAgentState) -> str:
    if state.get("image_path"):
        return END
    return "react_agent" if llm_enabled() else "finalize"


def _after_react(state: ImageAgentState) -> str:
    return END if state.get("image_path") else "finalize"


@lru_cache(maxsize=1)
def build_image_agent_graph():
    g = StateGraph(ImageAgentState)
    g.add_node("workflow", workflow_node)
    g.add_node("react_agent", react_node)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "workflow")
    g.add_conditional_edges("workflow", _after_workflow, ["react_agent", "finalize", END])
    g.add_conditional_edges("react_agent", _after_react, ["finalize", END])
    g.add_edge("finalize", END)
    return g.compile()


class ImageWebAgent:
    """Uso: ImageWebAgent("Ghost Producciones").run() -> 'data/image/logo_ghostproducciones.png'"""

    def __init__(self, client_name: str) -> None:
        if not client_name or not client_name.strip():
            raise ValueError("client_name vacío")
        self.client_name = client_name.strip()
        self.result: ImageAgentState = {}

    def run(self) -> str:
        """Ejecuta el agente y devuelve la ruta (relativa al proyecto) del logo PNG."""
        self.result = build_image_agent_graph().invoke({"client_name": self.client_name})
        return self.result["image_path"]


if __name__ == "__main__":  # compatibilidad: python -m agent.image_agent.image_web_agent
    from .__main__ import main

    main()
