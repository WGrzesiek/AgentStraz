"""
Test podstawowy modułu transformacji współrzędnych i formatowania.
"""

from src.coords import wgs84_to_puwg1992, puwg1992_to_wgs84
from src.kiut_client import generate_kiut_map_url

def test_coords():
    # Pałac Kultury i Nauki, Warszawa (~52.2319, ~21.0067)
    lat, lon = 52.2319, 21.0067
    x_1992, y_1992 = wgs84_to_puwg1992(lat, lon)
    print(f"WGS84 ({lat}, {lon}) -> PUWG 1992: Northing={x_1992}, Easting={y_1992}")
    
    # Sprawdzenie zakresu PUWG 1992 dla Polski
    assert 400000 < x_1992 < 600000, f"Niepoprawny zakres X: {x_1992}"
    assert 550000 < y_1992 < 750000, f"Niepoprawny zakres Y: {y_1992}"

    lat_rev, lon_rev = puwg1992_to_wgs84(x_1992, y_1992)
    print(f"PUWG 1992 -> WGS84: {lat_rev}, {lon_rev}")
    assert abs(lat - lat_rev) < 0.005, f"Zbyt duży błąd szerokości: {lat} vs {lat_rev}"
    assert abs(lon - lon_rev) < 0.005, f"Zbyt duży błąd długości: {lon} vs {lon_rev}"

    map_url = generate_kiut_map_url(lat, lon, box_size_m=100)
    print(f"Przykładowy URL mapy WMS KIUT:\n{map_url[:120]}...")
    assert "REQUEST=GetMap" in map_url
    print("Testy matematyczne i generowania URL zakończone sukcesem!")

if __name__ == "__main__":
    test_coords()
