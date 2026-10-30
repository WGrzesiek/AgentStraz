"""
Klient Open-Meteo do precyzyjnych, lokalnych pomiarów wiatru (w tym porywów wiatru).
"""

import httpx
from typing import Dict, Any, Optional


async def get_openmeteo_weather(lat: float, lon: float, timeout_sec: float = 6.0) -> Optional[Dict[str, Any]]:
    """
    Pobiera dane pogodowe w siatce 1km dla dokładnych współrzędnych miejsca akcji.
    Dostarcza kluczową informację o porywach wiatru (wind_gusts_10m).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    }
    headers = {
        "User-Agent": "MCP-Weather-Safety/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            curr = data.get("current", {})

            wind_speed = float(curr.get("wind_speed_10m") or 0.0)
            wind_dir = float(curr.get("wind_direction_10m") or 0.0)
            gusts = float(curr.get("wind_gusts_10m") or 0.0)
            temp = float(curr.get("temperature_2m") or 0.0)
            humidity = float(curr.get("relative_humidity_2m") or 0.0)

            return {
                "source": "Open-Meteo (Siatka lokalna)",
                "temperature_c": temp,
                "wind_speed_kmh": round(wind_speed, 1),
                "wind_speed_ms": round(wind_speed / 3.6, 1),
                "wind_direction_deg": wind_dir,
                "wind_gusts_kmh": round(gusts, 1),
                "humidity_pct": humidity,
            }
    except Exception:
        return None
