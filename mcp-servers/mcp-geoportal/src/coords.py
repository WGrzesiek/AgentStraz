"""
Moduł transformacji układów współrzędnych:
WGS84 (EPSG:4326 - GPS, Lat/Lon) <-> PUWG 1992 (EPSG:2180 - Państwowy Układ Współrzędnych Geodezyjnych 1992).

Polskie rejestry geodezyjne (GUGiK, ULDK, GESUT, PRG) operują w układzie PUWG 1992 (EPSG:2180).
"""

import math
from typing import Tuple

try:
    from pyproj import Transformer
    _TRANSFORMER_4326_TO_2180 = Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
    _TRANSFORMER_2180_TO_4326 = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True)
    _HAS_PYPROJ = True
except ImportError:
    _HAS_PYPROJ = False


def wgs84_to_puwg1992(lat: float, lon: float) -> Tuple[float, float]:
    """
    Przelicza współrzędne WGS84 (szerokość i długość geograficzna) na układ PUWG 1992 (x, y w metrach).
    Uwaga: w geodezji polskiej X to oś północna (Northing), Y to oś wschodnia (Easting).
    Zwraca: (x_1992, y_1992) gdzie x to Northing, y to Easting.
    """
    if _HAS_PYPROJ:
        easting, northing = _TRANSFORMER_4326_TO_2180.transform(lon, lat)
        return round(northing, 2), round(easting, 2)

    # Parametry elipsoidy GRS80
    a = 6378137.0
    e2 = 0.00669438002290
    m0 = 0.9993  # skala w południku 19°
    l0 = math.radians(19.0)

    phi = math.radians(lat)
    lam = math.radians(lon)

    delta_lam = lam - l0

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    N = a / math.sqrt(1 - e2 * sin_phi**2)
    t = tan_phi**2
    eta2 = (e2 / (1 - e2)) * cos_phi**2

    A0 = 1 - e2/4 - 3*e2**2/64 - 5*e2**3/256
    A2 = 3/8 * (e2 + e2**2/4 + 15*e2**3/128)
    A4 = 15/256 * (e2**2 + 3*e2**3/4)
    A6 = 35*e2**3 / 3072

    S = a * (A0 * phi - A2 * math.sin(2*phi) + A4 * math.sin(4*phi) - A6 * math.sin(6*phi))

    x_gk = S + N * tan_phi * (
        (delta_lam**2 / 2) * cos_phi**2 +
        (delta_lam**4 / 24) * cos_phi**4 * (5 - t + 9 * eta2 + 4 * eta2**2) +
        (delta_lam**6 / 720) * cos_phi**6 * (61 - 58 * t + t**2)
    )

    y_gk = N * (
        delta_lam * cos_phi +
        (delta_lam**3 / 6) * cos_phi**3 * (1 - t + eta2) +
        (delta_lam**5 / 120) * cos_phi**5 * (5 - 18 * t + t**2 + 14 * eta2 - 58 * t * eta2)
    )

    x_1992 = x_gk * m0 - 5300000.0
    y_1992 = y_gk * m0 + 500000.0

    return round(x_1992, 2), round(y_1992, 2)


def puwg1992_to_wgs84(x_1992: float, y_1992: float) -> Tuple[float, float]:
    """
    Przelicza układ PUWG 1992 (x: Northing, y: Easting) na WGS84 (lat, lon).
    Zwraca: (lat, lon)
    """
    if _HAS_PYPROJ:
        lon, lat = _TRANSFORMER_2180_TO_4326.transform(y_1992, x_1992)
        return round(lat, 6), round(lon, 6)

    # Elipsoida GRS80
    a = 6378137.0
    e2 = 0.00669438002290
    m0 = 0.9993
    l0 = math.radians(19.0)

    x_gk = (x_1992 + 5300000.0) / m0
    y_gk = (y_1992 - 500000.0) / m0

    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    # Obliczenie szerokości punktu rzutu (Footpoint latitude)
    M = x_gk
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))

    phi_f = (
        mu +
        (3*e1/2 - 27*e1**3/32) * math.sin(2*mu) +
        (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu) +
        (151*e1**3/96) * math.sin(6*mu) +
        (1097*e1**4/512) * math.sin(8*mu)
    )

    sin_f = math.sin(phi_f)
    cos_f = math.cos(phi_f)
    tan_f = math.tan(phi_f)

    N_f = a / math.sqrt(1 - e2 * sin_f**2)
    R_f = a * (1 - e2) / math.pow(1 - e2 * sin_f**2, 1.5)
    D = y_gk / N_f

    eta_f2 = (e2 / (1 - e2)) * cos_f**2
    t_f = tan_f**2

    phi = phi_f - (N_f * tan_f / R_f) * (
        D**2 / 2 -
        (5 + 3*t_f + 10*eta_f2 - 4*eta_f2**2 - 9*e2/(1-e2)) * D**4 / 24 +
        (61 + 90*t_f + 298*eta_f2 + 45*t_f**2 - 252*e2/(1-e2) - 3*eta_f2**2) * D**6 / 720
    )

    lam = l0 + (1 / cos_f) * (
        D -
        (1 + 2*t_f + eta_f2) * D**3 / 6 +
        (5 - 2*eta_f2 + 28*t_f - 3*eta_f2**2 + 8*e2/(1-e2) + 24*t_f**2) * D**5 / 120
    )

    return round(math.degrees(phi), 6), round(math.degrees(lam), 6)
