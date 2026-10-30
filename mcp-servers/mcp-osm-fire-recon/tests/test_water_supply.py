"""
Test modułu obliczeń taktycznych zaopatrzenia wodnego.
"""

from src.water_supply import (
    haversine_distance,
    calculate_bearing,
    calculate_w75_hoses,
    parse_hydrant_data,
)


def test_haversine_and_bearing():
    # Odległość między dwoma punktami w Warszawie
    p1 = (52.2319, 21.0067)
    p2 = (52.2329, 21.0077)

    dist = haversine_distance(p1[0], p1[1], p2[0], p2[1])
    bearing = calculate_bearing(p1[0], p1[1], p2[0], p2[1])

    print(f"Dystans: {dist} m, Kierunek: {bearing}")
    assert 50 < dist < 200, f"Błędny dystans: {dist}"
    assert "północny wschód" in bearing or "NE" in bearing


def test_w75_calculation():
    # 100 metrów -> z rezerwą 15% = 115m -> 6 odcinków po 20m
    calc = calculate_w75_hoses(100.0)
    print("Kalkulacja W-75 dla 100m:", calc)
    assert calc["w75_sections_count"] == 6

    # 160 metrów -> z rezerwą 15% = 184m -> 10 odcinków po 20m
    calc2 = calculate_w75_hoses(160.0)
    print("Kalkulacja W-75 dla 160m:", calc2)
    assert calc2["w75_sections_count"] == 10


def test_hydrant_parser():
    sample_node = {
        "id": 12345,
        "lat": 52.2325,
        "lon": 21.0070,
        "tags": {
            "emergency": "fire_hydrant",
            "fire_hydrant:type": "underground",
            "fire_hydrant:diameter": "80",
            "name": "Hydrant ul. Marszałkowska",
        }
    }
    parsed = parse_hydrant_data(sample_node, 52.2319, 21.0067)
    print("Sparsowany hydrant:", parsed)
    assert parsed["is_underground"] is True
    assert "STOJAK" in parsed["equipment_required"]
    assert parsed["diameter"] == "DN80"
    print("Wszystkie testy zaopatrzenia wodnego przeszły pomyślnie!")


if __name__ == "__main__":
    test_haversine_and_bearing()
    test_w75_calculation()
    test_hydrant_parser()
