"""
Writer con auto-revisión (patrón evaluator-optimizer):

    START -> draft -> review --(aprobado o límite de revisiones)--> END
               ^         |
               +--(corregir con las observaciones)--+
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes import draft_node, review_node
from .state import WriterContext, WriterState

from .nodes import DEFAULT_MAX_REVISIONS


def _after_review(state: WriterState) -> str:
    return END if state.get("done") else "draft"


@lru_cache(maxsize=1)
def build_writer_graph():
    graph = StateGraph(state_schema=WriterState, context_schema=WriterContext)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "review")
    graph.add_conditional_edges("review", _after_review, ["draft", END])
    return graph.compile()
