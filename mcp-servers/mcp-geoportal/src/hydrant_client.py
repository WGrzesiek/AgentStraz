"""Hydranty Geoportalu: K-GESUT WMS GetFeatureInfo/GML, bez klucza API."""
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

try:
    from .coords import wgs84_to_puwg1992, puwg1992_to_wgs84
except ImportError:
    from coords import wgs84_to_puwg1992, puwg1992_to_wgs84

KGESUT_URL = "https://mapy.geoportal.gov.pl/wss/geosrv/MapServer_KGESUT_WMS/wms"
SOURCE = "Geoportal / GUGiK K-GESUT — Hydranty"
FEATURE_LIMIT = 1000
NOTICE = ("Odległość w linii prostej od wskazanego ogniska pożaru; trasa rozwinięcia, "
          "typ, DN, dostępność, sprawność i wydajność wymagają potwierdzenia w terenie. "
          "Brak wyników nie oznacza braku hydrantów.")


def query_params(lat, lon, radius_m):
    if not all(math.isfinite(v) for v in (lat, lon, radius_m)):
        raise ValueError("Współrzędne i promień muszą być skończone.")
    if not (-90 < lat < 90 and -180 <= lon <= 180 and 10 <= radius_m <= 3000):
        raise ValueError("Podaj poprawny GPS i promień 10–3000 m.")
    north, east = wgs84_to_puwg1992(lat, lon)
    # WMS 1.3 EPSG:2180: N,E. GML Box EPSG:2180 zwraca E,N!
    # Obraz 3x3, tolerancja kliknięcia MapServer obejmuje obszar poszukiwań.
    # MAP_RESOLUTION=1 utrzymuje skalę poniżej MaxScaleDenominator=100000.
    # Serwer może zwrócić punkty spoza BBOX: obowiązkowy filtr geodezyjny.
    return dict(SERVICE="WMS", VERSION="1.3.0", REQUEST="GetFeatureInfo",
                LAYERS="hydranty", QUERY_LAYERS="hydranty", STYLES="",
                CRS="EPSG:2180", BBOX=f"{north-radius_m},{east-radius_m},{north+radius_m},{east+radius_m}",
                WIDTH=3, HEIGHT=3, I=1, J=1, MAP_RESOLUTION=1,
                FORMAT="image/png", INFO_FORMAT="application/vnd.ogc.gml", FEATURE_COUNT=FEATURE_LIMIT)


def distance_bearing(lat, lon, target_lat, target_lon):
    p1, p2 = map(math.radians, (lat, target_lat))
    dl = math.radians(target_lon-lon)
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    distance = 6371008.8 * 2 * math.asin(min(1, math.sqrt(a)))
    bearing = math.degrees(math.atan2(math.sin(dl)*math.cos(p2),
        math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl))) % 360
    return distance, bearing


def parse_hydrants(content, lat, lon, radius_m):
    root = ET.fromstring(content)
    if root.tag.split('}')[-1] != 'msGMLOutput':
        raise ValueError("Usługa nie zwróciła odpowiedzi GML K-GESUT.")
    features = [el for el in root.iter() if el.tag.split('}')[-1] == 'hydranty_feature']
    points, seen, rejected = [], set(), 0
    for feature in features:
        fields = {el.tag.split('}')[-1].lower(): (el.text or '').strip() for el in feature}
        try:
            box = feature.find('.//{http://www.opengis.net/gml}Box')
            if box is None or box.get('srsName') != 'EPSG:2180':
                raise ValueError("Nieobsługiwany CRS")
            coords = box.find('{http://www.opengis.net/gml}coordinates').text.split()
            corners = [tuple(map(float, pair.split(','))) for pair in coords]
            if len(corners) != 2 or corners[0] != corners[1] or len(corners[0]) != 2:
                raise ValueError("Brak jednoznacznej geometrii punktowej")
            east, north = corners[0]
            if not all(math.isfinite(v) for v in (east, north)):
                raise ValueError("Niepoprawna geometria")
            target_lat, target_lon = puwg1992_to_wgs84(north, east)
            distance, bearing = distance_bearing(lat, lon, target_lat, target_lon)
            key = fields.get('id_iip') or fields.get('id') or str(corners[0])
            if key in seen or distance > radius_m:
                continue
            seen.add(key)
            direction = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][int((bearing+22.5)//45) % 8]
            points.append(dict(id=fields.get('id') or key, source_id=key, lat=target_lat, lon=target_lon,
                distance_m=distance, distance_basis="straight_line", bearing_deg=round(bearing, 1),
                direction=direction, type="nieznany", diameter="DN nieznane",
                requires_standpipe_and_key=None, operational_status="niepotwierdzony",
                estimated_w75_hoses=max(1, math.ceil(distance*1.15/20)),
                source=SOURCE, source_url=KGESUT_URL, source_date=fields.get('data') or None,
                location_desc=f"{direction} od ogniska; GPS {target_lat}, {target_lon}"))
        except (ValueError, AttributeError, TypeError):
            rejected += 1
    points.sort(key=lambda p: (p['distance_m'], p['id']))
    for point in points:
        point['distance_m'] = round(point['distance_m'], 1)
    return points, len(features) >= FEATURE_LIMIT or rejected > 0


async def get_hydrants_near_point(lat, lon, radius_m=500, *, timeout_sec=20):
    params = query_params(lat, lon, radius_m)
    result = dict(source=SOURCE, source_url=KGESUT_URL,
                  retrieved_at=datetime.now(timezone.utc).isoformat(),
                  origin={"lat": lat, "lon": lon}, radius_m=radius_m,
                  notice=NOTICE, hydrants=[], nearest_hydrant=None)
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            response = await client.get(KGESUT_URL, params=params)
            response.raise_for_status()
        points, partial = parse_hydrants(response.content, lat, lon, radius_m)
        result.update(status="partial" if partial else ("ok" if points else "no_data"), hydrants=points,
                      nearest_hydrant=points[0] if points else None)
        if partial:
            result['notice'] += " Wynik niepełny: najbliższy wyłącznie spośród odczytanych punktów."
    except (httpx.HTTPError, ET.ParseError, ValueError) as error:
        result.update(status="unavailable", error=str(error))
    result['query_url'] = KGESUT_URL + '?' + urlencode(params)
    return result
