"""
Klient oficjalnego API IMGW-PIB (Instytut Meteorologii i Gospodarki Wodnej).
Pobiera dane synoptyczne ze stacji telemetrycznych w czasie rzeczywistym.
"""

import httpx
from typing import Dict, Any, Optional
from .stations import find_nearest_imgw_station


async def get_imgw_weather(lat: float, lon: float, timeout_sec: float = 6.0) -> Optional[Dict[str, Any]]:
    """
    Pobiera najświeższe dane pogodowe z najbliższej stacji synoptycznej IMGW.
    """
    station_id, station_name, dist_km = find_nearest_imgw_station(lat, lon)
    url = f"https://danepubliczne.imgw.pl/api/data/synop/id/{station_id}"
    headers = {
        "User-Agent": "MCP-Weather-Safety/1.0 (Straz Pozarna Recon)",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()

            # Bezpieczna konwersja wartości IMGW
            temp = float(data.get("temperatura") or 0.0)
            wind_speed_ms = float(data.get("predkosc_wiatru") or 0.0)
            wind_speed_kmh = round(wind_speed_ms * 3.6, 1)
            wind_dir_deg = float(data.get("kierunek_wiatru") or 0.0)
            humidity = float(data.get("wilgotnosc_wzgledna") or 0.0)
            pressure = float(data.get("cisnienie") or 1013.2)

            return {
                "source": "IMGW-PIB",
                "station_id": station_id,
                "station_name": station_name,
                "station_distance_km": dist_km,
                "measurement_date": data.get("data_pomiaru", ""),
                "measurement_hour": f"{data.get('godzina_pomiaru', '')}:00",
                "temperature_c": temp,
                "wind_speed_ms": wind_speed_ms,
                "wind_speed_kmh": wind_speed_kmh,
                "wind_direction_deg": wind_dir_deg,
                "humidity_pct": humidity,
                "pressure_hpa": pressure,
            }
    except Exception:
        return None
