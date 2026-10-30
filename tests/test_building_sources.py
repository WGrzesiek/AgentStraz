"""Syntetyczne odpowiedzi usług: osie, geometria, brak danych i dobór budynku."""

import asyncio
import copy
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-servers/mcp-geoportal/src"))
import building_client as client
from uug_client import parse_uug_response
from tools.building_recon import enrich_report, save_reports

LAT, LON = 50.255076, 20.173021
NORTH, EAST = client.wgs84_to_puwg1992(LAT, LON)
ZIP_URL = "https://opendata.geoportal.gov.pl/InneDane/Budynki3D/LOD1/2024/12/1214.zip"


def ring(east=EAST, north=NORTH):
    return [[east-5, north-5], [east+5, north-5], [east+5, north+5], [east-5, north+5], [east-5, north-5]]


def city_gml(identifier="test", offset=0, height=6):
    points = ring(EAST+offset)
    floor = " ".join(f"{e} {n} 200" for e, n in points)
    roof = " ".join(f"{e} {n} {200+height}" for e, n in points)
    return f'''<CityModel xmlns:gml="http://www.opengis.net/gml" xmlns:bldg="http://www.opengis.net/citygml/building/2.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs,crs:EPSG::2180,crs:EPSG::9651"/></gml:boundedBy>
      <bldg:Building gml:id="{identifier}"><bldg:measuredHeight uom="meter">{height}</bldg:measuredHeight>
      <gml:Polygon><gml:exterior><gml:LinearRing><gml:posList>{floor}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>
      <gml:Polygon><gml:exterior><gml:LinearRing><gml:posList>{roof}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>
      </bldg:Building></CityModel>'''.encode()


def egib_gml():
    points = " ".join(f"{n} {e}" for e, n in ring())
    return f'''<FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ms="urn:test">
      <ms:budynki><ms:ID_BUDYNKU>test</ms:ID_BUDYNKU><ms:KONDYGNACJE_NADZIEMNE>2</ms:KONDYGNACJE_NADZIEMNE>
      <gml:Polygon srsName="urn:ogc:def:crs:EPSG::2180"><gml:exterior><gml:LinearRing>
      <gml:posList srsDimension="2">{points}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>
      </ms:budynki></FeatureCollection>'''.encode()


class TestBuildingSources(unittest.TestCase):
    def test_models_remain_available_when_service_is_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = io.BytesIO()
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("building.gml", city_gml())
            with patch.object(client, "_request", return_value=bundle.getvalue()):
                client._model_index(ZIP_URL, Path(directory))
            with patch.object(client, "_request", side_effect=OSError("offline")):
                result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=directory))
            self.assertEqual(result["status"], "selected")
            self.assertEqual(result["building"]["model_package"]["status"], "cached")
            self.assertEqual(len(result["building"]["site_plan"]["features"]), 1)
            self.assertTrue(any("nowszych paczek" in warning for warning in result["building"]["data_warnings"]))
            self.assertEqual(client._cached_model_links(Path(directory), EAST+10000, NORTH, 80), [])

    def test_uug_axes_and_address_fields(self):
        geo = parse_uug_response({"results": {"1": {"x": "583595.2", "y": "265979.11",
            "city": "Łętkowice", "number": "25", "teryt": "121406", "code": "32-107"}}}, "test")
        self.assertAlmostEqual(geo.lat, LAT, places=5)
        self.assertAlmostEqual(geo.lon, LON, places=5)
        self.assertEqual(geo.full_address, "Łętkowice, 25")
        self.assertEqual(geo.x_1992, 265979.11)
        self.assertEqual(geo.teryt_gmina, "121406")
        self.assertIsNone(parse_uug_response({"results": {"1": {}, "2": {}}}, "test"))

    def test_egib_north_east_axes_no_height_from_levels(self):
        records, truncated = client.parse_egib(egib_gml())
        area, distance, contains = client._geometry_metrics(records[0]["polygons"], (EAST, NORTH))
        self.assertEqual(area, 100)
        self.assertTrue(contains)
        self.assertEqual(distance, 0)
        self.assertFalse(truncated)
        self.assertEqual(records[0]["levels"], "2")
        self.assertIsNone(records[0]["height_m"])

    def test_citygml_east_north_axes_and_height(self):
        record, = client.parse_citygml(city_gml(), ZIP_URL)
        self.assertEqual(record["height_m"], 6)
        area, _, contains = client._geometry_metrics(record["polygons"], (EAST, NORTH))
        self.assertEqual(area, 100)
        self.assertTrue(contains)

    def test_holes_are_subtracted_and_not_inside(self):
        outer = ring()
        hole = [[EAST-1, NORTH-1], [EAST+1, NORTH-1], [EAST+1, NORTH+1], [EAST-1, NORTH+1], [EAST-1, NORTH-1]]
        area, distance, contains = client._geometry_metrics([[outer, hole]], (EAST, NORTH))
        self.assertEqual(area, 96)
        self.assertFalse(contains)
        self.assertEqual(distance, 1)

    def test_osm_height_and_multipolygon_assembly(self):
        geometry = [{"lat": LAT-0.0001, "lon": LON-0.0001}, {"lat": LAT-0.0001, "lon": LON+0.0001},
                    {"lat": LAT+0.0001, "lon": LON+0.0001}, {"lat": LAT+0.0001, "lon": LON-0.0001}]
        geometry.append(geometry[0])
        records, notes = client.parse_osm({"elements": [
            {"type": "way", "id": 1, "tags": {"building": "yes", "building:levels": "2"}, "geometry": geometry},
            {"type": "relation", "id": 2, "tags": {"building": "yes", "type": "multipolygon", "height": "7.5 m"},
             "members": [{"type": "way", "role": "outer", "geometry": geometry[:3]},
                         {"type": "way", "role": "outer", "geometry": list(reversed(geometry[2:]))}]},
        ]})
        self.assertFalse(notes)
        self.assertIsNone(records[0]["height_m"])
        self.assertEqual(records[1]["height_m"], 7.5)
        self.assertTrue(client._geometry_metrics(records[1]["polygons"], (EAST, NORTH))[2])

    def test_model_links_only_county_archives(self):
        links = client.model_links(f'<a href="{ZIP_URL}">ok</a><a href="https://evil.test/a.zip">bad</a>'
            '<a href="https://opendata.geoportal.gov.pl/InneDane/Budynki3D/LOD1/LOD1_2024.zip">country</a>'
            '<a href="https://opendata.geoportal.gov.pl/InneDane/Budynki3D/LOD2/1214_gml.zip">LoD2</a>')
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], ZIP_URL)

    def test_xml_declarations_and_wrong_crs_rejected(self):
        with self.assertRaises(ValueError):
            client.parse_egib(b'<!DOCTYPE x [<!ENTITY x "bad">]><x/>')
        with self.assertRaises(ValueError):
            list(client.parse_citygml(city_gml().replace(b"2180", b"4326"), ZIP_URL))
        with self.assertRaises(ValueError):
            client._xml('<!DOCTYPE x [<!ENTITY x "bad">]><x>&x;</x>'.encode('utf-16'))

    def test_overlapping_buildings_need_selection_and_invalid_id_is_not_used(self):
        records = [{"id": f"egib:{i}", "source": "test", "polygons": [[ring()]], "height_m": None} for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(client, "parse_egib", side_effect=lambda raw: (copy.deepcopy(records), False)), \
             patch.object(client, "_request", side_effect=lambda url, **kw: b'{"elements": []}' if "overpass" in url else b''):
            for selection in (None, "egib:unknown"):
                result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp, building_id=selection))
                self.assertEqual(result["status"], "selection_required")
                self.assertNotIn("footprint_area_m2", result["building"])
            result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp, building_id="egib:1"))
            self.assertEqual(result["building"]["id"], "egib:1")

    def test_full_sources_cache_and_reports(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("test.gml", city_gml())
        def request(url, **kwargs):
            if url == ZIP_URL:
                return archive.getvalue()
            if url.startswith(client.MODELS_URL):
                return f'<a href="{ZIP_URL}">Pobierz</a>'.encode()
            if url.startswith(client.EGIB_URL):
                return egib_gml()
            return b'{"elements": []}'
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, "_request", side_effect=request) as fetch:
            result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp))
            self.assertEqual(result["status"], "selected")
            self.assertEqual(result["building"]["volume_m3"], 600)
            self.assertEqual(result["building"]["id"], "gugik:test")
            plan = result["building"]["site_plan"]
            self.assertEqual(plan["crs"], "EPSG:2180")
            self.assertEqual(plan["selected_id"], "gugik:test")
            self.assertEqual(len(plan["features"]), 1)
            self.assertEqual(plan["features"][0]["polygons"][0][0][0], [EAST-5, NORTH-5])
            self.assertEqual(result["building"]["model_package"]["status"], "downloaded")
            self.assertEqual(len(result["source_checks"]), 3)
            # Drugi odczyt nie pobiera ZIP ponownie.
            cached = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp))
            self.assertEqual(cached["building"]["model_package"]["status"], "cached")
            self.assertEqual(sum(call.args[0] == ZIP_URL for call in fetch.call_args_list), 1)
            data = enrich_report({"incident_info": {"address": "TEST — FIKCYJNY"}}, result)
            self.assertIsNone(data["building_water"]["flow_l_s"])
            save_reports(data, tmp)
            for extension in ("html", "md"):
                report = (Path(tmp) / f"budynek.{extension}").read_text()
                self.assertIn("600.0 m³", report)
                self.assertIn("GUGiK CityGML", report)
                self.assertIn("Brak powierzchni gaszenia", report)
                self.assertIn("pobrano automatycznie i zbudowano indeks", report)
            self.assertIn('data-building-id="gugik:test"', (Path(tmp) / 'budynek.html').read_text())
            with self.assertRaises(ValueError):
                enrich_report({"incident_info": {"lat": 52, "lon": 21}}, result)

    def test_no_silent_nearest_selection_and_explicit_id(self):
        record = {"id": "egib:nearby", "source": "test", "polygons": [[ring(EAST+30)]], "height_m": None}
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, "parse_egib", return_value=([record], False)), \
             patch.object(client, "_request", side_effect=lambda url, **kw: b'{"elements": []}' if "overpass" in url else b''):
            result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp))
            self.assertEqual(result["status"], "selection_required")
            self.assertNotIn("volume_m3", result["building"])
        # Zbuduj ponownie: funkcja usuwa geometrię ze zwracanych kandydatów.
        record["polygons"] = [[ring(EAST+30)]]
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, "parse_egib", return_value=([record], False)), \
             patch.object(client, "_request", side_effect=lambda url, **kw: b'{"elements": []}' if "overpass" in url else b''):
            result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp, building_id="egib:nearby"))
            self.assertEqual(result["status"], "selected")
            self.assertIsNone(result["building"]["height_m"])

    def test_all_failures_are_not_reported_as_absent_buildings(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, "_request", side_effect=OSError("offline")):
            result = asyncio.run(client.get_building_details(LAT, LON, cache_dir=tmp))
            self.assertEqual(result["status"], "unavailable")
            self.assertTrue(all(check["status"] == "unavailable" for check in result["source_checks"]))
            self.assertNotIn("volume_m3", result["building"])


if __name__ == "__main__":
    unittest.main()
