"""Logo desde Wikidata (propiedad P154). Ideal para empresas grandes."""

from __future__ import annotations

from ..utils import http_get, name_match

_API = "https://www.wikidata.org/w/api.php"


def wikidata_logo_candidates(client_name: str) -> list[dict]:
    r = http_get(_API, params={"action": "wbsearchentities", "search": client_name,
                               "language": "es", "format": "json", "limit": 5, "type": "item"})
    if r is None:
        return []
    cands = []
    for ent in r.json().get("search", []):
        if name_match(client_name, ent.get("label", "")) < 0.99:
            continue
        e = http_get(_API, params={"action": "wbgetclaims", "entity": ent["id"],
                                   "property": "P154", "format": "json"})
        if e is None:
            continue
        for claim in e.json().get("claims", {}).get("P154", []):
            fname = claim["mainsnak"].get("datavalue", {}).get("value")
            if fname:
                url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
                       + fname.replace(" ", "_") + "?width=600")
                cands.append({"url": url, "source": "wikidata", "score": 0.95,
                              "context": f"{ent.get('label')} - {ent.get('description', '')}"})
    return cands
