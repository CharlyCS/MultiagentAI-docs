"""Salidas estructuradas del writer (las fuerza el LLM con structured output)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Activity(BaseModel):
    descripcion: str = Field(description="Actividad realizada, una oración breve y clara.")
    estado: Literal["Completado", "En proceso", "Pendiente", "Observado"]


class Report(BaseModel):
    description: str = Field(description="Descripción del trabajo realizado, 1 a 3 párrafos.")
    raw: list[Activity] = Field(description="Filas de la tabla 'Registro'.")


class Review(BaseModel):
    critical_issues: list[str] = Field(
        default_factory=list,
        description="SOLO problemas graves: hechos inventados, contradicciones con las notas, "
                    "errores de datos (cliente, lugar, fecha) o texto incomprensible.")
    minor_suggestions: list[str] = Field(
        default_factory=list, description="Mejoras opcionales de estilo o redacción.")

    @property
    def approved(self) -> bool:
        return not self.critical_issues
