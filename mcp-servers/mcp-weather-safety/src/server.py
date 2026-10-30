"""
Główny Serwer MCP: mcp-weather-safety
Narzędzia telemetrii pogodowej, wektora wiatru i strefy zadymienia dla KDR OSP/PSP.
"""

from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from .imgw_client import get_imgw_weather
from .openmeteo_client import get_openmeteo_weather
from .plume_analysis import calculate_smoke_plume

mcp = FastMCP(
    "weather-safety",
    instructions="Serwer MCP do analizy warunków meteorologicznych w czasie rzeczywistym (IMGW-PIB) oraz wyznaczania wektora zadymienia, porywów wiatru i strefy zagrożenia pożarowego dla Straży Pożarnej."
)


@mcp.tool()
async def get_tactical_wind_and_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Pobiera aktualny kierunek i prędkość wiatru, porywy, temperaturę i wilgotność powietrza
    dla miejsca zdarzenia z najbliższej stacji IMGW-PIB oraz siatki wysokiej rozdzielczości.

    Args:
        lat: Szerokość geograficzna WGS84 miejsca akcji
        lon: Długość geograficzna WGS84 miejsca akcji
    """
    imgw = await get_imgw_weather(lat, lon)
    meteo = await get_openmeteo_weather(lat, lon)

    # Łączenie danych: priorytet IMGW dla stacji pomiarowej, Open-Meteo dla porywów wiatru
    wind_dir = imgw["wind_direction_deg"] if imgw else (meteo["wind_direction_deg"] if meteo else 0.0)
    wind_speed = imgw["wind_speed_kmh"] if imgw else (meteo["wind_speed_kmh"] if meteo else 0.0)
    gusts = meteo["wind_gusts_kmh"] if meteo else 0.0
    temp = imgw["temperature_c"] if imgw else (meteo["temperature_c"] if meteo else 15.0)
    humidity = imgw["humidity_pct"] if imgw else (meteo["humidity_pct"] if meteo else 50.0)

    plume = calculate_smoke_plume(wind_dir, wind_speed, gusts_kmh=gusts)

    station_desc = (
        f"{imgw['station_name']} ({imgw['station_distance_km']} km)"
        if imgw else "Siatka numeryczna (brak stacji IMGW w zasięgu)"
    )

    return {
        "success": True,
        "station_info": station_desc,
        "temperature_c": temp,
        "humidity_pct": humidity,
        "wind": plume["wind_from"],
        "smoke_plume": plume["smoke_plume"],
        "tactical_assessment": plume["tactical_assessment"],
    }


@mcp.tool()
async def get_smoke_and_hazard_zone(
    lat: float,
    lon: float,
    override_wind_deg: Optional[float] = None,
    override_speed_kmh: Optional[float] = None
) -> Dict[str, Any]:
    """
    Wyznacza strefę rozprzestrzeniania się dymu pożarowego / chmury toksycznej.
    Umożliwia podanie własnego kierunku wiatru zaobserwowanego przez ratowników na miejscu.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
        override_wind_deg: Opcjonalny kierunek wiatru w stopniach (0-360) zaobserwowany na miejscu
        override_speed_kmh: Opcjonalna prędkość wiatru w km/h
    """
    if override_wind_deg is None or override_speed_kmh is None:
        live = await get_tactical_wind_and_weather(lat, lon)
        wind_dir = override_wind_deg if override_wind_deg is not None else live["wind"]["degrees"]
        wind_spd = override_speed_kmh if override_speed_kmh is not None else live["wind"]["speed_kmh"]
        gusts = live["wind"].get("gusts_kmh") or 0.0
    else:
        wind_dir = override_wind_deg
        wind_spd = override_speed_kmh
        gusts = 0.0

    plume = calculate_smoke_plume(wind_dir, wind_spd, gusts_kmh=gusts)

    return {
        "success": True,
        "source": "Manualny odczyt KDR" if override_wind_deg is not None else "IMGW-PIB Live",
        "smoke_vector": plume["smoke_plume"],
        "tactical_advice": plume["tactical_assessment"]["tactical_advice"],
        "hazard_cone": plume["smoke_plume"]["hazard_cone_range"],
        "fire_spread_risk": plume["tactical_assessment"]["spread_risk"],
    }


@mcp.tool()
async def get_meteo_tactical_brief(lat: float, lon: float) -> Dict[str, Any]:
    """
    Generuje gotowy meldunek meteo do Karty Rozpoznania Bojowego.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
    """
    weather = await get_tactical_wind_and_weather(lat, lon)
    w = weather["wind"]
    sp = weather["smoke_plume"]
    ta = weather["tactical_assessment"]

    gust_str = f" (w porywach do {int(w['gusts_kmh'])} km/h)" if w.get("gusts_kmh") else ""
    brief_lines = [
        f"💨 WARUNKI METEO (Stacja: {weather['station_info']}):",
        f"• Wiatr: {w['name'].upper()} ({w['code']}, {w['degrees']}°), {w['speed_kmh']} km/h{gust_str}",
        f"• Zagrożenie zadymieniem: Posesje w sektorze {sp['travel_direction_code']} ({sp['travel_direction_name']})",
        f"• Rekomendacja KDR: {ta['tactical_advice']}",
    ]
    if ta.get("gust_alert"):
        brief_lines.append(f"• {ta['gust_alert']}")

    return {
        "success": True,
        "radio_text": "\n".join(brief_lines),
        "details": weather,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
