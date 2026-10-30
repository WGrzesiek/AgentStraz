"""
Klient Uniwersalnej Usługi Geokodowania (UUG) GUGiK oraz fallback Nominatim (OSM).
Udostępnia funkcję zamiany adresu tekstowego na współrzędne WGS84 i PUWG 1992.
"""

import httpx
from typing import Optional, Dict, Any, List
try:
    from .coords import puwg1992_to_wgs84, wgs84_to_puwg1992
except (ImportError, ValueError):
    from coords import puwg1992_to_wgs84, wgs84_to_puwg1992


class GeocodingResult:
    def __init__(
        self,
        lat: float,
        lon: float,
        x_1992: float,
        y_1992: float,
        full_address: str,
        city: str = "",
        street: str = "",
        house_number: str = "",
        postcode: str = "",
        teryt_simc: str = "",
        teryt_gmina: str = "",
        source: str = "UUG_GUGiK",
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.lat = lat
        self.lon = lon
        self.x_1992 = x_1992
        self.y_1992 = y_1992
        self.full_address = full_address
        self.city = city
        self.street = street
        self.house_number = house_number
        self.postcode = postcode
        self.teryt_simc = teryt_simc
        self.teryt_gmina = teryt_gmina
        self.source = source
        self.raw = raw or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "x_1992": self.x_1992,
            "y_1992": self.y_1992,
            "full_address": self.full_address,
            "city": self.city,
            "street": self.street,
            "house_number": self.house_number,
            "postcode": self.postcode,
            "teryt_simc": self.teryt_simc,
            "teryt_gmina": self.teryt_gmina,
            "source": self.source,
        }


async def geocode_address(address: str, timeout_sec: float = 8.0) -> Optional[GeocodingResult]:
    """
    Geokoduje podany adres. W pierwszej kolejności odpytuje oficjalny serwis GUGiK UUG.
    W przypadku braku odpowiedzi lub braku dopasowania odpytuje awaryjnie OpenStreetMap Nominatim.
    """
    clean_address = address.strip()
    if not clean_address:
        return None

    # 1. Próba UUG GUGiK
    uug_res = await _geocode_uug(clean_address, timeout_sec=timeout_sec)
    if uug_res:
        return uug_res

    # 2. Awaryjna próba Nominatim OSM (gdy np. w UUG jest literówka w formacie)
    osm_res = await _geocode_nominatim(clean_address, timeout_sec=timeout_sec)
    if osm_res:
        return osm_res

    return None


async def _geocode_uug(address: str, timeout_sec: float = 8.0) -> Optional[GeocodingResult]:
    """
    Odpytanie oficjalnej usługi UUG GUGiK: https://services.gugik.gov.pl/uug/
    """
    url = "https://services.gugik.gov.pl/uug"
    params = {
        "request": "GetAddress",
        "address": address,
    }
    headers = {
        "User-Agent": "MCP-Geoportal-FireRecon/1.0 (Straż Pożarna OSP/PSP Recon)",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()

            # Format odpowiedzi UUG GUGiK to zazwyczaj słownik z kluczem 'results' lub bezpośrednia lista
            results = data.get("results") if isinstance(data, dict) else data
            if not results or not isinstance(results, dict):
                return None

            # UUG zwraca słownik ID -> Obiekt punktu adresowego
            # Pobieramy pierwszy/najbardziej pasujący element
            first_key = next(iter(results))
            item = results[first_key]

            # Koordynaty w UUG są zazwyczaj w układzie 1992 (x, y) lub WGS84
            # np. item['x'], item['y']
            raw_x = item.get("x")
            raw_y = item.get("y")

            if raw_x is None or raw_y is None:
                return None

            val_x = float(raw_x)
            val_y = float(raw_y)

            # Rozpoznanie czy to 1992 czy WGS84:
            # W PUWG 1992: X (Northing) ~ 150000..850000, Y (Easting) ~ 150000..900000
            # W WGS84: Lat ~ 49..55, Lon ~ 14..25
            if val_x > 1000 and val_y > 1000:
                x_1992 = val_x
                y_1992 = val_y
                lat, lon = puwg1992_to_wgs84(x_1992, y_1992)
            else:
                lat = val_x if val_x > val_y else val_y
                lon = val_y if val_x > val_y else val_x
                x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)

            city = item.get("miejscowosc", "") or item.get("city", "")
            street = item.get("ulica", "") or item.get("street", "")
            house = item.get("numer", "") or item.get("house_number", "")
            postcode = item.get("kod", "") or item.get("postcode", "")

            full_addr_parts = [city]
            if street:
                full_addr_parts.append(f"ul. {street} {house}".strip())
            elif house:
                full_addr_parts.append(str(house))

            full_address = ", ".join([p for p in full_addr_parts if p]) or address

            return GeocodingResult(
                lat=lat,
                lon=lon,
                x_1992=x_1992,
                y_1992=y_1992,
                full_address=full_address,
                city=city,
                street=street,
                house_number=house,
                postcode=postcode,
                teryt_simc=str(item.get("simc", "")),
                teryt_gmina=str(item.get("terc", "")),
                source="GUGiK_UUG",
                raw=item,
            )

    except Exception:
        return None


async def _geocode_nominatim(address: str, timeout_sec: float = 6.0) -> Optional[GeocodingResult]:
    """
    Awaryjne geokodowanie przez Nominatim OSM z ograniczeniem do Polski (countrycodes=pl).
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "jsonv2",
        "countrycodes": "pl",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "MCP-Geoportal-FireRecon/1.0 (Straz Pozarna Recon)",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data or not isinstance(data, list):
                return None

            top = data[0]
            lat = float(top["lat"])
            lon = float(top["lon"])
            x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)

            addr_det = top.get("address", {})
            city = addr_det.get("city") or addr_det.get("town") or addr_det.get("village", "")
            street = addr_det.get("road", "")
            house = addr_det.get("house_number", "")
            postcode = addr_det.get("postcode", "")

            return GeocodingResult(
                lat=lat,
                lon=lon,
                x_1992=x_1992,
                y_1992=y_1992,
                full_address=top.get("display_name", address),
                city=city,
                street=street,
                house_number=house,
                postcode=postcode,
                source="OSM_Nominatim_Fallback",
                raw=top,
            )
    except Exception:
        return None
