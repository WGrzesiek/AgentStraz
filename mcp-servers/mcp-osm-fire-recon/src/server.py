"""
Główny Serwer MCP: mcp-osm-fire-recon
Narzędzia zaopatrzenia wodnego, lokalizacji hydrantów i dróg pożarowych dla KDR OSP/PSP.
"""

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from .overpass_client import get_nearest_hydrants, get_water_sources, get_access_restrictions

mcp = FastMCP(
    "osm-fire-recon",
    instructions="Serwer MCP do analizy zaopatrzenia wodnego (hydranty nadziemne/podziemne, średnice DN, rzeki, stawy) oraz dróg pożarowych dla Straży Pożarnej na podstawie bazy OpenStreetMap."
)


@mcp.tool()
async def find_nearest_hydrants(lat: float, lon: float, radius_m: int = 600, max_results: int = 5) -> Dict[str, Any]:
    """
    Wyszukuje najbliższe hydranty pożarnicze wokół miejsca zdarzenia.
    Zwraca odległość, azymut, typ (nadziemny/podziemny), średnicę (DN) oraz liczbę wymaganych odcinków W-75.

    Args:
        lat: Szerokość geograficzna WGS84 miejsca akcji
        lon: Długość geograficzna WGS84 miejsca akcji
        radius_m: Promień poszukiwań w metrach (domyślnie 600m)
        max_results: Maksymalna liczba zwracanych hydrantów (domyślnie 5)
    """
    hydrants = await get_nearest_hydrants(lat, lon, radius_m=radius_m, max_results=max_results)
    if not hydrants:
        return {
            "success": True,
            "count": 0,
            "hydrants": [],
            "tactical_alert": f"UWAGA: Brak zarejestrowanych hydrantów w promieniu {radius_m} m! Konieczne zasilanie z wozów (GBA/GCBA) lub otwartego punktu czerpania wody.",
        }

    first = hydrants[0]
    underground_warning = "WYMAGANY STOJAK I KLUCZ PODZIEMNY!" if first.get("is_underground") else "Hydrant nadziemny"

    return {
        "success": True,
        "count": len(hydrants),
        "primary_hydrant": {
            "distance_m": first["distance_m"],
            "direction": first["direction"],
            "type": first["type"],
            "diameter": first["diameter"],
            "w75_sections": first["w75_sections"],
            "warning": underground_warning,
        },
        "hydrants": hydrants,
    }


@mcp.tool()
async def find_water_sources(lat: float, lon: float, radius_m: int = 1500, max_results: int = 5) -> Dict[str, Any]:
    """
    Wyszukuje otwarte punkty czerpania wody (rzeki, stawy, jeziora, baseny ppoż.).
    Określa możliwość zassania wody motopompą (M16/8) lub pompą pływającą (Niagara).

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
        radius_m: Promień poszukiwań w metrach (domyślnie 1500m)
        max_results: Maksymalna liczba zwracanych obiektów (domyślnie 5)
    """
    sources = await get_water_sources(lat, lon, radius_m=radius_m, max_results=max_results)
    return {
        "success": True,
        "count": len(sources),
        "water_sources": sources,
    }


@mcp.tool()
async def check_access_and_hazards(lat: float, lon: float, radius_m: int = 400) -> Dict[str, Any]:
    """
    Sprawdza drogi dojazdowe, oznaczone dojazdy pożarowe oraz drogi nieutwardzone/gruntowe
    pod kątem przejazdu ciężkich samochodów gaśniczych GCBA.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
        radius_m: Promień analizy w metrach (domyślnie 400m)
    """
    roads = await get_access_restrictions(lat, lon, radius_m=radius_m)
    return {
        "success": True,
        "count": len(roads),
        "road_conditions": roads,
    }


@mcp.tool()
async def get_water_supply_tactical_brief(lat: float, lon: float) -> Dict[str, Any]:
    """
    Kompleksowy meldunek zaopatrzenia wodnego w 1 wywołaniu:
    Wyszukuje hydranty (do 800m) oraz otwarte punkty czerpania wody (do 1500m)
    i generuje gotową formatkę do przeczytania przez radio dla rot gaśniczych.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
    """
    hydrants = await get_nearest_hydrants(lat, lon, radius_m=800, max_results=3)
    sources = await get_water_sources(lat, lon, radius_m=1500, max_results=2)

    report_lines = ["🚒 ZAOPATRZENIE WODNE (Meldunek Bojowy):"]

    if hydrants:
        for idx, h in enumerate(hydrants, start=1):
            h_type = h['type'].upper()
            d_str = f"{h['distance_m']} m ({h['direction']})"
            w75 = f"~{h['w75_sections']} odcinków W-75"
            warning = " [⚠️ WYMAGANY STOJAK + KLUCZ PODZIEMNY!]" if h.get("is_underground") else ""
            report_lines.append(f"{idx}. Hydrant {h_type} {h['diameter']}: {d_str} -> {w75}{warning}")
    else:
        report_lines.append("❌ BRAK HYDRANTÓW w promieniu 800m! Zasilanie z wozów / punktu otwartego.")

    if sources:
        report_lines.append("\n💧 PUNKTY CZERPANIA WODY (Otwarte):")
        for s in sources:
            report_lines.append(f"• {s['name']} ({s['type']}): {s['distance_m']} m ({s['direction']}) -> {s['recommended_gear']}")
    else:
        report_lines.append("\n• Brak otwartych cieków wodnych do 1.5 km.")

    return {
        "success": True,
        "hydrants_found": len(hydrants),
        "sources_found": len(sources),
        "tactical_radio_text": "\n".join(report_lines),
        "hydrants": hydrants,
        "sources": sources,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
