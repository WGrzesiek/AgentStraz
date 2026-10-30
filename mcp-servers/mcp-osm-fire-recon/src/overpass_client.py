"""
Klient Overpass API dla OpenStreetMap.
Obsługuje zapytania przestrzenne z rotacją serwerów lustrzanych (mirroring) i obsługą timeoutów.
"""

import httpx
from typing import Dict, Any, List, Optional
try:
    from .water_supply import parse_hydrant_data, parse_water_source
except (ImportError, ValueError):
    from water_supply import parse_hydrant_data, parse_water_source

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


async def query_overpass(query_ql: str, timeout_sec: float = 12.0) -> Optional[Dict[str, Any]]:
    """
    Wykonuje zapytanie Overpass QL do dostępnego serwera z listy mirrorów.
    """
    headers = {
        "User-Agent": "MCP-OSM-FireRecon/1.0 (Straz Pozarna Recon)",
        "Accept": "application/json",
    }

    for server_url in OVERPASS_SERVERS:
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.post(
                    server_url,
                    data={"data": query_ql},
                    headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            continue

    return None


async def get_nearest_hydrants(lat: float, lon: float, radius_m: int = 500, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Wyszukuje hydranty w podanym promieniu od miejsca akcji.
    """
    ql = f"""
    [out:json][timeout:10];
    (
      node["emergency"="fire_hydrant"](around:{radius_m},{lat},{lon});
    );
    out body {max_results * 2};
    """
    data = await query_overpass(ql)
    if not data or "elements" not in data:
        return []

    elements = data.get("elements", [])
    parsed = [parse_hydrant_data(el, lat, lon) for el in elements]
    parsed.sort(key=lambda x: x["distance_m"])

    return parsed[:max_results]


async def get_water_sources(lat: float, lon: float, radius_m: int = 1500, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Wyszukuje rzeki, stawy, jeziora, zbiorniki ppoż. i punkty czerpania wody.
    """
    ql = f"""
    [out:json][timeout:12];
    (
      node["natural"="water"](around:{radius_m},{lat},{lon});
      way["natural"="water"](around:{radius_m},{lat},{lon});
      relation["natural"="water"](around:{radius_m},{lat},{lon});
      way["waterway"~"^(river|stream|canal|ditch)$"](around:{radius_m},{lat},{lon});
      node["emergency"~"^(suction_point|fire_water_pond|water_point)$"](around:{radius_m},{lat},{lon});
      way["emergency"="fire_water_pond"](around:{radius_m},{lat},{lon});
    );
    out center 20;
    """
    data = await query_overpass(ql)
    if not data or "elements" not in data:
        return []

    elements = data.get("elements", [])
    parsed = [parse_water_source(el, lat, lon) for el in elements]
    # Dedykowane punkty ppoż. i rzeki traktujemy priorytetowo
    parsed.sort(key=lambda x: (not x["is_fire_designated"], x["distance_m"]))

    # Deduplikacja po nazwie i odległości
    unique_sources = []
    seen = set()
    for s in parsed:
        key = (s["name"], int(s["distance_m"] / 100))
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)
            if len(unique_sources) >= max_results:
                break

    return unique_sources


async def get_access_restrictions(lat: float, lon: float, radius_m: int = 400) -> List[Dict[str, Any]]:
    """
    Wyszukuje oznaczone dojazdy pożarowe oraz drogi nieutwardzone/gruntowe
    stwarzające ryzyko dla ciężkich samochodów gaśniczych GCBA.
    """
    ql = f"""
    [out:json][timeout:10];
    (
      way["highway"]["surface"~"^(ground|dirt|sand|unpaved|mud)$"](around:{radius_m},{lat},{lon});
      way["highway"]["fire_lane"="yes"](around:{radius_m},{lat},{lon});
      way["highway"]["description"~"dojazd pożarowy|pożarow",i](around:{radius_m},{lat},{lon});
    );
    out center 15;
    """
    data = await query_overpass(ql)
    if not data or "elements" not in data:
        return []

    results = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("description") or "Droga bez nazwy"
        surface = tags.get("surface", "nieokreślona")
        is_fire_lane = tags.get("fire_lane") == "yes" or "pożarow" in name.lower() or "dojazd" in name.lower()

        results.append({
            "name": name,
            "surface": surface,
            "is_fire_lane": is_fire_lane,
            "tactical_note": "Oznaczony dojazd pożarowy" if is_fire_lane else f"Nawierzchnia gruntowa ({surface}) - ostrożnie przy wjeździe ciężkich GCBA",
        })

    return results
