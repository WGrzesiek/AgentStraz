"""
Moduł generatora meldunku radiowego KDR i Karty Rozpoznania Bojowego.
Integruje wyniki skilli tactical_recon, water_supply_calc, hazmat_utilities_safety i pv_bess_hazards.
"""

from dataclasses import dataclass
from typing import List, Optional

from skills.tactical_recon.logic import TacticalReconResult
from skills.water_supply_calc.logic import WaterSupplyPlan
from skills.hazmat_utilities_safety.logic import UtilitiesSafetyAssessment
from skills.pv_bess_hazards.logic import PVBessAssessment
from skills.water_supply_calc.building import calculate_building_water, building_water_lines


@dataclass
class IncidentReport:
    address: str
    coordinates: str
    plot_id: Optional[str]
    radio_brief: str
    recon_card_markdown: str
    building_water: Optional[dict] = None


def generate_kdr_reports(
    address: str,
    coordinates: str,
    fire_description: str,
    tactical_recon: TacticalReconResult,
    water_plan: WaterSupplyPlan,
    utilities: UtilitiesSafetyAssessment,
    pv_bess: PVBessAssessment,
    plot_id: Optional[str] = None,
    callsign_unit: str = "GBA OSP",
    sk_destination: str = "Stanowisko Kierowania",
    building: Optional[dict] = None,
    suppression: Optional[dict] = None,
) -> IncidentReport:
    """
    Syntetyzuje dane do meldunku radiowego i Karty Rozpoznania Bojowego.
    """
    building_water = calculate_building_water(building, suppression)
    # 1. Budowa meldunku radiowego (prosty, zwięzły, wojskowo-pożarniczy)
    radio_lines: List[str] = [
        f"{sk_destination}, tu {callsign_unit} na miejscu zdarzenia: {address}.",
        f"SYTUACJA: {fire_description}.",
        f"WIATR I ZADYMIENIE: wiatr {tactical_recon.wind_direction_name.lower()} {int(tactical_recon.wind_speed_kmh)} km/h, "
        f"zagrożony sektor {degrees_to_direction_short(tactical_recon.downwind_azimuth)}.",
    ]

    if tactical_recon.threatened_objects:
        radio_lines.append(f"Zagrożone obiekty sąsiednie: {len(tactical_recon.threatened_objects)} posesje.")

    radio_lines.append(
        f"ZAOPATRZENIE WODNE: {water_plan.tactical_recommendation}"
    )

    hazards_mention = []
    if utilities.gas_summary != "Brak zarejestrowanej sieci gazowej w bezpośrednim sąsiedztwie posesji.":
        hazards_mention.append("gazociąg w ulicy (kurek do odcięcia)")
    if "SN" in utilities.power_summary or "WN" in utilities.power_summary:
        hazards_mention.append("linia wysokiego/średniego napięcia")
    if pv_bess.has_pv and pv_bess.is_daylight:
        hazards_mention.append("fotowoltaika pod napięciem DC na dachu")
    if pv_bess.has_bess:
        hazards_mention.append("magazyn energii Li-ion - nakaz AODO")
    if utilities.lpg_warning:
        hazards_mention.append("podejrzenie butli 11kg")

    if hazards_mention:
        radio_lines.append(f"ZAGROŻENIA: {', '.join(hazards_mention)}.")

    if utilities.dispatch_services:
        radio_lines.append(f"ZADYSPONOWAĆ: {', '.join(utilities.dispatch_services)}.")

    radio_lines.append("Przystępujemy do działań. Bez odbioru.")
    radio_brief = " ".join(radio_lines)

    # 2. Budowa Karty Rozpoznania Bojowego (Markdown)
    card_lines = [
        "🚨 KARTA ROZPOZNANIA MIEJSCA ZDARZENIA 🚨",
        f"**Adres:** {address}",
        f"**Współrzędne:** {coordinates}" + (f" | **Działka nr:** {plot_id}" if plot_id else ""),
        f"**Obiekt / Zdarzenie:** {fire_description}",
        "",
        f"💨 **WARUNKI METEO I ZADYMIENIE:**",
        f"• Wiatr: {tactical_recon.wind_direction_name} ({tactical_recon.wind_direction_code}, {int(tactical_recon.wind_degrees)}°), {tactical_recon.wind_speed_kmh} km/h (porywy: {tactical_recon.wind_gusts_kmh} km/h)",
        f"• Sektor zadymienia: {degrees_to_direction_short(tactical_recon.downwind_azimuth)} ({int(tactical_recon.downwind_azimuth)}° ± {int(tactical_recon.hazard_cone_span_deg/2)}°)",
    ]

    if tactical_recon.threatened_objects:
        card_lines.append("• Obiekty w pasie wiatru (zagrożone promieniowaniem/dymem):")
        for obj in tactical_recon.threatened_objects:
            card_lines.append(f"  - {obj}")

    card_lines.extend([
        "",
        "🚒 **ZAOPATRZENIE WODNE:**",
        f"• Punkt: {water_plan.hydrant_type.value.upper()} (odległość: {int(water_plan.distance_m)}m, z naddatkiem: {int(water_plan.effective_distance_m)}m)",
        f"• Wymagane odcinki W-75: **{water_plan.sections_w75} szt.** (~{water_plan.sections_w75 * 20}m linii)",
        f"• Orientacyjna strata ciśnienia na linii: ~{water_plan.estimated_pressure_loss_bar} bar",
        "• Sprzęt dla roty wodnej:",
    ])
    for g in water_plan.required_gear:
        card_lines.append(f"  - {g}")

    if water_plan.warnings:
        for w in water_plan.warnings:
            card_lines.append(f"  ⚠️ {w}")

    card_lines.append("• KUBATURA I ZAPOTRZEBOWANIE WODY (szacunek):")
    card_lines.extend(f"  - {line}" for line in building_water_lines(building_water))
    card_lines.append(f"  - Źródła zweryfikowano: {building_water['sources_checked_on']}")
    card_lines.extend(f"  - Źródło: {url}" for url in building_water["sources"])

    card_lines.extend([
        "",
        "⚠️ **ZAGROŻENIA I MEDIA (GESUT):**",
        f"• GAZ: {utilities.gas_summary}",
        f"• ENERGETYKA: {utilities.power_summary}",
    ])

    if pv_bess.has_pv or pv_bess.has_bess:
        card_lines.append(f"• INSTALACJE PV/BESS: {pv_bess.summary_bullet}")
        for inst in pv_bess.tactical_instructions:
            card_lines.append(f"  - {inst}")
        for dist in pv_bess.safe_distances:
            card_lines.append(f"  - {dist}")

    if utilities.lpg_warning:
        card_lines.append(f"• BUTLE LPG: {utilities.lpg_warning}")

    if utilities.dispatch_services:
        card_lines.extend([
            "",
            "📞 **ZADYSPOWANIE SŁUŻB WSPÓŁDZIAŁAJĄCYCH:**",
            f"• {', '.join(utilities.dispatch_services)}",
        ])

    card_lines.extend([
        "",
        "📋 **ROZKAZ BOJOWY DLA KDR:**",
    ])
    for order in tactical_recon.tactical_orders:
        card_lines.append(f"• {order}")

    card_lines.extend([
        "",
        "---",
        "📻 **TREŚĆ MELDUNKU RADIOWEGO DO SK (do odczytania):**",
        f"> \"{radio_brief}\"",
    ])

    recon_card_markdown = "\n".join(card_lines)

    return IncidentReport(
        address=address,
        coordinates=coordinates,
        plot_id=plot_id,
        radio_brief=radio_brief,
        recon_card_markdown=recon_card_markdown,
        building_water=building_water,
    )


def degrees_to_direction_short(deg: float) -> str:
    from skills.tactical_recon.logic import degrees_to_direction
    return degrees_to_direction(deg)[0]
