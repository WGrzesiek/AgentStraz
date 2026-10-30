"""
Baza współrzędnych stacji synoptycznych IMGW-PIB w Polsce.
Umożliwia szybkie dopasowanie najbliższej stacji pomiarowej do współrzędnych akcji.
"""

import math
from typing import Dict, Tuple

# Współrzędne (lat, lon) głównych stacji synoptycznych IMGW w Polsce
IMGW_SYNOP_STATIONS: Dict[str, Tuple[float, float, str]] = {
    # id_stacji: (lat, lon, nazwa)
    "12100": (54.18, 16.18, "Kołobrzeg"),
    "12105": (54.20, 15.58, "Koszalin"),
    "12115": (54.47, 16.68, "Ustka"),
    "12120": (54.60, 18.35, "Łeba"),
    "12125": (54.60, 18.80, "Hel"),
    "12135": (54.38, 18.60, "Gdańsk"),
    "12155": (53.78, 20.48, "Olsztyn"),
    "12160": (54.03, 21.77, "Mikołajki"),
    "12185": (54.10, 22.93, "Suwałki"),
    "12205": (53.40, 14.62, "Szczecin"),
    "12210": (53.30, 15.05, "Stargard"),
    "12235": (53.13, 17.97, "Chojnice"),
    "12250": (53.12, 18.00, "Toruń"),
    "12270": (53.10, 22.05, "Mława"),
    "12285": (53.13, 23.17, "Białystok"),
    "12300": (52.73, 15.23, "Gorzów Wielkopolski"),
    "12310": (52.40, 16.83, "Poznań"),
    "12330": (52.42, 19.05, "Płock"),
    "12345": (52.20, 20.98, "Warszawa-Okęcie"),
    "12360": (52.17, 22.28, "Siedlce"),
    "12375": (52.03, 23.13, "Terespol"),
    "12385": (51.93, 15.53, "Zielona Góra"),
    "12400": (51.77, 18.08, "Kalisz"),
    "12415": (51.73, 19.40, "Łódź"),
    "12424": (51.42, 21.15, "Radom"),
    "12435": (51.25, 22.57, "Lublin"),
    "12455": (51.10, 17.03, "Wrocław"),
    "12465": (50.67, 17.93, "Opole"),
    "12485": (50.80, 19.10, "Częstochowa"),
    "12495": (50.87, 20.63, "Kielce"),
    "12500": (50.90, 15.73, "Jelenia Góra"),
    "12510": (50.73, 16.30, "Kłodzko"),
    "12520": (50.23, 19.03, "Katowice"),
    "12530": (50.08, 19.80, "Kraków-Balice"),
    "12540": (50.07, 21.98, "Tarnów"),
    "12560": (50.03, 22.00, "Rzeszów-Jasionka"),
    "12570": (50.57, 23.27, "Zamość"),
    "12600": (49.80, 19.05, "Bielsko-Biała"),
    "12625": (49.63, 20.70, "Nowy Sącz"),
    "12650": (49.68, 21.77, "Krosno"),
    "12660": (49.78, 22.77, "Przemyśl"),
    "12670": (49.30, 19.95, "Zakopane"),
}


def find_nearest_imgw_station(lat: float, lon: float) -> Tuple[str, str, float]:
    """
    Znajduje najbliższą stację synoptyczną IMGW dla zadanych współrzędnych.
    Zwraca: (id_stacji, nazwa_stacji, odległość_w_km)
    """
    best_id = "12345"
    best_name = "Warszawa-Okęcie"
    min_dist_km = float("inf")

    for st_id, (st_lat, st_lon, st_name) in IMGW_SYNOP_STATIONS.items():
        # Uproszczona odległość euklidesowa z wagą szerokości geograficznej
        d_lat = (st_lat - lat) * 111.0
        d_lon = (st_lon - lon) * 111.0 * math.cos(math.radians(lat))
        dist_km = math.sqrt(d_lat**2 + d_lon**2)

        if dist_km < min_dist_km:
            min_dist_km = dist_km
            best_id = st_id
            best_name = st_name

    return best_id, best_name, round(min_dist_km, 1)
