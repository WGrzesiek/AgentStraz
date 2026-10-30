"""
Klient Krajowej Integracji Uzbrojenia Terenu (KIUT) - bazy GESUT GUGiK.
Pobiera informacje o sieciach podziemnych i naziemnych (gaz, elektroenergetyka, wodociągi)
przez zapytania OGC WMS (GetFeatureInfo oraz GetMap).
"""

import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
try:
    from .coords import wgs84_to_puwg1992
except (ImportError, ValueError):
    from coords import wgs84_to_puwg1992

KIUT_WMS_URL = "https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaUzbrojeniaTerenu"

# Główne warstwy GESUT istotne dla KDR OSP/PSP
LAYERS_CONFIG = {
    "gaz": "przewod_gazowy,armatura_gazowa",
    "prad": "przewod_elektroenergetyczny,urzadzenie_elektroenergetyczne",
    "woda": "przewod_wodociagowy,armatura_wodociagowa",
    "kanalizacja": "przewod_kanalizacyjny,urzadzenie_kanalizacyjne",
}

ALL_LAYERS = ",".join(LAYERS_CONFIG.values())


class UtilitiesSummary:
    def __init__(
        self,
        has_gas: bool = False,
        gas_details: Optional[List[str]] = None,
        has_power: bool = False,
        power_details: Optional[List[str]] = None,
        has_water: bool = False,
        water_details: Optional[List[str]] = None,
        map_image_url: str = "",
        raw_text: str = "",
    ):
        self.has_gas = has_gas
        self.gas_details = gas_details or []
        self.has_power = has_power
        self.power_details = power_details or []
        self.has_water = has_water
        self.water_details = water_details or []
        self.map_image_url = map_image_url
        self.raw_text = raw_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_gas": self.has_gas,
            "gas_details": self.gas_details,
            "has_power": self.has_power,
            "power_details": self.power_details,
            "has_water": self.has_water,
            "water_details": self.water_details,
            "map_image_url": self.map_image_url,
            "summary_tactical": self.to_tactical_summary(),
        }

    def to_tactical_summary(self) -> str:
        lines = []
        if self.has_gas:
            lines.append("⚠️ SIEC GAZOWA WYKRYTA w strefie zdarzenia:")
            for d in self.gas_details[:4]:
                lines.append(f"  • {d}")
        else:
            lines.append("• Gaz: Brak wykrytych przewodów w bezpośrednim buforze GESUT.")

        if self.has_power:
            lines.append("⚡ ELEKTROENERGETYKA:")
            for d in self.power_details[:4]:
                lines.append(f"  • {d}")
        else:
            lines.append("• Prąd: Brak kolizyjnych sieci WN/SN w buforze.")

        if self.has_water:
            lines.append("💧 WODOCIĄGI (Sieć komunalna GESUT):")
            for d in self.water_details[:4]:
                lines.append(f"  • {d}")

        return "\n".join(lines)


def generate_kiut_map_url(
    lat: float,
    lon: float,
    box_size_m: int = 150,
    width: int = 800,
    height: int = 800
) -> str:
    """
    Generuje bezpośredni adres URL do wycinka mapy uzbrojenia terenu (WMS GetMap).
    Może być osadzony jako podgląd na tablecie lub w aplikacji strażackiej.
    """
    x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)
    half = box_size_m / 2.0

    # W układzie 1992: minx, miny, maxx, maxy (gdzie x to Northing, y to Easting)
    # WMS 1.1.1 przyjmuje BBOX w kolejności: miny, minx, maxy, maxx (Easting, Northing)
    min_easting = y_1992 - half
    max_easting = y_1992 + half
    min_northing = x_1992 - half
    max_northing = x_1992 + half

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "LAYERS": "geoportal,przewod_gazowy,armatura_gazowa,przewod_elektroenergetyczny,urzadzenie_elektroenergetyczne,przewod_wodociagowy,armatura_wodociagowa",
        "STYLES": "",
        "SRS": "EPSG:2180",
        "BBOX": f"{min_easting},{min_northing},{max_easting},{max_northing}",
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
    }
    return f"{KIUT_WMS_URL}?{urlencode(params)}"


async def query_utilities_gesut(
    lat: float,
    lon: float,
    radius_m: int = 100,
    timeout_sec: float = 8.0
) -> UtilitiesSummary:
    """
    Odpytuje usługę WMS GetFeatureInfo KIUT GUGiK dla podanych współrzędnych.
    Zwraca ustrukturyzowane podsumowanie wykrytej infrastruktury sieciowej.
    """
    x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)
    box_m = max(50, radius_m * 2)
    half = box_m / 2.0

    min_easting = y_1992 - half
    max_easting = y_1992 + half
    min_northing = x_1992 - half
    max_northing = x_1992 + half

    # Punkt zapytania w środku obrazu
    img_size = 301
    center_pixel = 150

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": ALL_LAYERS,
        "QUERY_LAYERS": ALL_LAYERS,
        "STYLES": "",
        "SRS": "EPSG:2180",
        "BBOX": f"{min_easting},{min_northing},{max_easting},{max_northing}",
        "WIDTH": str(img_size),
        "HEIGHT": str(img_size),
        "X": str(center_pixel),
        "Y": str(center_pixel),
        "INFO_FORMAT": "text/html",
        "FEATURE_COUNT": "30",
    }

    map_url = generate_kiut_map_url(lat, lon, box_size_m=box_m)

    headers = {
        "User-Agent": "MCP-Geoportal-FireRecon/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(KIUT_WMS_URL, params=params, headers=headers)
            content = resp.text

            return _parse_feature_info(content, map_url)
    except Exception as e:
        # Zwracamy obiekt z wygenerowanym URL mapy nawet przy braku odpowiedzi tekstowej
        return UtilitiesSummary(
            has_gas=False,
            gas_details=["Brak łączności z serwerem WMS GESUT (timeout lub błąd PODGiK)"],
            map_image_url=map_url,
            raw_text=str(e),
        )


def _parse_feature_info(html_or_text: str, map_url: str) -> UtilitiesSummary:
    """
    Parsuje wynik GetFeatureInfo z Geoportalu/KIUT.
    """
    text_lower = html_or_text.lower()

    gas_details: List[str] = []
    power_details: List[str] = []
    water_details: List[str] = []

    has_gas = "gaz" in text_lower or "przewod_gaz" in text_lower
    has_power = "elektro" in text_lower or "prad" in text_lower or "napowietrz" in text_lower or "stacja" in text_lower
    has_water = "wodo" in text_lower or "wodociag" in text_lower or "hydrant" in text_lower

    # Analiza cech charakterystycznych
    if "wysokiego ciśnienia" in text_lower or "w/c" in text_lower or "wysokie" in text_lower:
        gas_details.append("Rurociąg WYSOKIEGO ciśnienia w sąsiedztwie!")
    elif "średniego ciśnienia" in text_lower or "ś/c" in text_lower or "srednie" in text_lower:
        gas_details.append("Gazociąg średniego ciśnienia (ś/c)")
    elif "niskiego ciśnienia" in text_lower or "n/c" in text_lower or "niskie" in text_lower:
        gas_details.append("Gazociąg niskiego ciśnienia (n/c)")
    elif has_gas:
        gas_details.append("Zarejestrowana sieć lub przyłącze gazowe GESUT")

    if "przyłącze" in text_lower or "przylacze" in text_lower:
        if has_gas:
            gas_details.append("Wykryte przyłącze gazowe do obiektu")

    if "transformator" in text_lower or "stacja transformatorowa" in text_lower or "trafo" in text_lower:
        power_details.append("Stacja transformatorowa / transformator w rejonie")
    if "sn" in text_lower or "średniego napięcia" in text_lower:
        power_details.append("Linia Średniego Napięcia (SN)")
    elif "wn" in text_lower or "wysokiego napięcia" in text_lower:
        power_details.append("Linia Wysokiego Napięcia (WN)")
    elif has_power:
        power_details.append("Infrastruktura elektroenergetyczna zarejestrowana w GESUT")

    if "hydrant" in text_lower:
        water_details.append("Zarejestrowany hydrant w sieci komunalnej GESUT")
    if "zasuwa" in text_lower:
        water_details.append("Armatura wodociągowa (zasuwa sieciowa)")
    elif has_water:
        water_details.append("Przewód sieci wodociągowej w rejonie")

    return UtilitiesSummary(
        has_gas=has_gas,
        gas_details=gas_details,
        has_power=has_power,
        power_details=power_details,
        has_water=has_water,
        water_details=water_details,
        map_image_url=map_url,
        raw_text=html_or_text[:1000],
    )
