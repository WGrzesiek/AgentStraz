"""
Skrypt testowy uruchamiający pełen potok rozpoznania bojowego dla zadanego adresu.
"""

import asyncio
import sys
import os

# Dodanie katalogów src bezpośrednio do sys.path z aliasami
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "mcp-servers", "mcp-geoportal", "src"))
import uug_client
import uldk_client
import kiut_client

sys.path.insert(0, os.path.join(BASE_DIR, "mcp-servers", "mcp-osm-fire-recon", "src"))
import overpass_client
import water_supply

sys.path.insert(0, os.path.join(BASE_DIR, "mcp-servers", "mcp-weather-safety", "src"))
import imgw_client
import openmeteo_client
import plume_analysis


async def main():
    address = "Łętkowice 25"
    print(f"=== ROZPOCZYNAM ROZPOZNANIE BOJOWE DLA: {address} ===")

    # 1. Geokodowanie
    print("[1/5] Geokodowanie adresu (PRG/UUG)...")
    geo = await uug_client.geocode_address(address)
    if not geo:
        print("Nie udało się zgeokodować adresu.")
        return

    print(f"Lokalizacja: {geo.full_address}")
    print(f"Współrzędne: Lat={geo.lat}, Lon={geo.lon} | PUWG 1992: X={geo.x_1992}, Y={geo.y_1992}")

    # 2. Działka ewidencyjna (ULDK)
    print("\n[2/5] Weryfikacja działki katastralnej (ULDK)...")
    parcel = await uldk_client.get_parcel_by_coords(geo.lat, geo.lon)
    if parcel:
        print(f"Działka nr: {parcel.parcel_number} (TERYT: {parcel.parcel_id}), gmina: {parcel.commune}")
    else:
        print("Działka: Brak bezpośredniej odpowiedzi z serwera ULDK")

    # 3. Pogoda i Wiatr (IMGW + Open-Meteo)
    print("\n[3/5] Pobieranie warunków meteo (IMGW-PIB)...")
    imgw = await imgw_client.get_imgw_weather(geo.lat, geo.lon)
    meteo = await openmeteo_client.get_openmeteo_weather(geo.lat, geo.lon)

    wind_dir = imgw["wind_direction_deg"] if imgw else (meteo["wind_direction_deg"] if meteo else 0.0)
    wind_spd = imgw["wind_speed_kmh"] if imgw else (meteo["wind_speed_kmh"] if meteo else 0.0)
    gusts = meteo["wind_gusts_kmh"] if meteo else 0.0
    station_name = f"{imgw['station_name']} ({imgw['station_distance_km']} km)" if imgw else "Open-Meteo"

    plume = plume_analysis.calculate_smoke_plume(wind_dir, wind_spd, gusts_kmh=gusts)
    print(f"Stacja synoptyczna: {station_name}")
    print(f"Wiatr: {plume['wind_from']['name'].upper()} ({plume['wind_from']['code']}, {plume['wind_from']['degrees']}°), {plume['wind_from']['speed_kmh']} km/h (w porywach do {plume['wind_from']['gusts_kmh']} km/h)")
    print(f"Wektor zadymienia: sektor {plume['smoke_plume']['travel_direction_code']} ({plume['smoke_plume']['travel_direction_name']}, kąt {plume['smoke_plume']['travel_degrees']}°)")
    print(f"Stożek zagrożenia: {plume['smoke_plume']['hazard_cone_range']}")

    # 4. Zaopatrzenie wodne (OSM Overpass)
    print("\n[4/5] Poszukiwanie hydrantów i cieków wodnych (OSM)...")
    hydrants = await overpass_client.get_nearest_hydrants(geo.lat, geo.lon, radius_m=1200, max_results=3)
    sources = await overpass_client.get_water_sources(geo.lat, geo.lon, radius_m=2500, max_results=3)

    print(f"Znaleziono hydrantów w okolicy: {len(hydrants)}")
    for h in hydrants:
        warning = " [WYMAGANY STOJAK!]" if h.get("is_underground") else ""
        print(f"  • Hydrant {h['type']} {h['diameter']}: {h['distance_m']} m ({h['direction']}) -> {h['line_estimate']}{warning}")

    print(f"Znaleziono otwartych punktów czerpania wody: {len(sources)}")
    for s in sources:
        print(f"  • {s['name']} ({s['type']}): {s['distance_m']} m ({s['direction']}) -> {s['recommended_gear']}")

    # 5. Media i Zagrożenia (GESUT)
    print("\n[5/5] Analiza sieci GESUT (gaz, elektroenergetyka)...")
    utils = await kiut_client.query_utilities_gesut(geo.lat, geo.lon, radius_m=100)
    print(utils.to_tactical_summary())
    print(f"\nLink do podglądu mapy uzbrojenia terenu WMS:\n{utils.map_image_url}")


if __name__ == "__main__":
    asyncio.run(main())
