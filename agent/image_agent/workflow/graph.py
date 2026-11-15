"""
Workflow determinista (barato y rápido). Termina cuando encuentra el logo
completo o cuando se agotan las estrategias:

    START -> plan --(hay estrategia)--> search -> evaluate --(logo)--> END
               ^                                    |
               +-----------(siguiente)--------------+
             plan --(sin estrategias)--> END
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes import evaluate_node, plan_node, search_node
from .state import WorkflowState


def _after_plan(state: WorkflowState) -> str:
    return "search" if state.get("current_strategy") else END


def _after_evaluate(state: WorkflowState) -> str:
    return END if state.get("image_path") else "plan"


@lru_cache(maxsize=1)
def build_workflow_graph():
    g = StateGraph(WorkflowState)
    g.add_node("plan", plan_node)
    g.add_node("search", search_node)
    g.add_node("evaluate", evaluate_node)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", _after_plan, ["search", END])
    g.add_edge("search", "evaluate")
    g.add_conditional_edges("evaluate", _after_evaluate, ["plan", END])
    return g.compile()


def run_workflow(client_name: str) -> WorkflowState:
    return build_workflow_graph().invoke(
        {"client_name": client_name, "strategy_idx": 0, "tried_urls": []},
        config={"recursion_limit": 30},
    )
