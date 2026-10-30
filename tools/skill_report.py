"""Adapter wyników skilli do kontraktu wizualizatora, bez parsowania Markdown."""

from skills.water_supply_calc import HydrantType


def build_visualizer_data(report, tactical_recon, water_plan, utilities, pv_bess, *, is_demo=False):
    lat, lon = (float(value.strip()) for value in report.coordinates.split(','))
    point = {
        "id": "H1", "distance_m": water_plan.distance_m,
        "type": {HydrantType.PILLAR: "nadziemny", HydrantType.UNDERGROUND: "podziemny"}.get(
            water_plan.hydrant_type, "nieznany"),
        "diameter": f"DN{water_plan.diameter_dn}" if water_plan.diameter_dn else "DN nieznane",
        "estimated_w75_hoses": water_plan.sections_w75,
        "requires_standpipe_and_key": water_plan.hydrant_type == HydrantType.UNDERGROUND,
        "location_desc": "Lokalizacja i sprawność do potwierdzenia w terenie",
        # Skill otrzymuje odległość, ale nie azymut: nie dodajemy markera na mapie.
        "bearing_deg": None,
    }
    hydrants, intakes = [], []
    if water_plan.hydrant_type == HydrantType.SUCTION_POINT:
        intakes.append({
            "id": "W1", "name": "Punkt czerpania wody", "distance_m": water_plan.distance_m,
            "suction_method": "; ".join(water_plan.required_gear),
            "access_road": "Brak danych", "bearing_deg": None,
        })
    else:
        hydrants.append(point)
    return {
        "is_demo": is_demo,
        "building": (report.building_water or {}).get("building", {}),
        "suppression": (report.building_water or {}).get("suppression", {}),
        "building_water": report.building_water,
        "incident_info": {
            "address": report.address, "street": report.address,
            "lat": lat, "lon": lon, "parcel_id": report.plot_id or "Brak danych",
        },
        "weather": {
            "wind_deg": tactical_recon.wind_degrees,
            "wind_direction_abbr": tactical_recon.wind_direction_code,
            "wind_direction_text": tactical_recon.wind_direction_name,
            "wind_speed_kmh": tactical_recon.wind_speed_kmh,
            "wind_speed_ms": round(tactical_recon.wind_speed_kmh / 3.6, 1),
            "wind_gusts_kmh": tactical_recon.wind_gusts_kmh,
            "hazard_cone_span_deg": tactical_recon.hazard_cone_span_deg,
            "smoke_sector": tactical_recon.smoke_summary,
            "smoke_threat_objects": tactical_recon.threatened_objects,
        },
        "water_supply": {"hydrants": hydrants, "open_water_intakes": intakes},
        "utilities_and_hazards": {
            "gas": {"pipeline_type": utilities.gas_summary},
            "electricity": {"lines": utilities.power_summary},
            "access_roads": {},
            "additional_hazards": [text for text in [pv_bess.summary_bullet, utilities.lpg_warning] if text],
        },
        "tactical_orders": (tactical_recon.tactical_orders + water_plan.warnings
                            + utilities.isolation_zones + pv_bess.tactical_instructions
                            + pv_bess.safe_distances),
        "radio_brief": report.radio_brief,
    }
