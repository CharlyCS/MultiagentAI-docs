"""
image_agent: obtiene el logo de una empresa (client_name) y devuelve su ruta.

    from agent.image_agent import ImageWebAgent
    path = ImageWebAgent("Ghost Producciones").run()   # 'data/image/logo_ghostproducciones.png'

Estructura:
    config.py          rutas, límites y variables de entorno
    utils.py           texto (normalización, matching) y HTTP
    imaging.py         descarga, validación, recorte, guardado y placeholder
    verifier.py        verificación con visión (LLM) + heurística sin LLM
    tools/             búsquedas gratuitas (funciones puras, sin LLM)
    workflow/          paso 1: grafo determinista plan -> search -> evaluate
    react_agent/       paso 2: agente ReAct (LLM + ToolNode) para casos difíciles
    image_web_agent.py grafo principal que une todo + clase ImageWebAgent
"""

from .image_web_agent import ImageWebAgent, build_image_agent_graph

__all__ = ["ImageWebAgent", "build_image_agent_graph"]
