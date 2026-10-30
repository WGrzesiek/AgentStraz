"""
Skrypt demonstracyjny uruchamiający skille taktyczne dla scenariusza bojowego:
"Nowa Wieś, ul. Sosnowa 14".
Symuluje pobranie danych z serwerów MCP (Geoportal, OSM, IMGW) i wygenerowanie
kompletnej Karty Rozpoznania Bojowego oraz gotowego meldunku radiowego KDR.
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Zapewnienie obsługi UTF-8 na konsoli Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Zapewnienie ścieżki importu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from skills.water_supply_calc import calculate_water_supply, HydrantType
from skills.tactical_recon import analyze_tactical_recon, NeighborObject
from skills.hazmat_utilities_safety import (
    evaluate_utilities_safety,
    GasPipelineInfo,
    PowerLineInfo,
)
from skills.pv_bess_hazards import evaluate_pv_bess_hazards
from skills.kdr_radio_brief import generate_kdr_reports


def run_tactical_demo(output_dir="reports"):
    print("=" * 70)
    print("🚒 AGENT STRAŻ - SYSTEM ROZPOZNANIA BOJOWEGO DLA KDR (OSP)")
    print("=" * 70)

    # 1. Dane wejściowe dyspozycji
    address = "Nowa Wieś, ul. Sosnowa 14"
    coords = "52.12345, 20.98765"
    plot_id = "142/2"
    fire_desc = "Pożar pomieszczeń mieszkalnych budynku jednorodzinnego"

    print(f"\n[DYSPOZYCJA] Adres zdarzenia: {address} ({coords})")
    print(f"[ZGŁOSZENIE] {fire_desc}\n")

    # 2. Uruchomienie skilla: tactical_recon (Wiatr i Wektor Zagrożenia)
    print("--> [1/4] Uruchamianie skilla: tactical-recon...")
    neighbors = [
        NeighborObject(identifier="Sosnowa 16", distance_m=28.0, bearing_deg=130.0, object_type="budynek mieszkalny"),
        NeighborObject(identifier="Sosnowa 18", distance_m=55.0, bearing_deg=140.0, object_type="budynek gospodarczy"),
        NeighborObject(identifier="Sosnowa 12", distance_m=32.0, bearing_deg=310.0, object_type="budynek mieszkalny"),
    ]
    tactical_recon = analyze_tactical_recon(
        wind_degrees=315.0,  # Wiatr NW (północno-zachodni)
        wind_speed_kmh=18.0,
        wind_gusts_kmh=36.0,
        relative_humidity_pct=42.0,
        neighbors=neighbors,
    )

    # 3. Uruchomienie skilla: water_supply_calc (Zasilanie Wodne W-75)
    print("--> [2/4] Uruchamianie skilla: water-supply-calc...")
    water_plan = calculate_water_supply(
        distance_m=95.0,
        hydrant_type=HydrantType.UNDERGROUND,
        diameter_dn=80,
        target_flow_lpm=800.0,
    )

    # 4. Uruchomienie skilla: hazmat_utilities_safety (Media i Sieci GESUT)
    print("--> [3/4] Uruchamianie skilla: hazmat-utilities-safety...")
    gas_info = GasPipelineInfo(
        pressure_level="średnie",
        diameter_dn=63,
        distance_m=12.0,
        valve_location="skrzynka w linii ogrodzenia od zachodu",
    )
    power_info = PowerLineInfo(
        voltage_level="nN (0.4kV)",
        line_type="napowietrzna",
        distance_m=8.0,
        transformer_nearby=True,
        transformer_distance_m=130.0,
    )
    utilities = evaluate_utilities_safety(
        gas_info=gas_info,
        power_info=power_info,
        suspected_lpg_bottles=True,
    )

    # 5. Uruchomienie skilla: pv_bess_hazards (Fotowoltaika i Magazyny Energii)
    print("--> [4/4] Uruchamianie skilla: pv-bess-hazards...")
    pv_bess = evaluate_pv_bess_hazards(
        has_pv=True,
        pv_capacity_kw=9.9,
        has_bess=False,
        is_daylight=True,
        pwp_switch_located=False,
    )

    # 6. Synteza: kdr_radio_brief (Karta Rozpoznania + Komunikat Radiowy)
    report = generate_kdr_reports(
        address=address,
        coordinates=coords,
        plot_id=plot_id,
        fire_description=fire_desc,
        tactical_recon=tactical_recon,
        water_plan=water_plan,
        utilities=utilities,
        pv_bess=pv_bess,
        callsign_unit="GBA OSP Nowa Wieś",
        sk_destination="Stanowisko Kierowania KP PSP",
        # Fikcyjne wymiary i rozpoznana powierzchnia gaszenia; bez danych online.
        building={"footprint_area_m2": 120, "height_m": 6,
                  "source": "DEMO — DANE FIKCYJNE"},
        suppression={"fire_area_m2": 100, "duration_min": 20},
    )

    from tools.skill_report import build_visualizer_data
    from tools.visualizer import render_html

    data = build_visualizer_data(report, tactical_recon, water_plan, utilities, pv_bess, is_demo=True)
    data["weather"]["station_name"] = "Scenariusz demonstracyjny — dane fikcyjne"
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "karta_skills.md").write_text("DEMO — DANE FIKCYJNE\n\n" + report.recon_card_markdown, encoding="utf-8")
    (output / "karta_skills.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "karta_skills.html").write_text(render_html(data), encoding="utf-8")
    print(f"Raporty Markdown, JSON i HTML: {output.resolve()}")

    print("\n" + "=" * 70)
    print("WYGENEROWANA KARTA ROZPOZNANIA BOJOWEGO (MARKDOWN):")
    print("=" * 70)
    print(report.recon_card_markdown)
    print("\n" + "=" * 70)
    print("GOTOWY MELDUNEK RADIOWY KDR DO NADAŃ PRZEZ RADIO / TTS:")
    print("=" * 70)
    print(f'"{report.radio_brief}"')
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo skilli i wspólnego raportu KDR")
    parser.add_argument("--output-dir", default="reports")
    run_tactical_demo(parser.parse_args().output_dir)
