from __future__ import annotations

from typing import Optional

from typing_extensions import TypedDict


class WriterState(TypedDict, total=False):
    question: str                  # notas / observaciones del ingeniero
    data: dict                     # datos del evento (config.yaml)
    draft: Optional[dict]          # Report serializado {description, raw}
    feedback: list[str]            # observaciones del revisor
    revision: int
    approved: bool
    done: bool                     # aprobado o se alcanzó max_revisions


class WriterContext(TypedDict, total=False):
    max_revisions: int             # ciclos redactar -> revisar
    max_length: int                # palabras máximas de la descripción
