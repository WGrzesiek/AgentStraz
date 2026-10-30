"""Bezpłatne obrysy EGiB, CityGML GUGiK i OSM; bez kluczy i zgadywania wysokości."""

import asyncio
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

try:
    from .coords import wgs84_to_puwg1992, puwg1992_to_wgs84
except ImportError:
    from coords import wgs84_to_puwg1992, puwg1992_to_wgs84

EGIB_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/EGIB/WFS/UslugaZbiorcza"
MODELS_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/FOTO/WMS/ModeleBudynkow3D"
OVERPASS_URLS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
CACHE_TTL = 7 * 86400
MAX_ZIP = 128 * 1024 * 1024
GML = "{http://www.opengis.net/gml}"
BLDG = "{http://www.opengis.net/citygml/building/2.0}"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _request(url, *, data=None, limit=4 * 1024 * 1024, timeout=20):
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "AgentStraz/1.0 (building reconnaissance)",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Odpowiedź przekracza limit rozmiaru.")
    return content


class _NoDTD(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("Niedozwolona deklaracja DTD.")


def _xml(raw):
    # Zewnętrzne dokumenty nie mogą deklarować encji ani DTD.
    if b"<!doctype" in raw.lower() or b"<!entity" in raw.lower():
        raise ValueError("Niedozwolona deklaracja XML.")
    root = ET.fromstring(raw, parser=ET.XMLParser(target=_NoDTD()))
    if root.tag.rsplit("}", 1)[-1] in ("ExceptionReport", "ServiceExceptionReport"):
        raise ValueError("Usługa zwróciła wyjątek OGC.")
    return root


def _text(node, local):
    return next((el.text.strip() for el in node.iter()
                 if el.tag.rsplit("}", 1)[-1] == local and el.text), None)


def _ring_area(ring):
    # Przesunięcie do początku układu ogranicza utratę precyzji.
    x0, y0 = ring[0][:2]
    return abs(sum((a[0]-x0)*(b[1]-y0) - (b[0]-x0)*(a[1]-y0)
                   for a, b in zip(ring, ring[1:]))) / 2


def _inside(point, ring):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def _segment_distance(point, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx + dy*dy
    t = max(0, min(1, ((point[0]-a[0])*dx + (point[1]-a[1])*dy)/length2)) if length2 else 0
    return math.hypot(point[0]-a[0]-t*dx, point[1]-a[1]-t*dy)


def _geometry_metrics(polygons, point):
    area, distance, contains = 0, math.inf, False
    for polygon in polygons:
        outer, *holes = polygon
        area += _ring_area(outer) - sum(_ring_area(hole) for hole in holes)
        contains |= _inside(point, outer) and not any(_inside(point, hole) for hole in holes)
        for ring in polygon:
            distance = min(distance, *(_segment_distance(point, a, b) for a, b in zip(ring, ring[1:])))
    return area, 0.0 if contains else distance, contains


def _polygon(element, *, dimension=2, swap=False):
    rings = []
    for boundary in element:
        if boundary.tag.rsplit("}", 1)[-1] not in ("exterior", "interior", "outerBoundaryIs", "innerBoundaryIs"):
            continue
        pos = next((x for x in boundary.iter() if x.tag.rsplit("}", 1)[-1] == "posList"), None)
        if pos is None or not pos.text:
            continue
        dim = int(pos.get("srsDimension", dimension))
        values = [float(x) for x in pos.text.split()]
        if dim not in (2, 3) or len(values) % dim or not all(math.isfinite(v) for v in values):
            raise ValueError("Nieprawidłowe współrzędne GML.")
        ring = [values[i:i+dim] for i in range(0, len(values), dim)]
        if swap:
            ring = [[p[1], p[0], *p[2:]] for p in ring]
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("Niezamknięty obrys budynku.")
        rings.append(ring)
    return rings


def parse_egib(raw):
    root = _xml(raw)
    buildings = []
    for feature in root.iter():
        if feature.tag.rsplit("}", 1)[-1] != "budynki":
            continue
        polygons = []
        for poly in feature.iter():
            if poly.tag.rsplit("}", 1)[-1] != "Polygon":
                continue
            # WFS 2.0 EPSG:2180: osie N,E; jawne żądanie tego CRS.
            if "2180" not in poly.get("srsName", "urn:ogc:def:crs:EPSG::2180"):
                raise ValueError("Nieobsługiwany CRS EGiB.")
            rings = _polygon(poly, swap=True)
            if rings:
                polygons.append(rings)
        if polygons:
            buildings.append({
                "id": "egib:" + (_text(feature, "ID_BUDYNKU") or feature.get("{http://www.opengis.net/gml/3.2}id", "")),
                "source": "GUGiK EGiB WFS", "source_url": EGIB_URL,
                "polygons": polygons, "height_m": None,
                "building_type": _text(feature, "RODZAJ"),
                "levels": _text(feature, "KONDYGNACJE_NADZIEMNE"),
                "observed_at": None,
            })
    return buildings, bool(root.get("next"))


def _height(value):
    if value is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(m|meter|metre)?\s*", str(value))
    height = float(match[1]) if match else None
    return height if height is not None and math.isfinite(height) and height > 0 else None


def parse_osm(data):
    buildings, warnings = [], []
    for feature in data.get("elements", []):
        tags = feature.get("tags", {})
        if not tags.get("building") or tags.get("building") == "no":
            continue
        try:
            if feature.get("type") == "way":
                polygons = [[_osm_ring(feature.get("geometry", []))]]
            elif feature.get("type") == "relation" and tags.get("type") == "multipolygon":
                polygons = [[ring] for ring in _osm_member_rings(feature, "outer")]
                for hole in _osm_member_rings(feature, "inner"):
                    owners = [poly for poly in polygons if _inside(hole[0], poly[0])]
                    if len(owners) != 1:
                        raise ValueError("Nieprzypisany otwór OSM.")
                    owners[0].append(hole)
                if not polygons:
                    continue
            else:
                continue
        except (ValueError, KeyError):
            warnings.append(f"OSM: pominięto niepełny obrys {feature.get('id')}.")
            continue
        height = _height(tags.get("height"))
        if tags.get("min_height") not in (None, "0", "0.0"):
            height = None  # Bryła na podporach nie jest pełnym graniastosłupem.
        buildings.append({
            "id": f"osm:{feature['type']}/{feature['id']}", "source": "OpenStreetMap contributors (ODbL)",
            "source_url": f"https://www.openstreetmap.org/{feature['type']}/{feature['id']}",
            "polygons": polygons, "height_m": height, "levels": tags.get("building:levels"),
            "height_source": tags.get("source:height"), "building_type": tags.get("building"),
            "observed_at": feature.get("timestamp"),
        })
    return buildings, warnings


def _osm_ring(geometry):
    if len(geometry) < 4 or geometry[0] != geometry[-1]:
        raise ValueError("Niezamknięty obrys OSM.")
    ring = []
    for point in geometry:
        north, east = wgs84_to_puwg1992(point["lat"], point["lon"])
        if not all(math.isfinite(v) for v in (north, east)):
            raise ValueError("Nieprawidłowa geometria OSM.")
        ring.append([east, north])
    return ring


def _osm_member_rings(feature, role):
    segments = [list(m.get("geometry", [])) for m in feature.get("members", [])
                if m.get("role", "outer") == role and m.get("type") == "way"]
    rings = []
    while segments:
        chain = segments.pop(0)
        if not chain:
            raise ValueError("Brak geometrii członu OSM.")
        while chain[-1] != chain[0]:
            for i, segment in enumerate(segments):
                if not segment:
                    raise ValueError("Brak geometrii członu OSM.")
                if chain[-1] == segment[0]:
                    chain.extend(segment[1:])
                elif chain[-1] == segment[-1]:
                    chain.extend(list(reversed(segment))[1:])
                else:
                    continue
                segments.pop(i)
                break
            else:
                raise ValueError("Niekompletna relacja OSM.")
        rings.append(_osm_ring(chain))
    return rings


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")
        # Tylko oficjalne paczki powiatowe; nigdy ZIP dla całego kraju.
        if tag == "a" and re.fullmatch(r"https://opendata\.geoportal\.gov\.pl/InneDane/Budynki3D/[^?#]+/\d{4}(?:_gml)?\.zip", href):
            self.urls.append(href)


def model_links(html):
    parser = _Links()
    parser.feed(html)
    return sorted(set(parser.urls), key=lambda u: ("/LOD1/" in u.upper(), u), reverse=True)


def parse_citygml(raw, source_url):
    root = _xml(raw)
    envelope = root.find(f".//{GML}Envelope")
    if envelope is None or "2180" not in envelope.get("srsName", ""):
        raise ValueError("Nieobsługiwany CRS CityGML — wymagany EPSG:2180.")
    for building in root.iter(BLDG + "Building"):
        # W publikacji CityGML GUGiK współrzędne są zapisane jako E,N,Z.
        polygons = []
        for poly in building.iter(GML + "Polygon"):
            rings = _polygon(poly, dimension=3)
            if rings and len(rings[0][0]) == 3:
                polygons.append(rings)
        if not polygons:
            continue
        zmin = min(p[2] for poly in polygons for p in poly[0])
        zmax = max(p[2] for poly in polygons for p in poly[0])
        ground = [poly for poly in polygons if all(abs(p[2]-zmin) < 0.02 for p in poly[0])]
        if not ground:
            continue
        attrs = {el.get("name"): _text(el, "value") for el in building if el.get("name")}
        height = _height(_text(building, "measuredHeight")) or (zmax-zmin if zmax > zmin else None)
        yield {
            "id": "gugik:" + building.get(GML + "id", attrs.get("buildingId", "")),
            "source": "GUGiK CityGML " + ("LoD1" if "/LOD1/" in source_url.upper() else "LoD2"),
            "source_url": source_url, "polygons": ground, "height_m": height,
            "observed_at": attrs.get("aktZrodla"), "building_id_bdot": attrs.get("buildingId"),
            "height_method": "measuredHeight" if _height(_text(building, "measuredHeight")) else "różnica Z modelu",
        }


def _model_index(url, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    database = cache_dir / (key + ".sqlite")
    archive = cache_dir / (key + ".zip")
    package = {"url": url, "county_code": re.search(r"/(\d{4})(?:_gml)?\.zip$", url)[1]}
    if database.exists() and time.time() - database.stat().st_mtime < CACHE_TTL:
        package.update(status="cached", indexed_at=datetime.fromtimestamp(database.stat().st_mtime, timezone.utc).isoformat())
        return database, package
    package["status"] = "indexed_from_cache"
    if not archive.exists() or time.time() - archive.stat().st_mtime >= CACHE_TTL:
        raw = _request(url, limit=MAX_ZIP, timeout=45)
        with tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as handle:
            handle.write(raw)
            temporary = Path(handle.name)
        temporary.replace(archive)
        package["status"] = "downloaded"
    handle, temporary = tempfile.mkstemp(dir=cache_dir, suffix=".sqlite")
    os.close(handle)
    try:
        with sqlite3.connect(temporary) as db, zipfile.ZipFile(archive) as bundle:
            db.execute("CREATE TABLE buildings (minx REAL,miny REAL,maxx REAL,maxy REAL,data TEXT)")
            files = [x for x in bundle.infolist() if x.filename.lower().endswith((".gml", ".xml"))]
            if sum(x.file_size for x in files) > 512 * 1024 * 1024:
                raise ValueError("Paczka po rozpakowaniu przekracza limit 512 MiB.")
            for member in files:
                if member.file_size > 32 * 1024 * 1024:
                    raise ValueError("Plik CityGML przekracza limit 32 MiB.")
                for record in parse_citygml(bundle.read(member), url):
                    points = [p for poly in record["polygons"] for p in poly[0]]
                    db.execute("INSERT INTO buildings VALUES (?,?,?,?,?)", (
                        min(p[0] for p in points), min(p[1] for p in points),
                        max(p[0] for p in points), max(p[1] for p in points), json.dumps(record),
                    ))
            db.execute("CREATE INDEX bounds ON buildings(minx,maxx,miny,maxy)")
        Path(temporary).replace(database)
    finally:
        Path(temporary).unlink(missing_ok=True)
    package["indexed_at"] = datetime.fromtimestamp(database.stat().st_mtime, timezone.utc).isoformat()
    return database, package


def _nearby_models(url, cache_dir, east, north, radius):
    database, package = _model_index(url, cache_dir)
    with sqlite3.connect(database) as db:
        rows = db.execute("SELECT data FROM buildings WHERE minx<=? AND maxx>=? AND miny<=? AND maxy>=?",
                          (east+radius, east-radius, north+radius, north-radius))
        records = [json.loads(row[0]) for row in rows]
        for record in records:
            record["model_cached_at"] = datetime.fromtimestamp(database.stat().st_mtime, timezone.utc).isoformat()
            record["model_package"] = package
        return records


def _cached_model_links(cache_dir, east, north, radius):
    """Odtwórz linki tylko ze świeżych indeksów obejmujących szukany punkt."""
    urls = set()
    for database in cache_dir.glob("*.sqlite"):
        if time.time() - database.stat().st_mtime >= CACHE_TTL:
            continue
        try:
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                rows = db.execute("SELECT data FROM buildings WHERE minx<=? AND maxx>=? AND miny<=? AND maxy>=?",
                                  (east+radius, east-radius, north+radius, north-radius))
                for row in rows:
                    url = json.loads(row[0]).get("source_url", "")
                    if hashlib.sha256(url.encode()).hexdigest()[:24] == database.stem:
                        urls.update(model_links('<a href="' + url + '">model</a>'))
        except (sqlite3.Error, ValueError, OSError):
            continue
    return sorted(urls, reverse=True)


async def get_building_details(lat, lon, *, building_id=None, cache_dir=None):
    """Adresowy punkt musi leżeć w jednym obrysie; przy niejednoznaczności wybierz id.

    Wynik building jest gotowy do generate_kdr_reports/render_html. Kandydatów
    z różnych rejestrów nie łączymy przez samą odległość ani nie sumujemy kubatur.
    """
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lat, lon)):
        raise ValueError("Wymagane skończone współrzędne WGS84.")
    if not (48.9 <= lat <= 55.1 and 14 <= lon <= 24.2):
        raise ValueError("Źródła budynków obsługują obszar Polski.")
    north, east = wgs84_to_puwg1992(lat, lon)
    radius = 80
    retrieved = utc_now()
    cache_dir = Path(cache_dir or os.environ.get("BUILDING_CACHE_DIR") or Path(__file__).resolve().parents[3] / "reports/cache/buildings")
    records, checks, warnings, links = [], [], [], []

    async def egib():
        params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": "ms:budynki",
                  "SRSNAME": "urn:ogc:def:crs:EPSG::2180", "COUNT": 200,
                  "BBOX": f"{north-radius},{east-radius},{north+radius},{east+radius},urn:ogc:def:crs:EPSG::2180"}
        raw = await asyncio.to_thread(_request, EGIB_URL + "?" + urllib.parse.urlencode(params))
        result, truncated = parse_egib(raw)
        if truncated:
            warnings.append("EGiB: lista kandydatów ucięta; wybór wymaga potwierdzenia id.")
            for record in result:
                record["truncated"] = True
        return result

    async def osm():
        query = f'[out:json][timeout:15];(way["building"](around:{radius},{lat},{lon});relation["building"](around:{radius},{lat},{lon}););out meta geom;'
        for endpoint in OVERPASS_URLS:
            try:
                raw = await asyncio.to_thread(_request, endpoint, data=urllib.parse.urlencode({"data": query}).encode())
                data = json.loads(raw)
                if data.get("remark"):
                    raise ValueError("Overpass zwrócił niepełne dane.")
                result, notes = parse_osm(data)
                warnings.extend(notes)
                return result
            except (OSError, ValueError):
                continue
        raise ValueError("Usługi Overpass nie zwróciły pełnych danych.")

    async def models():
        # Zapytanie do grupy LoD1 zwraca dostępne roczniki; LoD2 jest zapasowy.
        params = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo",
                  "LAYERS": "LoD1,Modele_3D_budynkow_LoD2_2017", "QUERY_LAYERS": "LoD1,Modele_3D_budynkow_LoD2_2017",
                  "SRS": "EPSG:2180", "BBOX": f"{east-100},{north-100},{east+100},{north+100}",
                  "WIDTH": 101, "HEIGHT": 101, "X": 50, "Y": 50,
                  "INFO_FORMAT": "text/html", "FORMAT": "image/png", "FEATURE_COUNT": 20}
        try:
            raw = await asyncio.to_thread(_request, MODELS_URL + "?" + urllib.parse.urlencode(params))
            if raw.lstrip().startswith(b"<?xml"):
                _xml(raw)  # OGC ServiceException nie oznacza braku modeli.
            urls = model_links(raw.decode("utf-8"))
        except (OSError, ValueError):
            urls = await asyncio.to_thread(_cached_model_links, cache_dir.resolve(), east, north, radius)
            if not urls:
                raise
            warnings.append("Indeks usług GUGiK niedostępny; użyto lokalnych modeli. Dostępności nowszych paczek nie potwierdzono.")
        links.extend(urls)
        successful = False
        for url in urls:
            try:
                found = await asyncio.to_thread(_nearby_models, url, cache_dir, east, north, radius)
                successful = True
                if found:
                    return found
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, sqlite3.Error) as error:
                warnings.append(f"Modele 3D: {type(error).__name__} dla {url}.")
        if urls and not successful:
            raise ValueError("Nie udało się przetworzyć żadnej paczki modeli 3D; szczegóły w ostrzeżeniach.")
        return []

    results = await asyncio.gather(models(), egib(), osm(), return_exceptions=True)
    for name, result in zip(("GUGiK CityGML", "GUGiK EGiB", "OSM Overpass"), results):
        if isinstance(result, Exception):
            checks.append({"source": name, "status": "unavailable", "error": str(result), "retrieved_at": retrieved})
        else:
            records.extend(result)
            checks.append({"source": name, "status": "ok" if result else "no_data", "count": len(result), "retrieved_at": retrieved})
    candidates = []
    for record in records:
        area, distance, contains = _geometry_metrics(record["polygons"], (east, north))
        if area <= 0 or distance > radius:
            continue
        record.update(footprint_area_m2=round(area, 2), distance_m=round(distance, 2), contains_point=contains,
                      retrieved_at=retrieved)
        if record.get("height_m"):
            record["volume_m3"] = round(area * record["height_m"], 2)
        candidates.append(record)
    candidates.sort(key=lambda x: x["distance_m"])
    selected = None
    if building_id:
        selected = next((r for r in candidates if r["id"] == building_id), None)
        if selected is None:
            warnings.append("Wybrane id nie występuje wśród pobranych kandydatów.")
    else:
        for prefix in ("gugik:", "egib:", "osm:"):
            matches = [r for r in candidates if r["id"].startswith(prefix) and r["contains_point"]]
            if matches:
                if len(matches) == 1 and not matches[0].get("truncated"):
                    selected = matches[0]
                break
    building = dict(selected) if selected else {}
    building.pop("polygons", None)
    # Jeden rejestr na szkicu: unikamy dublowania tego samego budynku z EGiB/OSM.
    prefix = selected["id"].split(":", 1)[0] + ":" if selected else next(
        (prefix for prefix in ("gugik:", "egib:", "osm:") if any(r["id"].startswith(prefix) for r in candidates)), None)
    sketch_records = [r for r in candidates if prefix and r["id"].startswith(prefix)]
    if not building.get("model_package"):
        package = next((r["model_package"] for r in candidates if r.get("model_package")), None)
        if package:
            building["model_package"] = package
    building["site_plan"] = {
        "crs": "EPSG:2180", "origin_easting": east, "origin_northing": north,
        "radius_m": radius, "selected_id": selected["id"] if selected else None,
        "features": [{key: record.get(key) for key in
                      ("id", "source", "source_url", "observed_at", "height_m", "footprint_area_m2")}
                     | {"polygons": [[[point[:2] for point in ring] for ring in poly] for poly in record["polygons"]]}
                     for record in sketch_records],
    }
    warnings.append("Kubatura dotyczy uproszczonej bryły zewnętrznej; nie określa powierzchni gaszenia ani kubatury wewnętrznej.")
    if not selected:
        warnings.append("Nie wybrano budynku automatycznie. Potwierdź obiekt i podaj building_id; najbliższy budynek może mieć inny adres.")
    elif selected.get("height_m") is None:
        warnings.append("Brak wysokości. Liczba kondygnacji nie została przeliczona na metry.")
    building.update(recon_status="selected" if selected else "selection_required" if candidates else "unavailable",
                    data_warnings=warnings, source_checks=checks, retrieved_at=retrieved)
    if not selected:
        building["candidate_summary"] = [f"{r['id']}: {r['source']}, {r['distance_m']} m od punktu" for r in candidates[:10]]
    for candidate in candidates:
        candidate.pop("polygons", None)
    return {"success": bool(selected), "status": "selected" if selected else "selection_required" if candidates else "unavailable",
            "coordinates": {"lat": lat, "lon": lon}, "building": building,
            "candidates": candidates, "source_checks": checks, "model_download_urls": links,
            "warnings": warnings, "retrieved_at": retrieved}
