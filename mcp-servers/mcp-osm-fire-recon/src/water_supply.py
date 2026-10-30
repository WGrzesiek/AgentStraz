"""
Moduł obliczeń taktycznych zaopatrzenia wodnego dla Straży Pożarnej (OSP/PSP).
Przelicza odległości, linie wężowe W-75, typy hydrantów oraz punkty czerpania wody.
"""

import math
from typing import Dict, Any, List, Optional


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Oblicza odległość w linii prostej (w metrach) pomiędzy dwoma punktami GPS.
    """
    R = 6371000.0  # Promień Ziemi w metrach
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 1)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """
    Wyznacza kierunek geograficzny (azymut i skrót róży wiatrów) z punktu 1 do punktu 2.
    np. 'północny wschód (NE, 45°)'
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing_deg = (math.degrees(math.atan2(y, x)) + 360) % 360

    directions = [
        ("N", "północ"),
        ("NE", "północny wschód"),
        ("E", "wschód"),
        ("SE", "południowy wschód"),
        ("S", "południe"),
        ("SW", "południowy zachód"),
        ("W", "zachód"),
        ("NW", "północny zachód"),
    ]
    idx = int((bearing_deg + 22.5) / 45) % 8
    code, name = directions[idx]

    return f"{name} ({code}, {int(bearing_deg)}°)"


def calculate_w75_hoses(distance_m: float, terrain_reserve_pct: float = 15.0) -> Dict[str, Any]:
    """
    Przelicza odległość w metrach na standardowe odcinki węży tłocznych W-75 (20 m na odcinek).
    Uwzględnia rezerwę terenową (domyślnie +15% na łuki, omijanie przeszkód i ukształtowanie drogi).
    """
    effective_distance = distance_m * (1.0 + terrain_reserve_pct / 100.0)
    hose_length = 20.0
    sections = math.ceil(effective_distance / hose_length)

    return {
        "distance_direct_m": distance_m,
        "estimated_line_m": round(effective_distance, 1),
        "w75_sections_count": sections,
        "description": f"ok. {sections} odcinków W-75 (rozwinięcie ~{int(effective_distance)} m z rezerwą terenową)",
    }


def parse_hydrant_data(osm_element: Dict[str, Any], origin_lat: float, origin_lon: float) -> Dict[str, Any]:
    """
    Ekstrahuje i standaryzuje dane o hydrancie pod kątem wymogów bojowych KDR.
    """
    tags = osm_element.get("tags", {})
    lat = osm_element.get("lat") or osm_element.get("center", {}).get("lat")
    lon = osm_element.get("lon") or osm_element.get("center", {}).get("lon")

    dist = haversine_distance(origin_lat, origin_lon, lat, lon)
    direction = calculate_bearing(origin_lat, origin_lon, lat, lon)
    hoses = calculate_w75_hoses(dist)

    raw_type = tags.get("fire_hydrant:type", "").lower()
    raw_diameter = tags.get("fire_hydrant:diameter", "") or tags.get("diameter", "")

    # Normalizacja typu hydrantu
    if "pillar" in raw_type or "nadziemny" in raw_type or "aboveground" in raw_type:
        hydrant_type = "nadziemny"
        equipment_required = "Zwykły klucz hydrantowy 7E"
        is_underground = False
    elif "underground" in raw_type or "podziemny" in raw_type:
        hydrant_type = "podziemny"
        equipment_required = "WYMAGANY STOJAK HYDRANTOWY 2x75 i KLUCZ PODZIEMNY (T)"
        is_underground = True
    elif "wall" in raw_type or "scienny" in raw_type:
        hydrant_type = "ścienny"
        equipment_required = "Klucz do zaworu ściennego"
        is_underground = False
    else:
        hydrant_type = "typ nieokreślony w OSM (najczęściej nadziemny lub podziemny)"
        equipment_required = "Zabrać zapobiegawczo stojak i klucz podziemny"
        is_underground = None

    # Normalizacja średnicy
    if raw_diameter:
        diameter = f"DN{raw_diameter.replace('DN', '').replace('dn', '').strip()}"
    else:
        diameter = "DN nieokreślone (standardowo DN80)"

    street = tags.get("addr:street") or tags.get("name") or tags.get("description", "")
    operator = tags.get("operator", "")
    pressure = tags.get("fire_hydrant:pressure", "")

    return {
        "id": osm_element.get("id"),
        "lat": lat,
        "lon": lon,
        "distance_m": dist,
        "direction": direction,
        "type": hydrant_type,
        "is_underground": is_underground,
        "diameter": diameter,
        "pressure": pressure,
        "equipment_required": equipment_required,
        "w75_sections": hoses["w75_sections_count"],
        "line_estimate": hoses["description"],
        "location_hint": street,
        "operator": operator,
    }


def parse_water_source(osm_element: Dict[str, Any], origin_lat: float, origin_lon: float) -> Dict[str, Any]:
    """
    Ekstrahuje dane o otwartym punkcie czerpania wody (staw, rzeka, zbiornik ppoż).
    """
    tags = osm_element.get("tags", {})
    lat = osm_element.get("lat") or osm_element.get("center", {}).get("lat")
    lon = osm_element.get("lon") or osm_element.get("center", {}).get("lon")

    dist = haversine_distance(origin_lat, origin_lon, lat, lon)
    direction = calculate_bearing(origin_lat, origin_lon, lat, lon)

    name = tags.get("name") or tags.get("description") or "Nienazwany zbiornik/ciek"
    water_type = tags.get("natural") or tags.get("waterway") or tags.get("water") or "woda"

    # Rekomendacja sprzętowa do zassania wody
    if "river" in water_type or "rzeka" in name.lower() or "jezioro" in name.lower():
        recommended_gear = "Motopompa pożarnicza (M16/8, Tohatsu) z linią ssawną W-110, dostęp z brzegu"
    elif "stream" in water_type or "ditch" in water_type or "rów" in name.lower() or "strumień" in name.lower():
        recommended_gear = "Pompa pływająca (np. Niagara) lub motopompa szlamowa (płytki ciek)"
    elif "pond" in water_type or "staw" in name.lower() or "fire_water_pond" in str(tags):
        recommended_gear = "Pompa pływająca Niagara / motopompa (sprawdzić zamulenie dna)"
    else:
        recommended_gear = "Pompa pływająca lub motopompa pożarnicza"

    is_fire_specific = (
        tags.get("emergency") in ["suction_point", "fire_water_pond", "water_point"] or
        tags.get("fire_water") == "yes"
    )

    return {
        "id": osm_element.get("id"),
        "name": name,
        "type": water_type,
        "is_fire_designated": is_fire_specific,
        "distance_m": dist,
        "direction": direction,
        "lat": lat,
        "lon": lon,
        "recommended_gear": recommended_gear,
    }
