"""
Agente ReAct: el LLM decide qué tool usar en cada paso (ToolNode + tools_condition).

    START -> agent --(tool_calls)--> tools --(logo guardado)--> END
               ^                       |
               +------(seguir)---------+
             agent --(sin tool_calls / límite de pasos)--> END
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ..config import REACT_MAX_STEPS, llm_model_name
from ..utils import log
from .prompts import system_prompt
from .state import ReactState
from .tools import REACT_TOOLS


@lru_cache(maxsize=1)
def _llm():
    return ChatOpenAI(model=llm_model_name(), temperature=0).bind_tools(REACT_TOOLS)


def agent_node(state: ReactState) -> ReactState:
    steps = state.get("steps", 0) + 1
    response = _llm().invoke(state["messages"])
    calls = getattr(response, "tool_calls", None) or []
    log.info("[react] paso %d: %s", steps,
             ", ".join(f"{c['name']}({str(c['args'])[:70]})" for c in calls)
             if calls else str(response.content)[:120])
    return {"messages": [response], "steps": steps}


def _after_agent(state: ReactState) -> str:
    if state.get("steps", 0) >= REACT_MAX_STEPS:
        log.warning("[react] límite de %d pasos alcanzado", REACT_MAX_STEPS)
        return END
    return tools_condition(state)  # "tools" o END


def _after_tools(state: ReactState) -> str:
    return END if state.get("image_path") else "agent"


@lru_cache(maxsize=1)
def build_react_graph():
    g = StateGraph(ReactState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(REACT_TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _after_agent, ["tools", END])
    g.add_conditional_edges("tools", _after_tools, ["agent", END])
    return g.compile()


def run_react_agent(client_name: str, official_site: Optional[str] = None,
                    tried_urls: Optional[list[str]] = None,
                    backup_url: Optional[str] = None) -> ReactState:
    init: ReactState = {
        "client_name": client_name,
        "steps": 0,
        "backup_url": backup_url,
        "messages": [
            SystemMessage(system_prompt(client_name, official_site, tried_urls or [])),
            HumanMessage(f'Consigue el logo de "{client_name}".'),
        ],
    }
    try:
        return build_react_graph().invoke(init, config={"recursion_limit": 3 * REACT_MAX_STEPS + 5})
    except GraphRecursionError:
        log.warning("[react] recursion limit alcanzado")
        return init
