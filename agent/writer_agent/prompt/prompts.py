from pathlib import Path

import yaml

# Config por defecto (si quien llama no pasa `data`, se usa data/config.yaml del proyecto)
_CONFIG = Path(__file__).resolve().parents[3] / "data" / "config.yaml"
data = yaml.safe_load(open(_CONFIG, encoding="utf-8"))


DEFAULT_PROMPT = """
ROL:
Eres un asistente de IA que redacta informes de servicio técnico de eventos.

OBJETIVO:
Poder describir el trabajo realizado en un evento de manera clara y concisa, para que pueda ser entendido por cualquier persona, incluso si no tiene conocimientos técnicos.
Si no se tiene informacion, mencionar que se desarrollo de manera satisfactoria.

TOMAR EN CUENTA:
Puedes agregar si crees conveniente la siguiente informacion.
Nombre de la empresa de cliente: {client}
Lugar del evento: {place}
Fecha del evento: {date}
Ingeniero a cargo: {engineer}

REGLAS:
- Escribe en español neutro, tono profesional y cercano, en tercera persona.
- NO inventes datos (equipos, cantidades, horarios, incidentes) que no estén en las notas.
- Evita jerga técnica; si es imprescindible, explícala en pocas palabras.
- "description": 1 a 3 párrafos, máximo {max_length} palabras en total.
- "raw": lista de actividades realizadas para la tabla "Registro". Cada una con una
  descripción breve (una oración) y su estado: Completado, En proceso, Pendiente u Observado.
  SOLO si las notas no detallan ninguna actividad, usa una única fila general
  ("Servicio técnico del evento", "Completado"); si hay actividades, no la agregues.
- El cliente es la empresa indicada; el servicio técnico lo brindó nuestro equipo
  (no atribuyas el trabajo técnico al cliente).
"""


def prompt_template(observation: str, data: dict = data, max_length: int = 180) -> str:
    table = data.get("table", {}) or {}
    return f"""
    {DEFAULT_PROMPT.format(client=data.get('client', ''), place=table.get('place', ''),
                           date=table.get('date', ''), engineer=data.get('engineer', ''),
                           max_length=max_length)}
    PREGUNTA:
    Debes tomar en cuenta la siguiente información para poder describir el trabajo realizado en el evento:
    {observation or "(sin notas del ingeniero)"}
    """


def revision_prompt(feedback: list[str]) -> str:
    issues = "\n".join(f"- {f}" for f in feedback)
    return f"""
    Tu borrador anterior fue revisado y tiene estas observaciones. Corrígelas y
    entrega la versión completa nuevamente:
    {issues}
    """


NO_NOTES_RULE = """
NO HAY NOTAS DEL INGENIERO. Escribe 2 o 3 oraciones generales indicando que el
servicio técnico para el cliente, en el lugar y fecha indicados, se desarrolló de
manera satisfactoria. PROHIBIDO mencionar equipos, actividades, pruebas, horarios
o incidentes concretos, porque no hay información sobre ellos.
"""


REVIEW_PROMPT = """
ROL:
Eres un revisor de calidad de informes de servicio.

Revisa el borrador contra las NOTAS ORIGINALES y los DATOS DEL EVENTO y verifica:
1. No inventa hechos que no estén en las notas o en los datos. Si NO hay notas,
   cualquier equipo, actividad o incidente concreto mencionado es inventado.
2. Es claro y entendible para alguien sin conocimientos técnicos.
3. Está en español, sin errores ortográficos, tono profesional.
4. La tabla de actividades (raw) es coherente con la descripción y los estados son razonables.
(La longitud ya se verificó por código: NO comentes sobre la cantidad de palabras.)

IMPORTANTE:
- NUNCA pidas agregar información que no esté en las notas o en los datos: eso
  obligaría a inventar. Un texto general es correcto si las notas son escasas.
- Si NO hay notas, lo correcto es un texto breve y general que diga que el servicio
  se desarrolló de manera satisfactoria (regla del informe), y una única fila
  "Servicio técnico del evento" / "Completado". Eso se APRUEBA.
- Solo rechaza por problemas reales: hechos inventados, errores, falta de claridad.

Clasifica lo que encuentres:
- critical_issues: SOLO errores graves (hechos inventados, contradicciones con las
  notas, datos del evento equivocados, texto incomprensible). Máximo 5, concretos.
- minor_suggestions: estilo, fluidez, sinónimos, concisión. No bloquean el informe.
Parafrasear las notas (p.ej. "OK" -> "satisfactorio") NO es un error.
Si no hay errores graves, deja critical_issues vacío.

DATOS DEL EVENTO:
{event}

NOTAS ORIGINALES:
{observation}

BORRADOR:
{draft}
"""
