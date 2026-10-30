"""
Klient Uniwersalnej Usługi Geokodowania (UUG) GUGiK oraz fallback Nominatim (OSM).
Udostępnia funkcję zamiany adresu tekstowego na współrzędne WGS84 i PUWG 1992.
"""

import asyncio
import json
import os
import threading
import time
from functools import lru_cache
from urllib.parse import urlencode
from typing import Optional, Dict, Any, List
try:
    from .coords import puwg1992_to_wgs84, wgs84_to_puwg1992
except (ImportError, ValueError):
    from coords import puwg1992_to_wgs84, wgs84_to_puwg1992


def parse_uug_response(data, address):
    """UUG GetAddress zapisuje x=E, y=N, zgodnie z geometry_wkt POINT(E N)."""
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, dict) or len(results) != 1:
        return None
    item = next(iter(results.values()))
    east, north = float(item["x"]), float(item["y"])
    lat, lon = puwg1992_to_wgs84(north, east)
    if not (48.9 <= lat <= 55.1 and 14 <= lon <= 24.2):
        return None
    city = item.get("miejscowosc") or item.get("city", "")
    street = item.get("ulica") or item.get("street", "")
    house = item.get("numer") or item.get("number") or item.get("house_number", "")
    full = ", ".join(filter(None, [city, f"ul. {street} {house}".strip() if street else str(house)]))
    return GeocodingResult(lat, lon, north, east, full or address,
                           city=city, street=street, house_number=str(house),
                           postcode=item.get("code") or item.get("postcode", ""),
                           teryt_simc=str(item.get("simc", "")),
                           teryt_gmina=str(item.get("teryt") or item.get("terc", "")),
                           source="GUGiK_UUG", raw=item)


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
    try:
        try:
            from .building_client import _request
        except ImportError:
            from building_client import _request
        from urllib.parse import urlencode
        url = "https://services.gugik.gov.pl/uug?" + urlencode({"request": "GetAddress", "address": address})
        raw = await asyncio.to_thread(_request, url, timeout=timeout_sec)
        return parse_uug_response(json.loads(raw), address)
    except (OSError, ValueError, KeyError, TypeError):
        return None


async def _geocode_nominatim(address: str, timeout_sec: float = 6.0) -> Optional[GeocodingResult]:
    """
    Awaryjne geokodowanie przez Nominatim OSM z ograniczeniem do Polski (countrycodes=pl).
    """
    url = os.environ.get("NOMINATIM_SEARCH_URL", "https://nominatim.openstreetmap.org/search")
    params = {
        "q": address,
        "format": "jsonv2",
        "countrycodes": "pl",
        "limit": 1,
        "addressdetails": 1,
    }
    try:
        data = await asyncio.to_thread(_nominatim_search, url + "?" + urlencode(params), int(time.time() // 3600), timeout_sec)
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


_NOMINATIM_LOCK = threading.Lock()
_NOMINATIM_LAST_REQUEST = 0.0


@lru_cache(maxsize=256)
def _nominatim_search(url, hour_bucket, timeout_sec):
    # Cache i maksymalnie 1 żądanie/s w tym procesie (publiczna instancja OSM).
    global _NOMINATIM_LAST_REQUEST
    try:
        from .building_client import _request
    except ImportError:
        from building_client import _request
    import hashlib
    from pathlib import Path
    cache_dir = Path(os.environ.get("BUILDING_CACHE_DIR") or Path(__file__).resolve().parents[3] / "reports/cache/buildings")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / ("geocode-" + hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")
    with _NOMINATIM_LOCK:
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < 3600:
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        remaining = 1.0 - (time.monotonic() - _NOMINATIM_LAST_REQUEST)
        if remaining > 0:
            time.sleep(remaining)
        _NOMINATIM_LAST_REQUEST = time.monotonic()
        result = json.loads(_request(url, timeout=timeout_sec))
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
