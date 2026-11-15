"""Encontrar la web oficial de la empresa y extraer candidatos a logo de su HTML."""

from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..config import DOMAIN_GUESS_TLDS, NON_OFFICIAL_DOMAINS
from ..utils import domain_of, http_get, log, name_match, unwrap_cdn_url

_NOT_LOGO = re.compile(r"bann+er|hero|slide|card|background|\bbg\b|equipo|team|foto|photo|"
                       r"gallery|galeria|portfolio|cliente|client|partner|sponsor")
_SOCIAL = re.compile(r"facebook|instagram|twitter|linkedin|youtube|tiktok|whatsapp|"
                     r"icon-|/icons?/|flag|bandera|payment|visa|mastercard")


def find_official_site(client_name: str) -> Optional[str]:
    """Busca la web oficial: el dominio que contiene el nombre de la empresa gana."""
    from .search_engine import web_search

    best, best_score = None, 0.0
    for query in (f"{client_name} sitio oficial", f"{client_name} empresa"):
        for rank, r in enumerate(web_search(query)):
            url = r.get("href", "")
            dom = domain_of(url)
            if not dom or any(b in dom for b in NON_OFFICIAL_DOMAINS):
                continue
            score = 2.0 * name_match(client_name, dom.split(".")[0])
            score += name_match(client_name, r.get("title", ""))
            score -= rank * 0.05
            if score > best_score:
                parsed = urlparse(url)
                best, best_score = f"{parsed.scheme}://{parsed.netloc}/", score
        if best_score >= 2.0:
            break
    if best_score < 1.5:
        # El buscador gratis falló o no fue concluyente: probar dominios directos.
        guessed = guess_official_domain(client_name)
        if guessed:
            best, best_score = guessed, 2.0
    log.info("Web oficial: %s (score %.2f)", best, best_score)
    return best if best_score >= 1.5 else None


def guess_official_domain(client_name: str) -> Optional[str]:
    """Prueba <nombre>.com / .pe / ... y valida que la página hable de la empresa."""
    from ..utils import name_tokens, slugify

    stems = list(dict.fromkeys([slugify(client_name), "-".join(name_tokens(client_name))]))
    for stem in filter(None, stems):
        for tld in DOMAIN_GUESS_TLDS:
            url = f"https://{stem}{tld}/"
            r = http_get(url)
            if r is None or "html" not in r.headers.get("Content-Type", ""):
                continue
            title = BeautifulSoup(r.text[:20000], "html.parser").title
            text = (title.get_text() if title else "") + " " + domain_of(r.url)
            if name_match(client_name, text) >= 0.99 and domain_of(r.url).startswith(stem[:4]):
                log.info("Web oficial deducida: %s", r.url)
                parsed = urlparse(r.url)
                return f"{parsed.scheme}://{parsed.netloc}/"
    return None


def _img_src(img: Tag) -> Optional[str]:
    """La mejor fuente de un <img>: la de mayor ancho en srcset, si no src/data-src."""
    for attr in ("srcset", "data-srcset"):
        if img.get(attr):
            best, best_w = None, -1
            # separador = coma + espacio (las URLs de CDNs pueden llevar comas: "to_auto,w_501")
            for part in re.split(r",\s+", img[attr].strip()):
                bits = part.strip().split()
                if not bits:
                    continue
                w = int(re.sub(r"\D", "", bits[1]) or 0) if len(bits) > 1 else 0
                if w > best_w:
                    best, best_w = bits[0], w
            if best:
                return best
    for attr in ("data-src", "data-lazy-src", "src"):
        src = img.get(attr)
        if src and not src.startswith("data:"):
            return src
    return None


def _attrs_text(el: Tag) -> str:
    return " ".join([" ".join(el.get("class", []) or []), el.get("id", "") or ""]).lower()


def scrape_logo_candidates(page_url: str, client_name: str = "",
                           source: str = "official_site") -> list[dict]:
    """
    Extrae candidatos a logo de una página, de más a menos fiable:
      1. <img> del encabezado (header/nav, contenedor "logo", enlace a la home)
      2. JSON-LD schema.org "logo"
      3. otros <img> con "logo"
      4. apple-touch-icon / icon / og:image
    Devuelve [{url, source, score, context}] ordenado por score.
    """
    r = http_get(page_url)
    if r is None:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    base = r.url
    home = urlparse(base).netloc
    cands: dict[str, dict] = {}

    def add(src: Optional[str], score: float, ctx: str) -> None:
        if not src or src.startswith("data:"):
            return
        url = urljoin(base, src.strip())
        key = unwrap_cdn_url(url)  # mismo logo servido por CDN y directo = 1 candidato
        if key not in cands or score > cands[key]["score"]:
            cands[key] = {"url": url, "source": source, "score": round(score, 3), "context": ctx}

    # 1 y 3) <img> con señales de logo
    header_logo_found = False
    for img in soup.find_all("img"):
        src = _img_src(img)
        if not src:
            continue
        own = " ".join([src, img.get("alt", "") or "", img.get("title", "") or "",
                        _attrs_text(img)]).lower()
        parents = [p for p in img.parents if isinstance(p, Tag)][:4]
        parent_txt = " ".join(_attrs_text(p) for p in parents)
        link = img.find_parent("a")
        links_home = bool(link and link.get("href") and (
            urlparse(urljoin(base, link["href"])).path in ("", "/")
            and urlparse(urljoin(base, link["href"])).netloc == home))
        in_header = img.find_parent(["header", "nav"]) is not None or "header" in parent_txt
        logo_signal = "logo" in own or "logo" in parent_txt or "brand" in parent_txt
        alt_is_name = client_name and name_match(client_name, img.get("alt", "") or "") >= 0.99

        if _SOCIAL.search(own):
            continue
        if not (logo_signal or (links_home and (in_header or alt_is_name))):
            continue

        score = 0.75 if logo_signal else 0.65
        if in_header:
            score += 0.1
        if links_home:
            score += 0.1
        if alt_is_name:
            score += 0.05
        if _NOT_LOGO.search(own):
            score -= 0.45
        ctx = f"img: {own[:90]}"
        if (in_header or links_home) and logo_signal and not header_logo_found:
            header_logo_found = True
            score = max(score, 1.0)
            ctx = "LOGO DEL ENCABEZADO DE LA WEB OFICIAL | " + ctx
        add(src, score, ctx)

    # 2) JSON-LD schema.org "logo" (a veces desactualizado o con ruta rota)
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            blob = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for m in re.findall(r'"logo"\s*:\s*(?:\{[^}]*?"url"\s*:\s*)?"([^"]+)"', json.dumps(blob)):
            add(m, 0.9, "logo declarado en JSON-LD (schema.org) de la web oficial")

    # 4) Iconos grandes y og:image
    for link in soup.find_all("link", rel=True):
        rel = " ".join(link["rel"]).lower()
        if "apple-touch-icon" in rel:
            add(link.get("href"), 0.5, "apple-touch-icon (ícono) de la web oficial")
        elif "icon" in rel:
            add(link.get("href"), 0.35, "favicon de la web oficial")
    og = soup.find("meta", property="og:image")
    if og:
        add(og.get("content"), 0.45, "og:image (imagen para redes) de la web oficial")

    return sorted(cands.values(), key=lambda c: -c["score"])
