"""
Verificador con visión: el LLM compara candidatos y elige el logo.
Devuelve None cuando no hay LLM disponible (entonces se usa la heurística).
"""

from __future__ import annotations

import json
from typing import Optional

from PIL import Image

from .config import llm_enabled, llm_model_name
from .imaging import preview_b64
from .utils import log

_RULES = (
    "Cada imagen se muestra DOS veces lado a lado: sobre fondo blanco (izquierda) y "
    "sobre fondo oscuro (derecha). Muchos logos son blancos y solo se ven bien en el "
    "fondo oscuro: eso es VÁLIDO (luego se adapta para el documento).\n"
    "Reglas:\n"
    "- Rechaza fotos de personas/eventos, banners publicitarios, fotos de productos, "
    "íconos genéricos de redes sociales y logos de OTRAS empresas o marcas.\n"
    "- El logo que la empresa muestra en el encabezado de su WEB OFICIAL es la fuente "
    "más confiable y su versión ACTUAL: prefiérelo sobre imágenes de terceros.\n"
    "- kind='full' si es el logotipo completo (normalmente incluye el nombre); "
    "kind='icon' si es solo el ícono/isotipo/favicon de la empresa.\n"
    "- Prefiere 'full' sobre 'icon'.\n"
)


def choose_logo(valid: list[tuple[dict, Image.Image]], client_name: str) -> Optional[dict]:
    """
    Compara todos los candidatos en UNA llamada.
    Devuelve {"index": int|None, "kind": "full"|"icon"|None, "reason": str} o None sin LLM.
    """
    if not valid or not llm_enabled():
        return None
    try:
        from openai import OpenAI

        content: list[dict] = [{"type": "text", "text": (
            f'Busco el LOGOTIPO OFICIAL de la empresa "{client_name}" para un informe. '
            "Te muestro imágenes candidatas con su origen.\n" + _RULES +
            'Responde SOLO JSON: {"index": <número de la mejor imagen o null si '
            'ninguna sirve>, "kind": "full"|"icon", "reason": "<breve>"}')}]
        for i, (cand, img) in enumerate(valid, 1):
            content.append({"type": "text", "text": f"Imagen {i} | origen: {cand['context'][:160]}"})
            content.append({"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{preview_b64(img)}", "detail": "low"}})

        resp = OpenAI().chat.completions.create(
            model=llm_model_name(),
            temperature=0,
            max_tokens=150,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": content}],
        )
        answer = json.loads(resp.choices[0].message.content or "{}")
        log.info("  verificador LLM: %s", answer)
        idx = answer.get("index")
        if isinstance(idx, int) and 1 <= idx <= len(valid):
            return {"index": idx - 1, "kind": answer.get("kind") or "full",
                    "reason": answer.get("reason", "")}
        return {"index": None, "kind": None, "reason": answer.get("reason", "")}
    except Exception as e:
        log.warning("Verificador LLM no disponible: %s", e)
        return None


def heuristic_choice(valid: list[tuple[dict, Image.Image]]) -> dict:
    """Sin LLM: el candidato con mejor puntuación; favicon o score bajo => 'icon'."""
    i, (cand, _) = max(enumerate(valid), key=lambda v: v[1][0]["score"])
    kind = "full" if cand["score"] >= 0.5 and cand["source"] != "favicon" else "icon"
    return {"index": i, "kind": kind, "reason": "heurística"}
