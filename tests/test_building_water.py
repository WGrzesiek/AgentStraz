import copy
import math
import unittest

from skills.water_supply_calc.building import calculate_building_water
from tools.visualizer import render_html


class TestBuildingWater(unittest.TestCase):
    def test_dimensions_and_units(self):
        result = calculate_building_water(
            {"footprint_area_m2": 120, "height_m": 6},
            {"fire_area_m2": 100, "duration_min": 20},
        )
        self.assertEqual(result["volume_m3"], 720)
        self.assertEqual(result["flow_l_s"], {"min": 8, "max": 10})
        self.assertEqual(result["flow_l_min"], {"min": 480, "max": 600})
        self.assertEqual(result["water_volume_l"], {"min": 9600, "max": 12000})

    def test_explicit_interior_volume_scenario(self):
        result = calculate_building_water(
            {"interior_volume_m3": 600, "mean_room_height_m": 3},
            {"affected_fraction": 0.5},
        )
        self.assertEqual(result["fire_area_m2"], 100)
        self.assertIsNone(result["water_volume_l"])
        self.assertIn("scenariusz", result["area_method"])

    def test_no_fabricated_height_area_fraction_or_duration(self):
        for building, suppression in [
            ({}, {}), ({"footprint_area_m2": 120}, {}),
            ({"volume_m3": 720, "mean_room_height_m": 3}, {"affected_fraction": 1}),
            ({"interior_volume_m3": 600, "mean_room_height_m": 3}, {}),
            ({"interior_volume_m3": 600}, {"affected_fraction": 1}),
        ]:
            with self.subTest(building=building, suppression=suppression):
                result = calculate_building_water(building, suppression)
                self.assertEqual(result["status"], "insufficient_data")
                self.assertIsNone(result["flow_l_s"])
                self.assertIsNone(result["water_volume_l"])

    def test_measured_area_takes_precedence(self):
        result = calculate_building_water(
            {"volume_m3": 500, "footprint_area_m2": 100, "height_m": 6,
             "interior_volume_m3": 300, "mean_room_height_m": 3},
            {"fire_area_m2": 20, "affected_fraction": 1},
        )
        self.assertEqual(result["volume_m3"], 500)
        self.assertEqual(result["fire_area_m2"], 20)

    def test_rejects_invalid_inputs(self):
        for value in [0, -1, math.nan, math.inf, True, "120"]:
            for field in ["volume_m3", "footprint_area_m2", "height_m", "interior_volume_m3", "mean_room_height_m"]:
                with self.subTest(value=value, field=field), self.assertRaises(ValueError):
                    calculate_building_water({field: value})
            for field in ["fire_area_m2", "duration_min", "affected_fraction"]:
                with self.subTest(value=value, field=field), self.assertRaises(ValueError):
                    calculate_building_water({}, {field: value})
        with self.assertRaises(ValueError):
            calculate_building_water({}, {"affected_fraction": 1.1})

    def test_html_computes_from_input_escapes_and_ignores_stale_result(self):
        data = {"building": {"footprint_area_m2": 120, "height_m": 6,
                             "source": "<script>alert(1)</script>"},
                "suppression": {"fire_area_m2": 100, "duration_min": 20},
                "building_water": {"volume_m3": 99999}}
        original = copy.deepcopy(data)
        html = render_html(data)
        for text in ["720.0 m³", "480.0–600.0 l/min", "9600.0–12000.0 l", "zpe.gov.pl", "gov.pl/attachment"]:
            self.assertIn(text, html)
        self.assertNotIn("99999", html)
        self.assertNotIn("<script>alert(1)", html)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()
