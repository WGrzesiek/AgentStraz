"""
Test modułu stacji IMGW oraz analizy wektora zadymienia.
"""

from src.stations import find_nearest_imgw_station
from src.plume_analysis import wind_deg_to_compass, calculate_smoke_plume


def test_station_matching():
    # Warszawa centrum
    st_id, st_name, dist = find_nearest_imgw_station(52.2319, 21.0067)
    print(f"Najbliższa stacja dla Warszawy: {st_name} (ID: {st_id}, odległość: {dist} km)")
    assert "Warszawa" in st_name
    assert dist < 15.0

    # Zakopane
    st_id, st_name, dist = find_nearest_imgw_station(49.2992, 19.9489)
    print(f"Najbliższa stacja dla Zakopanego: {st_name} (odległość: {dist} km)")
    assert "Zakopane" in st_name
    assert dist < 10.0


def test_compass_and_plume():
    # Wiatr z północnego zachodu (315° NW)
    code, name = wind_deg_to_compass(315)
    print(f"Kierunek 315°: {code} ({name})")
    assert code == "NW"

    plume = calculate_smoke_plume(wind_from_deg=315, wind_speed_kmh=25, gusts_kmh=45)
    print("Analiza znoszenia dymu:", plume)

    # Dym musi lecieć na południowy wschód (SE)
    assert plume["smoke_plume"]["travel_direction_code"] == "SE"
    assert "SE" in plume["smoke_plume"]["hazard_cone_range"]
    assert "PORYWY" in plume["tactical_assessment"]["gust_alert"]
    print("Wszystkie testy meteo i wektora dymu zakończone sukcesem!")


if __name__ == "__main__":
    test_station_matching()
    test_compass_and_plume()
