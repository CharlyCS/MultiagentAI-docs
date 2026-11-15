from __future__ import annotations

from typing import Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict


class ReactState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    client_name: str
    steps: int                     # turnos del LLM (límite REACT_MAX_STEPS)
    # Salidas (las escribe la tool try_save_logo vía Command)
    image_path: Optional[str]
    source: Optional[str]
    backup_url: Optional[str]
