"""
Orquestador multi-agente (LangGraph) que genera el informe de servicio en Word.

    START -> read_doc ─┬─> image_agent  (logo del cliente: ImageWebAgent) ─┐
                       ├─> writer_agent (descripción + tabla Registro)     ├─> render_doc -> END
                       └─> photos       (fotos del evento, locales)       ─┘

Las tres ramas corren EN PARALELO; render_doc espera a las tres.
Uso:
    python orchestrator.py
    python orchestrator.py --notes "Se instalaron 4 pantallas LED..." --config data/config.yaml
"""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from typing_extensions import Annotated, TypedDict

from agent.image_agent.utils import slugify
from agent.writer_agent import WriterAgent
from agent.writer_agent.nodes import fallback_report
from core import (CONFIG_PATH, OUTPUT_DIR, TEMPLATE_PATH, collect_photos, load_config,
                  render_report, resolve_logo, setup_logging)
from core.settings import log

PLACEHOLDER_NOTES = {"", "text", "-", "n/a"}


def reducer(a: list, b: list | None) -> list:
    """Acumula avisos de las ramas paralelas (varias escriben 'warnings' a la vez)."""
    if b is not None:
        return a + b
    return a


class State(TypedDict, total=False):
    question: str                      # notas del ingeniero (config.yaml -> description)
    data: dict                         # config.yaml completo
    logo_path: str
    logo_info: dict
    photos: list[str]
    description: str
    raw: list[dict]
    writer_info: dict
    output_path: str
    warnings: Annotated[list[str], reducer]


class Context(TypedDict, total=False):
    config_path: str
    template_path: str
    output_dir: str
    max_revisions: int                 # ciclos del writer (redactar -> revisar)
    max_length: int                    # palabras máximas de la descripción
    notes: str                         # sobrescribe 'description' de config.yaml


# ----------------------------------------------------------------------------- nodos
def read_doc(state: State, runtime: Runtime[Context]) -> dict:
    ctx = runtime.context or {}
    data = load_config(ctx.get("config_path", CONFIG_PATH))
    question = ctx.get("notes") or str(data.get("description") or "")
    if question.strip().lower() in PLACEHOLDER_NOTES:
        question = ""
    log.info("Cliente: %s | Lugar: %s | Fecha: %s", data["client"],
             data["table"].get("place"), data["table"].get("date"))
    return {"data": data, "question": question, "warnings": []}


def image_agent_node(state: State) -> dict:
    data = state["data"]
    cfg = data["images"].get("picture_logo", {}) or {}
    logo_path, info = resolve_logo(data["client"], cfg)
    warnings = []
    if info.get("is_placeholder"):
        warnings.append("No se encontró el logo en la web: se usó un logo de texto.")
    log.info("Logo: %s (%s)", logo_path, info.get("found_by"))
    return {"logo_path": logo_path, "logo_info": info, "warnings": warnings}


def writer_agent_node(state: State, runtime: Runtime[Context]) -> dict:
    ctx = runtime.context or {}
    try:
        writer = WriterAgent(state["question"], data=state["data"],
                             max_revisions=ctx.get("max_revisions", 3))
        result = writer.run(max_length=ctx.get("max_length", 180))
        warnings = [] if result.get("approved") else [
            "El texto no fue aprobado por el revisor tras el máximo de revisiones; revísalo."]
        return {"description": result["description"], "raw": result["raw"],
                "writer_info": {"revisions": result.get("revisions"),
                                "approved": result.get("approved")},
                "warnings": warnings}
    except Exception as e:  # el informe se genera igual
        log.exception("Writer falló")
        fb = fallback_report(state["data"], state["question"])
        return {**fb, "writer_info": {"error": str(e)},
                "warnings": [f"Writer falló ({e}); se usó texto por defecto."]}


def photos_node(state: State) -> dict:
    cfg = state["data"]["images"].get("pictures_event", {}) or {}
    if (cfg.get("origin") or "local") != "local":
        return {"photos": [], "warnings": ["pictures_event: solo se soporta origin=local."]}
    photos, warnings = collect_photos(cfg.get("root", "fotos"))
    return {"photos": photos, "warnings": warnings}


def render_doc(state: State, runtime: Runtime[Context]) -> dict:
    ctx = runtime.context or {}
    data = state["data"]
    date = str(data["table"].get("date") or datetime.now().strftime("%d/%m/%Y")).replace("/", "-")
    out = Path(ctx.get("output_dir", OUTPUT_DIR)) / f"Informe_{slugify(data['client'])}_{date}.docx"
    path = render_report(ctx.get("template_path", TEMPLATE_PATH), out, data=data,
                         description=state["description"], raw=state["raw"],
                         logo_path=state["logo_path"], photos=state.get("photos", []))
    return {"output_path": path}


# ----------------------------------------------------------------------------- grafo
def build_graph(checkpointer=None):
    graph = StateGraph(state_schema=State, context_schema=Context)
    graph.add_node("read_doc", read_doc)
    graph.add_node("image_agent", image_agent_node)
    graph.add_node("writer_agent", writer_agent_node)
    graph.add_node("photos", photos_node)
    graph.add_node("render_doc", render_doc)

    graph.add_edge(START, "read_doc")
    for branch in ("image_agent", "writer_agent", "photos"):      # fan-out paralelo
        graph.add_edge("read_doc", branch)
    graph.add_edge(["image_agent", "writer_agent", "photos"], "render_doc")  # fan-in
    graph.add_edge("render_doc", END)
    return graph.compile(checkpointer=checkpointer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el informe de servicio (.docx).")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--template", default=str(TEMPLATE_PATH))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--notes", default="", help="Notas del ingeniero (sobrescribe description)")
    parser.add_argument("--max-revisions", type=int, default=3)
    args = parser.parse_args()
    setup_logging()

    compiled = build_graph(checkpointer=InMemorySaver())
    step1 = compiled.invoke(
        {},
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
        context={"config_path": args.config, "template_path": args.template,
                 "output_dir": args.output_dir, "notes": args.notes,
                 "max_revisions": args.max_revisions, "max_length": 180},
    )

    print("\n================ RESULTADO ================")
    print("Informe :", step1["output_path"])
    print("Logo    :", step1["logo_path"], "|", step1.get("logo_info", {}).get("found_by"))
    print("Fotos   :", len(step1.get("photos", [])))
    print("Writer  :", step1.get("writer_info"))
    for w in step1.get("warnings", []):
        print("AVISO   :", w)


if __name__ == "__main__":
    main()
