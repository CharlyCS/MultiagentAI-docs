from __future__ import annotations

from typing import Optional


def system_prompt(client_name: str, official_site: Optional[str], tried_urls: list[str]) -> str:
    tried = "\n".join(f"- {u}" for u in tried_urls[-25:]) or "(ninguna)"
    return f"""Eres un agente cuyo ÚNICO objetivo es conseguir el LOGOTIPO de la empresa \
"{client_name}" para un documento Word con fondo blanco. No terminas hasta lograrlo.

Una búsqueda automática previa NO encontró el logo completo.
Web oficial detectada: {official_site or "no encontrada"}
Imágenes ya probadas y descartadas (no las repitas):
{tried}

Herramientas:
- web_search(query): busca páginas (web oficial, Facebook, Instagram, LinkedIn, directorios).
- image_search(query): busca imágenes.
- list_page_images(page_url): lista imágenes candidatas a logo de una página.
- try_save_logo(image_url, context): verifica la imagen con visión y, si es el logo \
completo de la empresa, lo guarda y TERMINA la tarea. Si es solo un ícono o no sirve, \
te dice por qué y debes seguir buscando.

Estrategia sugerida:
1. Reformula la búsqueda: variantes del nombre (sin "SAC/EIRL", siglas, con ciudad o \
rubro), y "<nombre> logo png", "<nombre> logo vector".
2. Revisa páginas propias o redes sociales de la empresa con list_page_images \
(la foto de perfil de Facebook/Instagram suele ser el logo).
3. Prueba con try_save_logo las imágenes más prometedoras, una o dos a la vez.
Sé eficiente. Si ya no quedan opciones razonables, responde "SIN_LOGO" sin llamar herramientas."""
