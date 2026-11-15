"""Nodos del writer: draft (redacta) -> review (revisor crítico)."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from .prompt import NO_NOTES_RULE, REVIEW_PROMPT, prompt_template, revision_prompt
from .schemas import Activity, Report, Review
from .state import WriterContext, WriterState

load_dotenv()
model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
api_key = os.getenv("OPENAI_API_KEY")

log = logging.getLogger("writer_agent")
DEFAULT_MAX_REVISIONS = 3


@lru_cache(maxsize=4)
def _llm(temperature: float):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model_name, api_key=api_key, temperature=temperature)


def _event_summary(data: dict) -> str:
    table = data.get("table", {}) or {}
    return (f"Cliente: {data.get('client')} | Lugar: {table.get('place')} | "
            f"Fecha: {table.get('date')} | Ingeniero: {data.get('engineer')} | "
            f"Ventas: {data.get('sales_team')}")


def fallback_report(data: dict, question: str) -> dict:
    """Sin LLM: texto mínimo correcto (regla: si no hay info => 'satisfactorio')."""
    table = data.get("table", {}) or {}
    text = (question or "").strip()
    if not text or text.lower() == "text":
        text = (f"El servicio técnico para {data.get('client')} en {table.get('place')} "
                f"el {table.get('date')} se desarrolló de manera satisfactoria.")
    return {"description": text,
            "raw": [{"descripcion": "Servicio técnico del evento", "estado": "Completado"}]}


def draft_node(state: WriterState, runtime: Runtime[WriterContext]) -> WriterState:
    ctx = runtime.context or {}
    max_length = ctx.get("max_length", 180)
    revision = state.get("revision", 0) + 1
    if not api_key:
        log.warning("Sin OPENAI_API_KEY: se usa texto por defecto.")
        return {"draft": fallback_report(state["data"], state["question"]),
                "revision": revision, "approved": True}

    messages = [SystemMessage(prompt_template(state["question"], state["data"], max_length))]
    if not (state["question"] or "").strip():
        messages.append(SystemMessage(NO_NOTES_RULE))
    if state.get("draft") and state.get("feedback"):
        messages += [HumanMessage("Borrador anterior:\n" + json.dumps(state["draft"], ensure_ascii=False)),
                     HumanMessage(revision_prompt(state["feedback"]))]
    else:
        messages.append(HumanMessage("Redacta el informe."))

    report: Report = _llm(0.4).with_structured_output(Report).invoke(messages)
    if not (state["question"] or "").strip():
        # Sin notas no hay actividades reales que registrar: una sola fila general.
        report.raw = [Activity(descripcion="Servicio técnico del evento", estado="Completado")]
    log.info("[writer] borrador v%d (%d palabras, %d actividades)", revision,
             len(report.description.split()), len(report.raw))
    return {"draft": report.model_dump(), "revision": revision}


def review_node(state: WriterState, runtime: Runtime[WriterContext]) -> WriterState:
    ctx = runtime.context or {}
    if state.get("approved"):  # fallback sin LLM
        return {"done": True}
    prompt = REVIEW_PROMPT.format(
        event=_event_summary(state["data"]),
        observation=state["question"] or "(sin notas)",
        draft=json.dumps(state["draft"], ensure_ascii=False, indent=2),
    )
    review: Review = _llm(0).with_structured_output(Review).invoke([HumanMessage(prompt)])
    # Chequeos deterministas (los LLM no cuentan bien palabras)
    max_length = ctx.get("max_length", 180)
    n_words = len(state["draft"]["description"].split())
    issues = [i for i in review.critical_issues if "palabra" not in i.lower()]
    if n_words > max_length:
        issues.append(f"La descripción tiene {n_words} palabras; redúcela a máximo {max_length}.")
    if not state["draft"].get("raw"):
        issues.append("La tabla de actividades (raw) está vacía.")
    approved = not issues
    log.info("[writer] revisión v%d: %s %s", state.get("revision", 0),
             "APROBADO" if approved else "CORREGIR", issues or "")
    if review.minor_suggestions:
        log.debug("[writer] sugerencias menores: %s", review.minor_suggestions)
    max_rev = ctx.get("max_revisions", DEFAULT_MAX_REVISIONS)
    return {"approved": approved, "feedback": issues,
            "done": approved or state.get("revision", 0) >= max_rev}
