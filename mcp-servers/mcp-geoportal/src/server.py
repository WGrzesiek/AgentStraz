"""
Główny Serwer MCP: mcp-geoportal-gov-pl
Udostępnia narzędzia geodezyjne i infrastrukturalne GUGiK / Geoportal dla Agenta Rozpoznania Straży OSP/PSP.
"""

import re
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

from .uug_client import geocode_address as uug_geocode
from .uldk_client import get_parcel_by_coords
from .kiut_client import query_utilities_gesut, generate_kiut_map_url
from .coords import wgs84_to_puwg1992

# Inicjalizacja serwera FastMCP
mcp = FastMCP(
    "geoportal-gov-pl",
    instructions="Serwer MCP do geokodowania adresów (PRG/EMUiA), pobierania numerów i geometrii działek (ULDK) oraz identyfikacji sieci gazowych, elektroenergetycznych i wodociągowych (GESUT/KIUT) dla Kierującego Działaniem Ratowniczym OSP/PSP."
)


@mcp.tool()
async def geocode_address(address: str) -> Dict[str, Any]:
    """
    Geokoduje adres w Polsce na współrzędne GPS (WGS84) oraz układ geodezyjny PUWG 1992.
    Korzysta z oficjalnej bazy PRG/EMUiA GUGiK oraz zapasowo z OpenStreetMap.

    Args:
        address: Pełny lub częściowy adres, np. 'Nowa Wieś, ul. Sosnowa 14' lub 'Otwock, Kołłątaja 8'
    """
    res = await uug_geocode(address)
    if not res:
        return {
            "success": False,
            "message": f"Nie udało się zlokalizować adresu '{address}' w rejestrze PRG/EMUiA.",
        }

    return {
        "success": True,
        "address": res.full_address,
        "coordinates": {
            "lat": res.lat,
            "lon": res.lon,
            "wgs84": f"{res.lat}, {res.lon}",
        },
        "puwg1992": {
            "x_northing": res.x_1992,
            "y_easting": res.y_1992,
        },
        "teryt": {
            "simc": res.teryt_simc,
            "gmina": res.teryt_gmina,
        },
        "source": res.source,
    }


@mcp.tool()
async def get_parcel_info(lat: float, lon: float) -> Dict[str, Any]:
    """
    Pobiera informacje o działce ewidencyjnej z rejestru ULDK GUGiK na podstawie współrzędnych GPS.
    Zwraca pełny numer ewidencyjny działki, obręb, gminę oraz geometrię WKT.

    Args:
        lat: Szerokość geograficzna WGS84 (np. 52.2319)
        lon: Długość geograficzna WGS84 (np. 21.0067)
    """
    parcel = await get_parcel_by_coords(lat, lon)
    if not parcel:
        return {
            "success": False,
            "message": f"Brak działki ewidencyjnej w ULDK dla punktu ({lat}, {lon}).",
        }

    return {
        "success": True,
        "parcel_id": parcel.parcel_id,
        "parcel_number": parcel.parcel_number,
        "commune": parcel.commune,
        "county": parcel.county,
        "voivodship": parcel.voivodship,
        "has_geometry": bool(parcel.wkt_geometry),
    }


@mcp.tool()
async def get_utilities_near_point(lat: float, lon: float, radius_m: int = 100) -> Dict[str, Any]:
    """
    Weryfikuje uzbrojenie terenu z bazy GESUT (Krajowa Integracja Uzbrojenia Terenu) wokół punktu.
    Sprawdza obecność rurociągów gazowych (wysokie/średnie/niskie ciśnienie), linii prądu,
    stacji transformatorowych i sieci wodociągowej.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
        radius_m: Promień poszukiwań w metrach (domyślnie 100m)
    """
    summary = await query_utilities_gesut(lat, lon, radius_m=radius_m)
    return {
        "success": True,
        "has_gas": summary.has_gas,
        "gas_details": summary.gas_details,
        "has_power": summary.has_power,
        "power_details": summary.power_details,
        "has_water": summary.has_water,
        "water_details": summary.water_details,
        "map_image_url": summary.map_image_url,
        "tactical_report": summary.to_tactical_summary(),
    }


@mcp.tool()
async def get_utilities_map_url(lat: float, lon: float, box_size_m: int = 150) -> Dict[str, Any]:
    """
    Generuje bezpośredni link do mapy uzbrojenia terenu (WMS GetMap) w wysokiej rozdzielczości.
    Do wyświetlenia na tablecie wozów bojowych lub pobrania jako obraz.

    Args:
        lat: Szerokość geograficzna WGS84
        lon: Długość geograficzna WGS84
        box_size_m: Szerokość wycinka terenu w metrach (domyślnie 150m)
    """
    map_url = generate_kiut_map_url(lat, lon, box_size_m=box_size_m)
    return {
        "map_url": map_url,
        "box_size_meters": box_size_m,
        "description": "Wycinek mapy sieci podziemnych GESUT (gaz, elektroenergetyka, wodociągi) z Geoportalu.",
    }


@mcp.tool()
async def full_site_recon(address_or_coords: str) -> Dict[str, Any]:
    """
    Kompleksowe rozpoznanie wstępne miejsca zdarzenia w jednym zapytaniu.
    Przyjmuje adres (np. 'Lipowa 8, Halinów') lub współrzędne '52.23, 21.01'.
    Wykonuje geokodowanie, identyfikację działki katastralnej i analizę sieci GESUT.

    Args:
        address_or_coords: Adres tekstowy lub ciąg współrzędnych 'lat, lon'
    """
    input_str = address_or_coords.strip()

    # Sprawdzenie czy wejście to współrzędne liczbowe
    coords_match = re.match(r"^([0-9]+\.?[0-9]*)[,\s]+([0-9]+\.?[0-9]*)$", input_str)
    if coords_match:
        lat = float(coords_match.group(1))
        lon = float(coords_match.group(2))
        full_addr = f"Współrzędne GPS: {lat}, {lon}"
    else:
        geo = await uug_geocode(input_str)
        if not geo:
            return {
                "success": False,
                "message": f"Nie udało się odnaleźć lokalizacji dla: '{input_str}'",
            }
        lat = geo.lat
        lon = geo.lon
        full_addr = geo.full_address

    # Równoległe pobranie działki i uzbrojenia terenu
    parcel = await get_parcel_by_coords(lat, lon)
    utilities = await query_utilities_gesut(lat, lon, radius_m=100)

    return {
        "success": True,
        "address": full_addr,
        "coordinates": {
            "lat": lat,
            "lon": lon,
            "wgs84": f"{lat}, {lon}",
        },
        "parcel": parcel.to_dict() if parcel else None,
        "utilities": {
            "has_gas": utilities.has_gas,
            "gas_details": utilities.gas_details,
            "has_power": utilities.has_power,
            "power_details": utilities.power_details,
            "has_water": utilities.has_water,
            "water_details": utilities.water_details,
            "tactical_report": utilities.to_tactical_summary(),
        },
        "map_image_url": utilities.map_image_url,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
