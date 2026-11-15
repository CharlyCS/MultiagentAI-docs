"""
WriterAgent: redacta la descripción del servicio y la tabla "Registro" a partir de
las notas del ingeniero, y se auto-revisa con un segundo LLM (ver graph.py).
"""

from __future__ import annotations

from typing import Optional

from .graph import DEFAULT_MAX_REVISIONS, build_writer_graph
from .nodes import model_name
from .prompt.prompts import data as default_data


class WriterAgent:
    """
    Uso:
        writer = WriterAgent(question="notas del ingeniero...", data=config)
        result = writer.run()      # {"description": str, "raw": [{"descripcion", "estado"}]}
        texto = writer.generate_text()
    """

    def __init__(self, question: str, data: Optional[dict] = None,
                 max_revisions: int = DEFAULT_MAX_REVISIONS) -> None:
        self.model_name = model_name
        self.question = question
        self.data = data or default_data
        self.max_revisions = max_revisions
        self.result: dict = {}

    def run(self, max_length: int = 180) -> dict:
        state = build_writer_graph().invoke(
            {"question": self.question, "data": self.data, "revision": 0, "feedback": []},
            context={"max_revisions": self.max_revisions, "max_length": max_length},
        )
        self.result = {**state["draft"], "revisions": state.get("revision", 1),
                       "approved": state.get("approved", False)}
        return self.result

    def generate_text(self, max_length: int = 180) -> str:
        generated_text = (self.result or self.run(max_length))["description"]
        return generated_text


if __name__ == "__main__":
    import json
    import logging
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    notes = " ".join(sys.argv[1:]) or default_data.get("description", "")
    print(json.dumps(WriterAgent(notes).run(), ensure_ascii=False, indent=2))
