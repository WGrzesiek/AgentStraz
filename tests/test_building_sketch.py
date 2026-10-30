import copy
import unittest

from tools.building_sketch import render_building_sketch
from tools.visualizer import render_html


class TestBuildingSketch(unittest.TestCase):
    def setUp(self):
        self.building = {"site_plan": {
            "crs": "EPSG:2180", "origin_easting": 500000, "origin_northing": 300000,
            "radius_m": 80, "selected_id": "gugik:test",
            "features": [{"id": "gugik:test", "source": "TEST — DANE FIKCYJNE", "height_m": 6,
                          "footprint_area_m2": 100,
                          "polygons": [[[[499995, 299995], [500005, 299995], [500005, 300005], [499995, 300005], [499995, 299995]]]]}],
        }}

    def test_metric_scale_north_selected_and_holes(self):
        self.building['site_plan']['features'][0]['polygons'][0].append(
            [[499999, 299999], [500001, 299999], [500001, 300001], [499999, 300001], [499999, 299999]])
        original = copy.deepcopy(self.building)
        svg = render_building_sketch(self.building)
        self.assertIn('M275.00,305.00 L305.00,305.00 L305.00,275.00', svg)
        self.assertIn('M287.00,293.00', svg)
        self.assertIn('fill-rule="evenodd"', svg)
        self.assertIn('fill="#b91c1c"', svg)
        self.assertIn('B1 — analizowany', svg)
        self.assertIn('6.00 m', svg)
        self.assertIn('>25 m<', svg)
        self.assertEqual(self.building, original)

    def test_external_identifiers_escaped_once_in_html(self):
        feature = self.building['site_plan']['features'][0]
        feature['id'] = '<script>alert(1)</script>'
        feature['source'] = '<img src=x onerror=alert(1)>'
        html = render_html({'building': self.building})
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('&amp;lt;script', html)

    def test_no_placeholder_geometry_with_missing_or_invalid_data(self):
        for building in [{}, {'site_plan': {'features': []}},
                         {'site_plan': {**self.building['site_plan'], 'crs': 'EPSG:4326'}},
                         {'site_plan': {**self.building['site_plan'], 'origin_easting': float('nan')}}]:
            with self.subTest(building=building):
                html = render_building_sketch(building)
                self.assertIn('Brak geometrii', html)
                self.assertNotIn('<svg', html)

    def test_json_render_includes_sketch_without_selected_object(self):
        self.building['site_plan']['selected_id'] = None
        html = render_html({'building': self.building})
        self.assertIn('data-building-id="gugik:test"', html)
        self.assertIn('Nie wybrano budynku', html)
        self.assertNotIn('B1 — analizowany', html)


if __name__ == '__main__':
    unittest.main()
