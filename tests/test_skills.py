"""
Testy jednostkowe skilli taktycznych dla Asystenta KDR OSP.
"""

import unittest
import math

from skills.water_supply_calc.logic import (
    calculate_water_supply,
    HydrantType,
    WaterSupplyPlan,
)
from skills.tactical_recon.logic import (
    analyze_tactical_recon,
    degrees_to_direction,
    is_in_cone,
    NeighborObject,
)
from skills.pv_bess_hazards.logic import (
    evaluate_pv_bess_hazards,
    PVBessAssessment,
)
from skills.hazmat_utilities_safety.logic import (
    evaluate_utilities_safety,
    GasPipelineInfo,
    PowerLineInfo,
)
from skills.kdr_radio_brief.logic import generate_kdr_reports


class TestWaterSupplyCalc(unittest.TestCase):
    def test_underground_hydrant_calculation(self):
        plan = calculate_water_supply(
            distance_m=95.0,
            hydrant_type=HydrantType.UNDERGROUND,
            diameter_dn=80,
            terrain_reserve_pct=0.15,
        )
        # 95 * 1.15 = 109.25m -> ceil(109.25 / 20) = 6 odcinków
        self.assertEqual(plan.sections_w75, 6)
        self.assertEqual(plan.hydrant_type, HydrantType.UNDERGROUND)
        self.assertTrue(any("Stojak hydrantowy" in g for g in plan.required_gear))
        self.assertTrue(any("7B/7C" in g for g in plan.required_gear))
        self.assertGreater(plan.estimated_pressure_loss_bar, 0.0)

    def test_pillar_hydrant_gear(self):
        plan = calculate_water_supply(
            distance_m=40.0,
            hydrant_type=HydrantType.PILLAR,
            diameter_dn=80,
        )
        self.assertEqual(plan.sections_w75, 3)
        self.assertTrue(any("7E" in g for g in plan.required_gear))
        self.assertFalse(any("Stojak hydrantowy" in g for g in plan.required_gear))

    def test_suction_point_gear(self):
        plan = calculate_water_supply(
            distance_m=120.0,
            hydrant_type=HydrantType.SUCTION_POINT,
        )
        self.assertTrue(any("Motopompa" in g for g in plan.required_gear))
        self.assertTrue(any("W-110" in g for g in plan.required_gear))
        self.assertTrue(any("Smok ssawny" in g for g in plan.required_gear))

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            calculate_water_supply(distance_m=-10.0)

    def test_large_distance_warning(self):
        plan = calculate_water_supply(distance_m=350.0)
        self.assertTrue(any("Duża odległość" in w for w in plan.warnings))


class TestTacticalRecon(unittest.TestCase):
    def test_degrees_to_direction(self):
        code, name = degrees_to_direction(315.0)
        self.assertEqual(code, "NW")
        self.assertEqual(name, "PÓŁNOCNO-ZACHODNI")

        code_n, _ = degrees_to_direction(0.0)
        self.assertEqual(code_n, "N")

    def test_downwind_cone_and_neighbors(self):
        # Wiatr z NW (315°) wieje w stronę SE (135°)
        neighbors = [
            NeighborObject(identifier="Dom A", distance_m=30.0, bearing_deg=135.0),  # dokładnie w osi SE
            NeighborObject(identifier="Dom B", distance_m=40.0, bearing_deg=315.0),  # pod wiatr (NW)
        ]
        result = analyze_tactical_recon(
            wind_degrees=315.0,
            wind_speed_kmh=20.0,
            neighbors=neighbors,
        )
        self.assertAlmostEqual(result.downwind_azimuth, 135.0)
        self.assertEqual(len(result.threatened_objects), 1)
        self.assertIn("Dom A", result.threatened_objects[0])

    def test_strong_wind_warning(self):
        result = analyze_tactical_recon(
            wind_degrees=90.0,
            wind_speed_kmh=25.0,
            wind_gusts_kmh=55.0,
        )
        self.assertIn("KRYTYCZNY", result.hazard_level)
        self.assertTrue(any("żagwiach" in o for o in result.tactical_orders))


class TestPVBessHazards(unittest.TestCase):
    def test_pv_daylight_hazards(self):
        assessment = evaluate_pv_bess_hazards(
            has_pv=True,
            pv_capacity_kw=10.0,
            has_bess=False,
            is_daylight=True,
        )
        self.assertTrue(assessment.has_pv)
        self.assertTrue(assessment.pwp_required)
        self.assertIsNotNone(assessment.dc_voltage_warning)
        self.assertIn("1000V", assessment.dc_voltage_warning)
        self.assertTrue(any("5 metrów" in d for d in assessment.safe_distances))

    def test_bess_toxic_hazards(self):
        assessment = evaluate_pv_bess_hazards(
            has_pv=False,
            has_bess=True,
            bess_capacity_kwh=15.0,
        )
        self.assertIn("fluorowodoru", assessment.toxic_gas_warning)
        self.assertTrue(any("AODO" in i for i in assessment.tactical_instructions))


class TestHazmatUtilitiesSafety(unittest.TestCase):
    def test_gas_and_power_assessment(self):
        gas = GasPipelineInfo(pressure_level="średnie", diameter_dn=63, distance_m=10.0)
        power = PowerLineInfo(voltage_level="SN (15kV)", line_type="napowietrzna", distance_m=15.0)
        res = evaluate_utilities_safety(gas_info=gas, power_info=power)

        self.assertTrue(any("Pogotowie Gazowe" in s for s in res.dispatch_services))
        self.assertTrue(any("Pogotowie Energetyczne" in s for s in res.dispatch_services))
        self.assertTrue(any("5m" in z for z in res.isolation_zones))
        self.assertIsNotNone(res.lpg_warning)


class TestKDRRadioBriefIntegration(unittest.TestCase):
    def test_full_report_generation(self):
        recon = analyze_tactical_recon(wind_degrees=315.0, wind_speed_kmh=15.0)
        water = calculate_water_supply(distance_m=95.0, hydrant_type=HydrantType.UNDERGROUND)
        util = evaluate_utilities_safety()
        pv = evaluate_pv_bess_hazards(has_pv=True, pv_capacity_kw=8.0, is_daylight=True)

        report = generate_kdr_reports(
            address="Sosnowa 14",
            coordinates="52.12, 20.98",
            fire_description="Pożar poddasza",
            tactical_recon=recon,
            water_plan=water,
            utilities=util,
            pv_bess=pv,
        )

        self.assertIn("Sosnowa 14", report.radio_brief)
        self.assertIn("KARTA ROZPOZNANIA MIEJSCA ZDARZENIA", report.recon_card_markdown)
        self.assertIn("ZAOPATRZENIE WODNE", report.recon_card_markdown)
        self.assertIn("MELDUNKU RADIOWEGO", report.recon_card_markdown)


if __name__ == "__main__":
    unittest.main()
