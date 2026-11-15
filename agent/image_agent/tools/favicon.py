"""Favicon grande de un dominio (servicios gratuitos de Google y DuckDuckGo)."""

from __future__ import annotations

from ..utils import domain_of


def favicon_candidates(site_url: str) -> list[dict]:
    dom = domain_of(site_url)
    return [
        {"url": f"https://www.google.com/s2/favicons?domain={dom}&sz=256",
         "source": "favicon", "score": 0.3, "context": f"favicon {dom}"},
        {"url": f"https://icons.duckduckgo.com/ip3/{dom}.ico",
         "source": "favicon", "score": 0.25, "context": f"favicon {dom}"},
    ]
