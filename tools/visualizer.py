#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentStraz - Wizualizator Karty Rozpoznania Bojowego KDR w formacie HTML
Generuje interaktywny, taktyczny pulpit HTML dla jednostek OSP / PSP.
"""

import os
import sys
import json
import re
import math
import copy
from html import escape
import argparse
from typing import Dict, Any, Optional

# Umożliwia również uruchomienie: python3 tools/visualizer.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills.water_supply_calc.building import (
    calculate_building_water, building_water_lines, SOURCE_URL, PSP_SOURCE_URL,
)
from tools.report_panels import water_panel, combined_plan

# Zapewnienie kodowania UTF-8 na Windows w konsoli
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_DEMO_DATA: Dict[str, Any] = {
    "is_demo": True,
    "incident_info": {
        "title": "Pożar budynku mieszkalnego jednorodzinnego",
        "call_code": "MZ-POZAR-BUD_MIESZK",
        "dispatch_time": "14:22",
        "address": "Nowa Wieś, ul. Sosnowa 14",
        "city": "Nowa Wieś",
        "street": "ul. Sosnowa 14",
        "municipality": "gm. Halinów, pow. miński",
        "lat": 52.23190,
        "lon": 21.00670,
        "parcel_id": "145/2",
        "cadastral_district": "0012 Dębe Wielkie"
    },
    "weather": {
        "station_name": "Stacja IMGW Mińsk Mazowiecki / Warszawa",
        "station_distance_km": 4.2,
        "wind_direction_text": "Północno-zachodni",
        "wind_direction_abbr": "NW",
        "wind_deg": 315,
        "wind_speed_kmh": 18,
        "wind_speed_ms": 5.0,
        "wind_gusts_kmh": 36,
        "temperature_c": 19.5,
        "humidity_pct": 42,
        "smoke_sector": "SE (Południowy Wschód, ~135°)",
        "smoke_threat_objects": [
            "ul. Sosnowa 16 (posesja sąsiednia, zabudowa drewniana, 25m)",
            "ul. Sosnowa 18 (stodoła murowana, 60m)",
            "Młodnik sosnowy i las prywatny w sektorze zawietrznym (120m)"
        ]
    },
    "water_supply": {
        "hydrants": [
            {
                "id": "H1",
                "type": "nadziemny",
                "diameter": "DN80",
                "distance_m": 95,
                "estimated_w75_hoses": 5,
                "requires_standpipe_and_key": False,
                "location_desc": "ul. Sosnowa 8 (pobocze drogi, widoczny)",
                "status": "sprawny",
                "bearing_deg": 275
            },
            {
                "id": "H2",
                "type": "podziemny",
                "diameter": "DN100",
                "distance_m": 210,
                "estimated_w75_hoses": 11,
                "requires_standpipe_and_key": True,
                "location_desc": "Skrzyżowanie ul. Sosnowa i Leśna",
                "status": "wymaga stojaka",
                "bearing_deg": 40
            }
        ],
        "open_water_intakes": [
            {
                "id": "W1",
                "name": "Rzeka Mienia / Ciek Czarna",
                "type": "Ciek naturalny",
                "distance_m": 420,
                "direction": "Wschód (E)",
                "bearing_deg": 95,
                "suction_method": "Motopompa M16/8, pompa pływająca Niagara",
                "access_road": "Dojazd utwardzony od ul. Młyńskiej, stroma skarpa (2.0 m)"
            }
        ]
    },
    "utilities_and_hazards": {
        "gas": {
            "detected": True,
            "pipeline_type": "Gazociąg średniego ciśnienia (ś/c) PE DN63",
            "location": "W pasie drogowym ul. Sosnowa",
            "valve_location": "Zasuwa przyłącza i skrzynka w linii ogrodzenia (żółty słupek)",
            "risk_level": "Wysokie (odciąć zasilanie gazowe na przyłączu!)"
        },
        "electricity": {
            "lines": "Linia napowietrzna nN (niski poziom) wzdłuż drogi dojazdowej",
            "substation_trafo": "Trafo słupowe 15/0.4 kV w odległości 130m na północ (nr ST-442)",
            "cautions": "Zakaz podawania zwartego prądu gaśniczego do czasu wyłączenia zasilania (sprawdzić złącze ZK)",
            "risk_level": "Średnie"
        },
        "access_roads": {
            "road_type": "Droga gminna asfaltowa, szerokość 4.5 m",
            "gcba_access": "Wjazd dla ciężkich samochodów gaśniczych GCBA bez utrudnień",
            "bottlenecks": "Brama posesji: prześwit 3.4 m, rowek odwadniający nieutwardzony po lewej stronie"
        },
        "additional_hazards": [
            "Butle propan-butan (11 kg) w przyległym garażu blaszaku",
            "Instalacja PV 7.5 kWp na dachu (napięcie stałe DC)"
        ]
    }
}



def empty_recon_data():
    """Braki danych nigdy nie są uzupełniane scenariuszem demonstracyjnym."""
    return {
        "incident_info": {}, "weather": {},
        "water_supply": {"hydrants": [], "open_water_intakes": []},
        "utilities_and_hazards": {"gas": {}, "electricity": {}, "access_roads": {},
                                  "additional_hazards": []},
    }


def _escape_data(value):
    if isinstance(value, str):
        return escape(value, quote=True)
    if isinstance(value, dict):
        return {key: _escape_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_escape_data(item) for item in value]
    return value

def parse_text_recon(text: str) -> Dict[str, Any]:
    """
    Parsuje meldunek tekstowy / Markdown (zgodny z AGENTS.md) do ustrukturyzowanego słownika.
    """
    data = empty_recon_data()
    data["is_demo"] = "DEMO — DANE FIKCYJNE" in text
    text = re.sub(r"\*\*", "", text)

    # 1. Adres
    m = re.search(r'Adres:\s*([^\n]+)', text, re.IGNORECASE)
    if m:
        addr = m.group(1).strip()
        data["incident_info"]["address"] = addr
        parts = [p.strip() for p in addr.split(',')]
        if len(parts) >= 1:
            data["incident_info"]["city"] = parts[0]
        if len(parts) >= 2:
            data["incident_info"]["street"] = parts[1]

    # 2. Koordynaty i działka
    m_coords = re.search(r'(?:Koordynaty|Współrzędne|GPS):\s*([0-9]+\.[0-9]+)[,\s]+([0-9]+\.[0-9]+)', text, re.IGNORECASE)
    if m_coords:
        data["incident_info"]["lat"] = float(m_coords.group(1))
        data["incident_info"]["lon"] = float(m_coords.group(2))

    m_parcel = re.search(r'Działka(?: nr)?:\s*([^,\n|]+)(?:,\s*obręb\s*([^|\n]+))?', text, re.IGNORECASE)
    if m_parcel:
        data["incident_info"]["parcel_id"] = m_parcel.group(1).strip()
        if m_parcel.group(2):
            data["incident_info"]["cadastral_district"] = m_parcel.group(2).strip()

    # 3. Warunki meteo
    m_station = re.search(r'Stacja:\s*([^,\)]+)(?:,\s*([0-9\.]+)\s*km)?', text, re.IGNORECASE)
    if m_station:
        data["weather"]["station_name"] = m_station.group(1).strip()
        if m_station.group(2):
            data["weather"]["station_distance_km"] = float(m_station.group(2))

    m_wind = re.search(r'Wiatr:\s*([^,\(]+)\s*\(([^,\)]+),\s*([0-9]+)°?\),\s*([0-9]+)\s*km/h(?:\s*\(w porywach do\s*([0-9]+)\s*km/h\))?', text, re.IGNORECASE)
    if m_wind:
        data["weather"]["wind_direction_text"] = m_wind.group(1).strip()
        data["weather"]["wind_direction_abbr"] = m_wind.group(2).strip()
        data["weather"]["wind_deg"] = int(m_wind.group(3))
        data["weather"]["wind_speed_kmh"] = int(m_wind.group(4))
        data["weather"]["wind_speed_ms"] = round(int(m_wind.group(4)) / 3.6, 1)
        if m_wind.group(5):
            data["weather"]["wind_gusts_kmh"] = int(m_wind.group(5))

    m_smoke = re.search(r'(?:Zagrożenie zadymieniem|Wektor zadymienia):\s*(?:Posesje w sektorze\s*)?([^\n]+)', text, re.IGNORECASE)
    if m_smoke:
        data["weather"]["smoke_sector"] = m_smoke.group(1).strip()

    # 4. Hydranty
    hydrant_matches = re.findall(
        r'(\d+)\.\s*Hydrant\s+(nadziemny|podziemny)\s+(DN\d+):\s*(\d+)\s*m[^\n]*\n\s*->\s*Szacowane rozwinięcie:\s*~?(\d+)\s*odcink[^\n]*(\[UWAGA:[^\]]+\])?',
        text, re.IGNORECASE
    )
    if hydrant_matches:
        parsed_hydrants = []
        for idx, (num, h_type, dn, dist, hoses, note) in enumerate(hydrant_matches):
            is_underground = "podziemny" in h_type.lower() or (note and "stojak" in note.lower())
            parsed_hydrants.append({
                "id": f"H{num}",
                "type": h_type.lower(),
                "diameter": dn.upper(),
                "distance_m": int(dist),
                "estimated_w75_hoses": int(hoses),
                "requires_standpipe_and_key": is_underground,
                "location_desc": f"Hydrant {h_type} {dn} w odległości {dist} m",
                "status": "sprawność niepotwierdzona",
                "bearing_deg": None
            })
        data["water_supply"]["hydrants"] = parsed_hydrants

    # 5. Cieki wodne
    m_water = re.search(r'Otwarty\s+(?:punkt czerpania wody|ciek wodny):\s*(.+?)\s*w odl\.\s*(\d+)\s*m\s*\n\s*->\s*Możliwość zassania:\s*([^\n]+?)(?:,\s*dojazd:\s*([^\n]+))?$', text, re.IGNORECASE | re.MULTILINE)
    if m_water:
        data["water_supply"]["open_water_intakes"] = [{
            "id": "W1",
            "name": m_water.group(1).strip(),
            "type": "Ciek naturalny / Zbiornik",
            "distance_m": int(m_water.group(2)),
            "direction": "Sektor boczny",
            "bearing_deg": None,
            "suction_method": m_water.group(3).strip(),
            "access_road": m_water.group(4).strip() if m_water.group(4) else "Brak danych"
        }]

    # 6. Zagrożenia i media
    m_gas = re.search(r'•\s*GAZ:\s*([^\n]+)', text, re.IGNORECASE)
    if m_gas:
        data["utilities_and_hazards"]["gas"]["pipeline_type"] = m_gas.group(1).strip()

    m_power = re.search(r'•\s*ENERGETYKA:\s*([^\n]+)', text, re.IGNORECASE)
    if m_power:
        data["utilities_and_hazards"]["electricity"]["lines"] = m_power.group(1).strip()

    m_road = re.search(r'•\s*DOJAZD(?:\s*POŻAROWY)?:\s*([^\n]+)', text, re.IGNORECASE)
    if m_road:
        data["utilities_and_hazards"]["access_roads"]["road_type"] = m_road.group(1).strip()

    return data


def generate_tactical_svg(data: Dict[str, Any]) -> str:
    """
    Generuje interaktywny schemat wektorowy SVG (Radar / Plan Sytuacyjny 500m).
    100% odporny na restrykcje CSP i działający w trybie offline.
    """
    cx, cy = 250, 250
    max_radius_m = 500
    scale = 200.0 / max_radius_m  # 200px = 500m, czyli 0.4 px/m

    wind_deg = data.get("weather", {}).get("wind_deg")
    if wind_deg is None or data.get("weather", {}).get("wind_speed_kmh", 0) == 0:
        return '<p>Brak danych o kierunku przemieszczania dymu. Schemat niedostępny.</p>' 
    # Wiatr wieje Z kąta wind_deg. Zatem dym przemieszcza się DO kąta (wind_deg + 180) % 360
    downwind_deg = (wind_deg + 180) % 360
    smoke_angle_rad = math.radians(downwind_deg)
    smoke_cone_spread = data.get("weather", {}).get("hazard_cone_span_deg", 60) / 2 #  # szerokość połówkowa stożka w stopniach
    left_angle_rad = math.radians(downwind_deg - smoke_cone_spread)
    right_angle_rad = math.radians(downwind_deg + smoke_cone_spread)

    # Obliczenie wierzchołków stożka zadymienia na 500m
    cone_dist_px = 220
    x_cone_l = cx + cone_dist_px * math.sin(left_angle_rad)
    y_cone_l = cy - cone_dist_px * math.cos(left_angle_rad)
    x_cone_r = cx + cone_dist_px * math.sin(right_angle_rad)
    y_cone_r = cy - cone_dist_px * math.cos(right_angle_rad)

    # Elementy hydrologiczne i hydranty
    hydrants_svg = []
    for h in data.get("water_supply", {}).get("hydrants", []):
        if h.get("bearing_deg") is None or h.get("distance_m") is None or h["distance_m"] > 500:
            continue
        dist_m = h["distance_m"]
        dist_px = dist_m * scale
        b_deg = h.get("bearing_deg", 270)
        b_rad = math.radians(b_deg)
        hx = cx + dist_px * math.sin(b_rad)
        hy = cy - dist_px * math.cos(b_rad)

        is_underground = h.get("requires_standpipe_and_key", False)
        marker_color = "#F59E0B" if is_underground else "#0EA5E9"
        border_color = "#D97706" if is_underground else "#0284C7"
        icon_text = "H" if not is_underground else "HP"
        h_id = h.get("id", "H")
        dn = h.get("diameter", "DN80")
        hoses = h.get("estimated_w75_hoses", 5)

        hydrants_svg.append(f"""
        <!-- Hydrant {h_id} -->
        <g class="cursor-pointer group" >
            <!-- Linia węża do obiektu -->
            <line x1="{cx}" y1="{cy}" x2="{hx}" y2="{hy}" stroke="{marker_color}" stroke-dasharray="4,4" stroke-width="2" opacity="0.6"/>
            <!-- Puls i marker -->
            <circle cx="{hx}" cy="{hy}" r="15" fill="{marker_color}" fill-opacity="0.25" class="animate-pulse" />
            <circle cx="{hx}" cy="{hy}" r="10" fill="{marker_color}" stroke="{border_color}" stroke-width="2" />
            <text x="{hx}" y="{hy + 3.5}" text-anchor="middle" font-size="9" font-weight="bold" fill="#FFFFFF">{icon_text}</text>
            <!-- Etykieta -->
            <rect x="{hx - 36}" y="{hy + 14}" width="72" height="18" rx="4" fill="#0F172A" fill-opacity="0.85" stroke="{marker_color}" stroke-width="1"/>
            <text x="{hx}" y="{hy + 26}" text-anchor="middle" font-size="9" font-weight="600" fill="#E2E8F0">{h_id}: {dist_m}m ({hoses}xW)</text>
        </g>
        """)

    # Punkt czerpania wody (ciek / rzeka)
    water_intakes_svg = []
    for w in data.get("water_supply", {}).get("open_water_intakes", []):
        if w.get("bearing_deg") is None or w.get("distance_m") is None or w["distance_m"] > 500:
            continue
        dist_m = w["distance_m"]
        dist_px = dist_m * scale
        b_deg = w.get("bearing_deg", 95)
        b_rad = math.radians(b_deg)
        wx = cx + dist_px * math.sin(b_rad)
        wy = cy - dist_px * math.cos(b_rad)
        w_id = w.get("id", "W1")

        water_intakes_svg.append(f"""
        <!-- Ciek wodny {w_id} -->
        <g class="cursor-pointer group" >
            <line x1="{cx}" y1="{cy}" x2="{wx}" y2="{wy}" stroke="#38BDF8" stroke-dasharray="2,4" stroke-width="1.5" opacity="0.4"/>
            <circle cx="{wx}" cy="{wy}" r="12" fill="#0284C7" stroke="#38BDF8" stroke-width="2" />
            <text x="{wx}" y="{wy + 4}" text-anchor="middle" font-size="10" font-weight="bold" fill="#FFFFFF">💧</text>
            <rect x="{wx - 45}" y="{wy + 15}" width="90" height="18" rx="4" fill="#0F172A" fill-opacity="0.85" stroke="#38BDF8" stroke-width="1"/>
            <text x="{wx}" y="{wy + 27}" text-anchor="middle" font-size="9" font-weight="600" fill="#7DD3FC">Ciek: {dist_m}m (M16/8)</text>
        </g>
        """)

    # Brak geometrii sieci: nie rysujemy fikcyjnego gazociągu ani trafo.
    # SVG Defs, pierścienie, siatka taktyczna
    return f"""
    <svg viewBox="0 0 500 500" class="w-full h-full select-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <!-- Gradient stożka dymu -->
            <radialGradient id="smokeGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#475569" stop-opacity="0.75" />
                <stop offset="60%" stop-color="#334155" stop-opacity="0.45" />
                <stop offset="100%" stop-color="#1E293B" stop-opacity="0.0" />
            </radialGradient>
            <!-- Wzór siatki militarnej/taktycznej -->
            <pattern id="tacticalGrid" width="25" height="25" patternUnits="userSpaceOnUse">
                <path d="M 25 0 L 0 0 0 25" fill="none" stroke="currentColor" stroke-opacity="0.07" stroke-width="1"/>
            </pattern>
        </defs>

        <!-- Tło siatki -->
        <rect width="500" height="500" fill="url(#tacticalGrid)" class="text-slate-400" />

        <!-- Pierścienie odległości (100m, 200m, 300m, 500m) -->
        <circle cx="{cx}" cy="{cy}" r="{100 * scale}" fill="none" stroke="#64748B" stroke-dasharray="3,3" stroke-width="1" opacity="0.35" />
        <text x="{cx + 100 * scale + 4}" y="{cy - 4}" font-size="8" fill="#94A3B8" opacity="0.8">100m</text>

        <circle cx="{cx}" cy="{cy}" r="{200 * scale}" fill="none" stroke="#64748B" stroke-dasharray="3,3" stroke-width="1" opacity="0.35" />
        <text x="{cx + 200 * scale + 4}" y="{cy - 4}" font-size="8" fill="#94A3B8" opacity="0.8">200m</text>

        <circle cx="{cx}" cy="{cy}" r="{300 * scale}" fill="none" stroke="#64748B" stroke-dasharray="3,3" stroke-width="1" opacity="0.3" />
        <text x="{cx + 300 * scale + 4}" y="{cy - 4}" font-size="8" fill="#94A3B8" opacity="0.7">300m</text>

        <circle cx="{cx}" cy="{cy}" r="{500 * scale}" fill="none" stroke="#EF4444" stroke-dasharray="4,4" stroke-width="1.5" opacity="0.45" />
        <text x="{cx + 500 * scale - 28}" y="{cy - 6}" font-size="9" font-weight="bold" fill="#F87171" opacity="0.9">ZASIĘG 500m</text>

        <!-- Osie krzyżowe N-S / W-E -->
        <line x1="{cx}" y1="20" x2="{cx}" y2="480" stroke="#475569" stroke-width="1" opacity="0.3"/>
        <line x1="20" y1="{cy}" x2="480" y2="{cy}" stroke="#475569" stroke-width="1" opacity="0.3"/>

        <!-- Oznaczenia stron świata -->
        <text x="{cx}" y="16" text-anchor="middle" font-size="12" font-weight="bold" fill="#EF4444">N</text>
        <text x="{cx}" y="495" text-anchor="middle" font-size="11" font-weight="bold" fill="#64748B">S</text>
        <text x="492" y="{cy + 4}" text-anchor="end" font-size="11" font-weight="bold" fill="#64748B">E</text>
        <text x="8" y="{cy + 4}" text-anchor="start" font-size="11" font-weight="bold" fill="#64748B">W</text>

        <!-- STOŻEK DYMU I ROZPRZESTRZENIANIA ZAGROŻENIA -->
        <path d="M {cx} {cy} L {x_cone_l} {y_cone_l} A {cone_dist_px} {cone_dist_px} 0 0 1 {x_cone_r} {y_cone_r} Z"
              fill="url(#smokeGradient)" stroke="#64748B" stroke-width="1" stroke-dasharray="3,3" opacity="0.8" />
        
        <!-- Wektor kierunku wiatru i znoszenia dymu -->
        <g>
            <line x1="{cx}" y1="{cy}" x2="{cx + 170 * math.sin(smoke_angle_rad)}" y2="{cy - 170 * math.cos(smoke_angle_rad)}"
                  stroke="#F87171" stroke-width="2.5" stroke-dasharray="5,3" opacity="0.9"/>
            <polygon points="{cx + 185 * math.sin(smoke_angle_rad)},{cy - 185 * math.cos(smoke_angle_rad)} 
                             {cx + 168 * math.sin(smoke_angle_rad) - 6 * math.cos(smoke_angle_rad)},{cy - 168 * math.cos(smoke_angle_rad) - 6 * math.sin(smoke_angle_rad)} 
                             {cx + 168 * math.sin(smoke_angle_rad) + 6 * math.cos(smoke_angle_rad)},{cy - 168 * math.cos(smoke_angle_rad) + 6 * math.sin(smoke_angle_rad)}" 
                     fill="#EF4444" />
            <text x="{cx + 110 * math.sin(smoke_angle_rad) + 12}" y="{cy - 110 * math.cos(smoke_angle_rad)}"
                  font-size="9" font-weight="bold" fill="#FCA5A5">WEKTOR DYMU ({downwind_deg}°)</text>
        </g>

        <!-- Warstwy infrastruktury -->
        {"".join(water_intakes_svg)}
        {"".join(hydrants_svg)}

        <!-- MIEJSCE ZDARZENIA (GROUND ZERO) -->
        <g class="cursor-pointer">
            <circle cx="{cx}" cy="{cy}" r="22" fill="#DC2626" fill-opacity="0.2" class="animate-ping" />
            <circle cx="{cx}" cy="{cy}" r="14" fill="#B91C1C" stroke="#F87171" stroke-width="2" />
            <text x="{cx}" y="{cy + 4.5}" text-anchor="middle" font-size="11">🔥</text>
            <rect x="{cx - 50}" y="{cy - 30}" width="100" height="17" rx="3" fill="#991B1B" stroke="#FECACA" stroke-width="1"/>
            <text x="{cx}" y="{cy - 18}" text-anchor="middle" font-size="8.5" font-weight="bold" fill="#FFFFFF">CEL: {data.get('incident_info', {}).get('street', 'OBIEKT')[:16].upper()}</text>
        </g>
    </svg>
    """


def generate_radio_briefing(data: Dict[str, Any]) -> str:
    """
    Formułuje gotowy tekst meldunku radiowego KDR do SKKP lub załogi wozu.
    """
    if data.get("radio_brief"):
        return data["radio_brief"]
    info = data.get("incident_info", {})
    weather = data.get("weather", {})
    water = data.get("water_supply", {}).get("hydrants", [])
    return (
        f"Projekt meldunku do potwierdzenia przez KDR. Adres: {info.get('address', 'brak danych')}. "
        f"Wiatr: {weather.get('wind_direction_abbr', 'brak danych')}, "
        f"{weather.get('wind_speed_kmh', 'brak danych')} km/h. "
        f"Punkty hydrantowe w danych: {len(water)}; sprawność wymaga potwierdzenia. "
        f"Gaz: {data.get('utilities_and_hazards', {}).get('gas', {}).get('pipeline_type', 'brak danych')}."
    )


def render_html(data: Dict[str, Any], standalone: bool = True) -> str:
    """
    Generuje kompletny dokument HTML (lub widżet embed) z pulpitem taktycznym.
    """
    # Liczymy z wejścia strukturalnego, nigdy z tekstu ani dostarczonego wyniku.
    calculation = calculate_building_water(data.get("building"), data.get("suppression"))
    building_water_html = water_panel(calculation)
    combined_plan_html = combined_plan(data)
    source_lines = building_water_lines(calculation)
    source_details_html = '<details class="card-box p-4"><summary>Źródła i metodyka — budynek oraz kalkulacja wody</summary><ul class="text-xs space-y-2 mt-3">' + ''.join(f'<li>{escape(line)}</li>' for line in source_lines) + f'<li><a href="{SOURCE_URL}">ZPE — kalkulacja sił i środków</a> · <a href="{PSP_SOURCE_URL}">KG PSP / CNBOP — tabela 3.1</a></li></ul></details>'
    data = _escape_data(copy.deepcopy(data))
    info = data.get("incident_info", {})
    weather = data.get("weather", {})
    water = data.get("water_supply", {})
    hazards = data.get("utilities_and_hazards", {})

    lat = info.get("lat")
    lon = info.get("lon")
    address = info.get("address", "Nieznany adres")
    geocoding_note = ("Geokodowanie: OpenStreetMap contributors (ODbL)"
                      if "OSM" in info.get("geocoding_source", "") else info.get("geocoding_source", ""))
    parcel = info.get("parcel_id", "---")
    district = info.get("cadastral_district", "---")

    wind_deg = weather.get("wind_deg", "brak danych")
    wind_abbr = weather.get("wind_direction_abbr", "brak danych")
    wind_text = weather.get("wind_direction_text", "brak danych")
    wind_speed = weather.get("wind_speed_kmh", "brak danych")
    wind_gusts = weather.get("wind_gusts_kmh", "brak danych")
    smoke_sector = weather.get("smoke_sector", "brak danych")

    svg_map = generate_tactical_svg(data)
    data_notice = ("DEMO — DANE FIKCYJNE" if data.get("is_demo") else "Dane wymagają potwierdzenia w terenie")
    analysis_html = "".join(
        f"<li>{line}</li>" for line in data.get("tactical_orders", [])
    )
    radio_briefing = generate_radio_briefing(data)

    hydrants = water.get("hydrants", [])
    open_waters = water.get("open_water_intakes", [])

    hydrants_html = "" if hydrants else "<p>Brak danych o hydrantach.</p>"
    recon = water.get("hydrant_recon")
    if recon:
        hydrants_html += (f"<p>Geoportal K-GESUT • status: {recon.get('status')} • "
                          f"promień: {recon.get('radius_m')} m • "
                          f"pobrano: {recon.get('retrieved_at')}</p>"
                          f"<p>{recon.get('notice', '')}</p>")
    for index, h in enumerate(hydrants):
        is_underground = h.get("requires_standpipe_and_key", False)
        badge_color = "bg-amber-900/60 border-amber-500 text-amber-200" if is_underground else "bg-sky-900/60 border-sky-500 text-sky-200"
        warning_box = """
        <div class="mt-2 text-xs font-semibold text-amber-300 bg-amber-950/70 p-2 rounded border border-amber-600/60 flex items-center gap-1.5">
            <span>⚠️</span> <span>WYMAGANY STOJAK HYDRANTOWY I KLUCZ PODZIEMNY!</span>
        </div>
        """ if is_underground else ""
        source_info = (f"<p class='text-xs text-slate-400'>Źródło: {h.get('source')} • "
                       f"data źródła: {h.get('source_date') or 'nie podano'} • "
                       "typ, DN i sprawność do potwierdzenia</p>") if h.get('source') else ""
        distance_label = "od ogniska — w linii prostej" if h.get('distance_basis') == 'straight_line' else "od celu"
        nearest_label = "<p>Najbliższy odczytany hydrant w promieniu wyszukiwania</p>" if recon and index == 0 else ""

        hydrants_html += f"""
        <div class="p-3.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:border-slate-500 transition-all">
            {nearest_label}
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-xs font-bold border {badge_color}">
                        {h.get('id', 'H')} • {h.get('type', '').upper()}
                    </span>
                    <span class="text-sm font-semibold text-slate-100">{h.get('diameter', 'DN nieznane')}</span>
                </div>
                <div class="text-right">
                    <span class="text-lg font-black text-amber-400">{h.get('distance_m')} m</span>
                    <span class="text-xs text-slate-400 block">{distance_label}</span>
                </div>
            </div>
            <div class="mt-2.5 flex items-center justify-between text-xs text-slate-300 border-t border-slate-700/60 pt-2">
                <span class="text-slate-400">{h.get('location_desc', '')}</span>
                <span class="font-bold text-sky-400 bg-sky-950/80 px-2 py-1 rounded border border-sky-800/50">
                    🚒 ~{h.get('estimated_w75_hoses')} odcinków W-75
                </span>
            </div>
            {warning_box}
            {source_info}
        </div>
        """

    open_water_html = "" if open_waters else "<p>Brak danych o punktach czerpania wody.</p>"
    for w in open_waters:
        open_water_html += f"""
        <div class="p-3.5 rounded-lg border border-cyan-800/60 bg-cyan-950/30">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-base">🌊</span>
                    <span class="text-sm font-bold text-cyan-200">{w.get('name')}</span>
                </div>
                <span class="text-base font-bold text-cyan-400">{w.get('distance_m')} m</span>
            </div>
            <div class="mt-2 text-xs text-slate-300 space-y-1">
                <div><strong class="text-slate-400">Sprzęt ssawny:</strong> {w.get('suction_method')}</div>
                <div><strong class="text-slate-400">Dojazd i brzeg:</strong> {w.get('access_road')}</div>
            </div>
        </div>
        """

    gas_data = hazards.get("gas", {})
    elec_data = hazards.get("electricity", {})
    road_data = hazards.get("access_roads", {})
    add_hazards = hazards.get("additional_hazards", [])

    add_hazards_html = "".join([f"<li class='text-xs text-amber-200 flex items-start gap-1.5'><span class='text-amber-400 font-bold'>•</span> {h}</li>" for h in add_hazards])

    # Dynamiczne linki do map
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    geoportal_url = f"https://mapy.geoportal.gov.pl/imap/Imgp_2.html?locale=pl&gui=new&session={lon},{lat},2000"

    html_content = f"""<!DOCTYPE html>
<html lang="pl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karta Rozpoznania Bojowego KDR - {address}</title>
    <!-- Tailwind CSS (GStatic Allowlisted) -->
    <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ background: #FFFFFF !important; color: #000000 !important; }}
            .card-box {{ border: 1px solid #94A3B8 !important; background: #FFFFFF !important; color: #000000 !important; }}
        }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased p-3 sm:p-5">

    <!-- KONTENER GŁÓWNY -->
    <div class="max-w-6xl mx-auto space-y-4">

        <!-- NAGŁÓWEK OPERACYJNY -->
        <header class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-start gap-3.5">
                <div class="w-12 h-12 rounded-xl bg-red-600/20 border border-red-500/50 flex items-center justify-center text-2xl shrink-0 shadow-inner">
                    🚒
                </div>
                <div>
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="bg-red-600 text-white text-xs font-black tracking-wider px-2 py-0.5 rounded shadow">
                            {data_notice}
                        </span>
                        <span class="bg-slate-800 text-slate-300 text-xs font-semibold px-2 py-0.5 rounded border border-slate-700">
                            SWD: {info.get('call_code', 'brak danych')}
                        </span>
                        <span class="text-xs text-slate-400 font-mono">
                            Godz: {info.get('dispatch_time', 'brak danych')}
                        </span>
                    </div>
                    <h1 class="text-xl sm:text-2xl font-black text-white tracking-tight mt-1">
                        {address}
                    </h1>
                    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-0.5">
                        <span>{geocoding_note}</span>
                        <span><strong>GPS:</strong> <code class="text-amber-400 font-mono font-semibold">{lat if lat is not None else 'brak danych'}, {lon if lon is not None else 'brak danych'}</code></span>
                        <span><strong>Działka:</strong> {parcel} ({district})</span>
                    </div>
                </div>
            </div>

            <!-- PRZYCISKI SZYBKICH AKCJI -->
            <div class="flex flex-wrap items-center gap-2 no-print self-end md:self-center">
                <button onclick="copyRadioBriefing()" class="px-3 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-lg shadow transition flex items-center gap-1.5">
                    <span>📋</span> Kopiuj Meldunek
                </button>
                <a href="{geoportal_url}" target="_blank" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-lg transition flex items-center gap-1.5">
                    <span>🗺️</span> Geoportal
                </a>
                <a href="{google_maps_url}" target="_blank" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-lg transition flex items-center gap-1.5">
                    <span>📍</span> Google Maps
                </a>
                <button onclick="window.print()" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold rounded-lg transition flex items-center gap-1">
                    <span>🖨️</span> Drukuj / PDF
                </button>
            </div>
        </header>

        <!-- POWIADOMIENIE KOPIOWANIA -->
        <div id="copyToast" class="hidden no-print fixed top-5 right-5 bg-emerald-600 text-white px-4 py-2.5 rounded-lg shadow-2xl text-xs font-bold z-50 flex items-center gap-2">
            <span>✅</span> Skopiowano meldunek radiowy KDR do schowka!
        </div>

        <!-- UKŁAD DWUKOLUMNOWY -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">

            <!-- LEWA KOLUMNA: PLAN SYTUACYJNY I RADAR (7 kolumn) -->
            <div class="lg:col-span-7 space-y-4">

        
                {combined_plan_html}

                <!-- KARTA PLANU SYTUACYJNEGO -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                        <div class="flex items-center gap-2">
                            <span class="text-base">🎯</span>
                            <h2 class="font-bold text-slate-100 text-sm tracking-wide uppercase">
                                Schemat orientacyjny (500 m); tylko punkty o znanym azymucie
                            </h2>
                        </div>
                        <span class="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                            Orientacja Północ (N)
                        </span>
                    </div>

                    <!-- KONTENER SVG RADARU -->
                    <div class="aspect-square w-full max-w-[480px] mx-auto bg-slate-950 rounded-xl border border-slate-800 p-2 relative overflow-hidden shadow-inner flex items-center justify-center">
                        {svg_map}
                    </div>

                    <!-- LEGENDA TAKTYCZNA -->
                    <div class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t border-slate-800/80 text-[11px] text-slate-300">
                        <div class="flex items-center gap-1.5">
                            <span class="w-3 h-3 rounded-full bg-red-600 inline-block"></span>
                            <span>Cel / Ognisko</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <span class="w-3 h-3 rounded-full bg-sky-500 inline-block"></span>
                            <span>Hydrant nadziemny</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
                            <span>Hydrant podziemny</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <span class="w-3 h-3 rounded bg-slate-600 inline-block opacity-75"></span>
                            <span>Stożek dymu</span>
                        </div>
                    </div>
                </div>

                <!-- ZAGROŻENIA I MEDIA (GESUT) -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box">
                    <div class="flex items-center gap-2 pb-3 border-b border-slate-800 mb-3">
                        <span class="text-base">⚠️</span>
                        <h2 class="font-bold text-slate-100 text-sm tracking-wide uppercase">
                            Zagrożenia i Media (GESUT / Teren)
                        </h2>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <!-- GAZ -->
                        <div class="p-3 rounded-lg border border-amber-900/50 bg-amber-950/20">
                            <div class="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase mb-1">
                                <span>🔥</span> SIEĆ GAZOWA
                            </div>
                            <p class="text-xs text-slate-200 font-semibold">{gas_data.get('pipeline_type', 'Brak danych o sieci')}</p>
                            <p class="text-xs text-amber-300/90 mt-1">{gas_data.get('valve_location', '')}</p>
                            <span class="mt-2 inline-block text-[11px] font-bold text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-700/60">
                                {gas_data.get('risk_level', 'Uwaga!')}
                            </span>
                        </div>

                        <!-- ELEKTROENERGETYKA -->
                        <div class="p-3 rounded-lg border border-red-900/50 bg-red-950/20">
                            <div class="flex items-center gap-2 text-red-400 font-bold text-xs uppercase mb-1">
                                <span>⚡</span> ENERGETYKA I TRAFO
                            </div>
                            <p class="text-xs text-slate-200 font-semibold">{elec_data.get('substation_trafo', 'Brak danych o transformatorach')}</p>
                            <p class="text-xs text-slate-300 mt-1">{elec_data.get('lines', '')}</p>
                            <p class="text-[11px] text-red-300 font-medium mt-1">⚠️ {elec_data.get('cautions', '')}</p>
                        </div>
                    </div>

                    <!-- DOJAZD POŻAROWY -->
                    <div class="mt-3 p-3 rounded-lg border border-slate-700 bg-slate-800/60">
                        <div class="flex items-center justify-between">
                            <div class="text-xs font-bold text-slate-200 uppercase flex items-center gap-1.5">
                                <span>🚛</span> DOJAZD POŻAROWY I TONAŻ (GCBA)
                            </div>
                            <span class="text-[11px] bg-emerald-950 text-emerald-300 border border-emerald-700 px-2 py-0.5 rounded font-bold">
                                {road_data.get('gcba_access', 'PRZEJEZDNOŚĆ NIEPOTWIERDZONA')}
                            </span>
                        </div>
                        <p class="text-xs text-slate-300 mt-1.5">{road_data.get('road_type', '')}</p>
                        <p class="text-xs text-slate-400 mt-0.5"><strong class="text-slate-300">Wąskie gardła:</strong> {road_data.get('bottlenecks', 'Brak danych')}</p>
                    </div>

                    <!-- DODATKOWE ZAGROŻENIA -->
                    {f'''
                    <div class="mt-3 p-3 rounded-lg border border-amber-800/40 bg-amber-950/10">
                        <div class="text-xs font-bold text-amber-300 uppercase mb-1.5">Zidentyfikowane materiały niebezpieczne:</div>
                        <ul class="space-y-1">{add_hazards_html}</ul>
                    </div>
                    ''' if add_hazards else ''}
                </div>
            </div>

            <!-- PRAWA KOLUMNA: METEO, WODA I MELDUNEK (5 kolumn) -->
            <div class="lg:col-span-5 space-y-4">

                <!-- WARUNKI METEO I WEKTOR WIATRU -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                        <div class="flex items-center gap-2">
                            <span class="text-base">💨</span>
                            <h2 class="font-bold text-slate-100 text-sm tracking-wide uppercase">
                                Warunki Meteo — {weather.get('station_name', 'źródło nieznane')}
                            </h2>
                        </div>
                        <span class="text-xs text-slate-400">
                            {weather.get('station_distance_km')} km od celu
                        </span>
                    </div>

                    <div class="flex items-center justify-between gap-4">
                        <!-- TARCZA RÓŻY WIATRÓW -->
                        <div class="relative w-28 h-28 shrink-0 flex items-center justify-center bg-slate-950 rounded-full border border-slate-800 shadow-inner">
                            <!-- Litery kierunków -->
                            <span class="absolute top-1 text-[10px] font-bold text-red-500">N</span>
                            <span class="absolute bottom-1 text-[10px] font-bold text-slate-500">S</span>
                            <span class="absolute right-1.5 text-[10px] font-bold text-slate-500">E</span>
                            <span class="absolute left-1.5 text-[10px] font-bold text-slate-500">W</span>
                            <!-- Igła wiatrowskazu -->
                            <div class="w-1.5 h-16 bg-gradient-to-t from-slate-600 via-amber-400 to-red-500 rounded-full shadow-lg transition-transform duration-700"
                                 style="transform: rotate({wind_deg}deg);">
                            </div>
                            <div class="w-3.5 h-3.5 bg-white rounded-full border-2 border-slate-900 z-10"></div>
                        </div>

                        <!-- DANE LICZBOWE -->
                        <div class="space-y-1.5 flex-1">
                            <div>
                                <span class="text-xs text-slate-400 block">Kierunek wiatru</span>
                                <span class="text-lg font-black text-white">{wind_text}</span>
                                <span class="text-xs font-mono text-amber-400 block font-bold">({wind_abbr}, {wind_deg}°)</span>
                            </div>
                            <div class="pt-1 border-t border-slate-800 flex items-baseline justify-between">
                                <span class="text-xs text-slate-400">Prędkość:</span>
                                <span class="text-base font-bold text-slate-100">{wind_speed} km/h <span class="text-xs text-slate-400 font-normal">({weather.get('wind_speed_ms')} m/s)</span></span>
                            </div>
                            <div class="flex items-baseline justify-between">
                                <span class="text-xs text-slate-400">W porywach:</span>
                                <span class="text-base font-black text-red-400">do {wind_gusts} km/h</span>
                            </div>
                        </div>
                    </div>

                    <!-- STREFA ZAGROŻENIA ZADYMIENIEM -->
                    <div class="mt-3.5 p-3 rounded-lg bg-red-950/30 border border-red-800/50">
                        <div class="flex items-center gap-1.5 text-red-400 text-xs font-bold uppercase">
                            <span>🔥</span> SEKTOR ZADYMIENIA I SKAŻENIA:
                        </div>
                        <p class="text-xs font-bold text-red-200 mt-1">{smoke_sector}</p>
                        <div class="mt-2 text-xs text-slate-300">
                            <span class="text-slate-400 block font-semibold">Obiekty bezpośrednio zagrożone:</span>
                            <ul class="list-disc list-inside space-y-0.5 mt-1 text-slate-300">
                                {"".join([f"<li>{obj}</li>" for obj in weather.get('smoke_threat_objects', [])])}
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- ZAOPATRZENIE WODNE -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                        <div class="flex items-center gap-2">
                            <span class="text-base">🚒</span>
                            <h2 class="font-bold text-slate-100 text-sm tracking-wide uppercase">
                                Zaopatrzenie Wodne
                            </h2>
                        </div>
                        <span class="text-xs bg-sky-950 text-sky-300 px-2 py-0.5 rounded border border-sky-800 font-semibold">
                            Węże W-75 (20m)
                        </span>
                    </div>

                    <div class="space-y-2.5">
                        <section class="p-3 rounded-lg border border-sky-800 bg-sky-950/30">
                            <h3 class="font-bold text-sky-200">Kubatura i zapotrzebowanie wody — szacunek</h3>
                            {building_water_html}
                        </section>
                        {hydrants_html}
                        {open_water_html}
                    </div>
                </div>

                <!-- MELDUNEK RADIOWY KDR -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box no-print">
                    <div class="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                        <div class="flex items-center gap-2">
                            <span class="text-base">📻</span>
                            <h3 class="font-bold text-slate-200 text-xs tracking-wider uppercase">
                                Gotowy Meldunek Radiowy KDR
                            </h3>
                        </div>
                    </div>
                    <textarea id="radioBriefingText" readonly rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-300 font-mono resize-none focus:outline-none">{radio_briefing}</textarea>
                    <button onclick="copyRadioBriefing()" class="w-full mt-2 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg border border-slate-700 transition flex items-center justify-center gap-1.5">
                        <span>📋</span> Kopiuj do schowka
                    </button>
                </div>

            </div>
        </div>

        <details class="card-box p-4" id="tactical-notes"><summary class="cursor-pointer font-bold">Uwagi taktyczne — do oceny KDR</summary><ul class="mt-3">{analysis_html}</ul></details>
        {source_details_html}
        <!-- STOPKA -->
        <footer class="pt-2 text-center text-xs text-slate-500 no-print border-t border-slate-800/60">
            AgentStraz • System Rozpoznania Taktycznego KDR OSP/PSP • Wygenerowano automatycznie
        </footer>

    </div>

    <!-- SKRYPTY INTERAKTYWNE -->
    <script>
        function copyRadioBriefing() {{
            const text = document.getElementById('radioBriefingText').value;
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('copyToast');
                toast.classList.remove('hidden');
                setTimeout(() => {{
                    toast.classList.add('hidden');
                }}, 3000);
            }}).catch(err => {{
                console.error('Błąd kopiowania:', err);
            }});
        }}

        function highlightElement(id) {{
            console.log("Wybrano obiekt taktyczny:", id);
        }}
    </script>
</body>
</html>
"""
    return html_content


def generate_report_file(input_source: str, output_path: str, is_text: bool = False) -> str:
    """
    Tworzy plik HTML na podstawie ścieżki do pliku JSON lub tekstu/markdown.
    """
    if is_text or input_source.endswith((".md", ".txt")):
        with open(input_source, "r", encoding="utf-8") as f:
            content = f.read()
        data = parse_text_recon(content)
    elif input_source.endswith(".json"):
        with open(input_source, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Próba bezpośredniego parsowania jako string json lub markdown
        try:
            data = json.loads(input_source)
        except Exception:
            data = parse_text_recon(input_source)

    html = render_html(data, standalone=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="AgentStraz - Wizualizator Karty Rozpoznania Bojowego OSP/PSP w formacie HTML")
    parser.add_argument("--demo", action="store_true", help="Generuje przykładową kartę rozpoznania dla celów testowych")
    parser.add_argument("--input", "-i", type=str, help="Ścieżka do wejściowego pliku JSON z danymi rozpoznania")
    parser.add_argument("--text-input", "-t", type=str, help="Ścieżka do wejściowego pliku tekstowego / Markdown (AGENTS.md format)")
    parser.add_argument("--output", "-o", type=str, default="karta_rozpoznania.html", help="Ścieżka wyjściowego pliku HTML")
    parser.add_argument("--open", action="store_true", help="Otwiera wygenerowany plik w domyślnej przeglądarce")

    args = parser.parse_args()

    if not (args.demo or args.input or args.text_input):
        parser.error("Podaj --demo, --input lub --text-input")

    if args.demo:
        print("🚒 Generowanie przykładowej Karty Rozpoznania Bojowego KDR...")
        data = DEFAULT_DEMO_DATA
        html = render_html(data, standalone=True)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ Zapisano pomyślnie w: {os.path.abspath(args.output)}")
    elif args.text_input:
        generate_report_file(args.text_input, args.output, is_text=True)
        print(f"✅ Przetworzono tekst i zapisano w: {os.path.abspath(args.output)}")
    elif args.input:
        generate_report_file(args.input, args.output, is_text=False)
        print(f"✅ Przetworzono JSON i zapisano w: {os.path.abspath(args.output)}")

    if args.open:
        import webbrowser
        webbrowser.open(os.path.abspath(args.output))


if __name__ == "__main__":
    main()
