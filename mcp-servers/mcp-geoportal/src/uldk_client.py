"""
Klient Usługi Lokalizacji Działek Katastralnych (ULDK) GUGiK.
Pozwala na identyfikację działki ewidencyjnej, pobranie jej numeru TERYT,
obrębu oraz geometrii obrysu (WKT).
"""

import httpx
from typing import Optional, Dict, Any
try:
    from .coords import wgs84_to_puwg1992
except (ImportError, ValueError):
    from coords import wgs84_to_puwg1992


class ParcelInfo:
    def __init__(
        self,
        parcel_id: str,
        voivodship: str = "",
        county: str = "",
        commune: str = "",
        region: str = "",
        parcel_number: str = "",
        wkt_geometry: str = "",
        raw_response: str = "",
    ):
        self.parcel_id = parcel_id
        self.voivodship = voivodship
        self.county = county
        self.commune = commune
        self.region = region
        self.parcel_number = parcel_number
        self.wkt_geometry = wkt_geometry
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "parcel_number": self.parcel_number,
            "region": self.region,
            "commune": self.commune,
            "county": self.county,
            "voivodship": self.voivodship,
            "wkt_geometry": self.wkt_geometry,
        }


async def get_parcel_by_coords(lat: float, lon: float, timeout_sec: float = 6.0) -> Optional[ParcelInfo]:
    """
    Identyfikuje działkę katastralną na podstawie współrzędnych WGS84 (GPS).
    Współrzędne są konwertowane do PUWG 1992 i wysyłane do ULDK GUGiK.
    """
    x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)
    return await get_parcel_by_xy_1992(x_1992, y_1992, timeout_sec=timeout_sec)


async def get_parcel_by_xy_1992(x_1992: float, y_1992: float, timeout_sec: float = 6.0) -> Optional[ParcelInfo]:
    """
    Odpytanie ULDK GUGiK metodą GetParcelByXY w układzie PUWG 1992.
    """
    url = "https://uldk.gugik.gov.pl/"
    # W ULDK xy podaje się zazwyczaj: Y (Easting), X (Northing) lub X,Y w zależności od srid
    # Zgodnie ze specyfikacją ULDK: xy=X,Y dla EPSG:2180 (Northing, Easting) lub Y,X
    # Standard: xy={y_1992},{x_1992} lub {x_1992},{y_1992}
    params = {
        "request": "GetParcelByXY",
        "xy": f"{y_1992},{x_1992}",
        "srid": "2180",
        "result": "geom,teryt,commune,county,voivodship",
    }
    headers = {
        "User-Agent": "MCP-Geoportal-FireRecon/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                # Spróbuj z odwrotną kolejnością współrzędnych
                params["xy"] = f"{x_1992},{y_1992}"
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    return None

            text = resp.text.strip()
            lines = text.splitlines()
            if not lines:
                return None

            # Kod 0 w pierwszej linii oznacza sukces
            status_line = lines[0].strip()
            if status_line != "0" or len(lines) < 2:
                # Próba w odwróconej osi, jeśli pierwsza nie zwróciła wyniku
                if params["xy"] == f"{y_1992},{x_1992}":
                    params["xy"] = f"{x_1992},{y_1992}"
                    resp2 = await client.get(url, params=params, headers=headers)
                    text2 = resp2.text.strip()
                    lines2 = text2.splitlines()
                    if lines2 and lines2[0].strip() == "0" and len(lines2) >= 2:
                        lines = lines2
                    else:
                        return None
                else:
                    return None

            data_line = lines[1].strip()
            parts = data_line.split("|") if "|" in data_line else data_line.split(";")

            # Parsowanie odpowiedzi ULDK
            parcel_id = parts[0].strip() if len(parts) > 0 else ""
            geom = ""
            commune = ""
            county = ""
            voivodship = ""

            for part in parts[1:]:
                p = part.strip()
                if "POLYGON" in p or "MULTIPOLYGON" in p:
                    geom = p
                elif not commune and len(p) > 2:
                    commune = p

            # Ekstrakcja numeru działki z pełnego TERYT (np. 141201_1.0001.1867/2 -> 1867/2)
            parcel_number = parcel_id.split(".")[-1] if "." in parcel_id else parcel_id

            return ParcelInfo(
                parcel_id=parcel_id,
                parcel_number=parcel_number,
                commune=commune,
                county=county,
                voivodship=voivodship,
                wkt_geometry=geom,
                raw_response=text,
            )
    except Exception:
        return None
