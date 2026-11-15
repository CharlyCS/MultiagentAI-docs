from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from typing_extensions import Annotated, TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
import yaml
import docxtpl


data = yaml.safe_load(open("data/config.yaml"))

def reducer(a: list, b: int | None) -> list:
    if b is not None:
        return a + [b]
    return a


class State(TypedDict):
    question: str

class Context(TypedDict):
    r: float


def read_doc(state: State, runtime: Runtime[Context]) -> dict:

    return {"x": next_value}


graph = StateGraph(state_schema=State, context_schema=Context)
graph.add_node("read_doc", read_doc)
graph.add_edge(START, "read_doc", reducer=reducer)
graph.set_entry_point("read_doc")
graph.set_finish_point("A")
compiled = graph.compile()



graph.add_node()

step1 = compiled.invoke({"x": 0.5}, context={"r": 3.0})
# {'x': [0.5, 0.75]}

