"""
Moduł analizy bezpieczeństwa mediów (GESUT), gazociągów, linii energetycznych
i butli LPG wg taktyki PSP.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GasPipelineInfo:
    pressure_level: str       # "niskie", "średnie", "wysokie"
    diameter_dn: Optional[int] = None
    distance_m: float = 0.0
    valve_location: Optional[str] = "w linii ogrodzenia"


@dataclass
class PowerLineInfo:
    voltage_level: str        # "nN (0.4kV)", "SN (15kV)", "WN (110kV)"
    line_type: str            # "napowietrzna", "kablowa podziemna"
    distance_m: float = 0.0
    transformer_nearby: bool = False
    transformer_distance_m: Optional[float] = None


@dataclass
class UtilitiesSafetyAssessment:
    gas_summary: str
    power_summary: str
    lpg_warning: Optional[str]
    immediate_actions: List[str]
    dispatch_services: List[str]
    isolation_zones: List[str]
    overall_danger_level: str


def evaluate_utilities_safety(
    gas_info: Optional[GasPipelineInfo] = None,
    power_info: Optional[PowerLineInfo] = None,
    suspected_lpg_bottles: bool = True,
    building_type: str = "mieszkalny jednorodzinny",
) -> UtilitiesSafetyAssessment:
    """
    Analizuje infrastrukturę techniczną i generuje instrukcje bezpieczeństwa dla KDR.
    """
    actions: List[str] = []
    dispatch: List[str] = []
    isolation: List[str] = []
    dangers: List[str] = []

    # 1. Gazociąg
    if gas_info:
        dn_str = f" DN{gas_info.diameter_dn}" if gas_info.diameter_dn else ""
        gas_summary = (
            f"Gazociąg {gas_info.pressure_level}go ciśnienia{dn_str} "
            f"(odległość: {int(gas_info.distance_m)}m). Zawór/szafka: {gas_info.valve_location}."
        )
        actions.append(f"Zlokalizować i zamknąć główny kurek gazu: {gas_info.valve_location}.")
        dispatch.append("Pogotowie Gazowe (992) – odcięcie dopływu na przyłączu/sieci.")

        if gas_info.pressure_level in ("średnie", "wysokie"):
            isolation.append(f"Strefa izolacji przy rozszczelnieniu gazociągu {gas_info.pressure_level}go ciśnienia: min. 50m.")
            dangers.append("Wysokie ryzyko wybuchu mieszaniny gazowo-powietrznej.")
    else:
        gas_summary = "Brak zarejestrowanej sieci gazowej w bezpośrednim sąsiedztwie posesji."

    # 2. Elektroenergetyka
    if power_info:
        trafo_str = ""
        if power_info.transformer_nearby:
            dist_t = f" w odl. {int(power_info.transformer_distance_m)}m" if power_info.transformer_distance_m else ""
            trafo_str = f" | Transformator słupowy/kontenerowy{dist_t}"

        power_summary = (
            f"Linia elektroenergetyczna {power_info.line_type} {power_info.voltage_level} "
            f"(odległość: {int(power_info.distance_m)}m){trafo_str}."
        )

        actions.append("Odłączyć zasilanie w budynku (główny wyłącznik / bezpiecznik w złączu kablowym ZK).")
        dispatch.append("Pogotowie Energetyczne (991) – potwierdzenie beznapięciowości linii.")

        if "SN" in power_info.voltage_level or "WN" in power_info.voltage_level:
            isolation.append("Linia SN/WN: BEZWZGLĘDNY ZAKAZ zbliżania drabin i ludzi poniżej 5m!")
            isolation.append("Zakaz podawania zwartego prądu wody na urządzenia pod napięciem SN/WN.")
            dangers.append("Ryzyko przeskoku łuku elektrycznego i porażenia śmiertelnego!")
        elif power_info.line_type == "napowietrzna":
            isolation.append("Linia napowietrzna nN: zachować szczególną ostrożność z drabinami mechanicznymi.")
    else:
        power_summary = "Standardowe przyłącze elektroenergetyczne kablowe podziemne."
        actions.append("Odłączyć zasilanie w rozdzielnicy głównej / złączu kablowym.")

    # 3. Butle z propan-butanem (LPG)
    lpg_warning = None
    if suspected_lpg_bottles:
        lpg_warning = (
            "PODEJRZENIE BUTLI PROPAN-BUTAN 11 kg (standard w budownictwie jednorodzinnym/OSP): "
            "zagrożenie wybuchem BLEVE i wyrzutem odłamków. Chłodzić zza osłony prądem rozproszonym."
        )
        actions.append("Rozpoznanie u lokatorów: potwierdzić liczbę i lokalizację butli 11kg.")
        isolation.append("Strefa zagrożenia odłamkowego butli 11kg: min. 50m.")

    # Ogólna ocena zagrożenia
    if "WN" in power_summary or "SN" in power_summary or (gas_info and gas_info.pressure_level == "wysokie"):
        danger_level = "KRYTYCZNE"
    elif gas_info and gas_info.pressure_level == "średnie":
        danger_level = "WYSOKIE"
    else:
        danger_level = "ŚREDNIE (standardowe procedury zabezpieczenia mediów)"

    return UtilitiesSafetyAssessment(
        gas_summary=gas_summary,
        power_summary=power_summary,
        lpg_warning=lpg_warning,
        immediate_actions=actions,
        dispatch_services=list(dict.fromkeys(dispatch)),
        isolation_zones=isolation,
        overall_danger_level=danger_level,
    )
