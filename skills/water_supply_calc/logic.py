"""
Kalkulator taktyczny zaopatrzenia wodnego dla KDR i rot gaśniczych OSP/PSP.
Oblicza liczbę odcinków W-75, wymagany osprzęt armatury i straty ciśnienia.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import List, Optional


class HydrantType(str, Enum):
    PILLAR = "pillar"              # nadziemny
    UNDERGROUND = "underground"    # podziemny
    SUCTION_POINT = "suction"      # punkt czerpania ze zbiornika/cieku
    UNKNOWN = "unknown"


@dataclass
class WaterSupplyPlan:
    distance_m: float
    effective_distance_m: float
    sections_w75: int
    hydrant_type: HydrantType
    diameter_dn: Optional[int]
    required_gear: List[str]
    estimated_pressure_loss_bar: float
    tactical_recommendation: str
    warnings: List[str] = field(default_factory=list)


def calculate_water_supply(
    distance_m: float,
    hydrant_type: HydrantType = HydrantType.PILLAR,
    diameter_dn: Optional[int] = 80,
    target_flow_lpm: float = 800.0,
    terrain_reserve_pct: float = 0.15,
) -> WaterSupplyPlan:
    """
    Oblicza parametry budowy linii gaśniczej W-75 i dobiera sprzęt.

    :param distance_m: Geometryczna odległość do punktu wodnego w metrach
    :param hydrant_type: Typ hydrantu lub punkt czerpania
    :param diameter_dn: Średnica nominalna (np. 80, 100, 150)
    :param target_flow_lpm: Planowany przepływ w litrach na minutę (domyślnie 800 l/min)
    :param terrain_reserve_pct: Naddatek na omijanie przeszkód (domyślnie 15%)
    """
    if distance_m < 0:
        raise ValueError("Odległość nie może być ujemna.")

    # 1. Obliczenie długości rzeczywistej i liczby odcinków W-75 (20m/szt)
    effective_dist = distance_m * (1.0 + terrain_reserve_pct)
    sections = max(1, math.ceil(effective_dist / 20.0))

    gear: List[str] = [
        f"Węże tłoczne W-75: {sections} szt. (nominalnie {sections * 20} m)",
        "Klucze do łączników 75/52 (para)",
    ]
    warnings: List[str] = []

    # 2. Dobór armatury wg typu hydrantu
    if hydrant_type == HydrantType.UNDERGROUND:
        gear.append("Stojak hydrantowy DN80/2x75 (lub DN100 w zależności od nasady)")
        gear.append("Klucz do hydrantów podziemnych (typ 7B/7C)")
        gear.append("Klucz do zasuw (opcjonalnie do odkopania/otwarcia zasuwy)")
        tactical_rec = (
            f"Hydrant podziemny w odl. {int(distance_m)}m: Rota zaopatrzenia wodnego "
            f"zabiera stojak hydrantowy DN80/2x75, klucz podziemny oraz {sections} odcinków W-75."
        )
    elif hydrant_type == HydrantType.PILLAR:
        gear.append("Klucz do hydrantów nadziemnych (typ 7E)")
        tactical_rec = (
            f"Hydrant nadziemny w odl. {int(distance_m)}m: Bezpośrednie wpięcie linii W-75. "
            f"Wymaga {sections} odcinków W-75 i klucza hydrantowego 7E."
        )
    elif hydrant_type == HydrantType.SUCTION_POINT:
        gear = [
            "Motopompa pożarnicza (np. Tohatsu / Polonia M16/8)",
            "Węże ssawne W-110 (min. 2-3 odcinki po 2.5m)",
            "Smok ssawny z zaworem zwrotnym i koszem ochronnym",
            "Pływak ze sznurem asekuracyjnym",
            f"Węże tłoczne W-75: {sections} szt. od motopompy do wozu gaśniczego",
        ]
        tactical_rec = (
            f"Punkt czerpania wody otwartej w odl. {int(distance_m)}m: Wymaga rozstawienia "
            f"motopompy pożarniczej, linii ssawnej W-110 ze smokiem i pływakiem."
        )
    else:
        gear.append("Klucz uniwersalny do hydrantów")
        tactical_rec = f"Punkt zasilania w odl. {int(distance_m)}m: Budowa linii W-75 ({sections} szt.)."

    # 3. Oszacowanie strat ciśnienia na linii W-75 (ok. 0.12 bar na 100m przy 800 l/min)
    total_hose_length = sections * 20.0
    pressure_loss_bar = round((total_hose_length / 100.0) * 0.12 * ((target_flow_lpm / 800.0) ** 2), 2)

    # 4. Sprawdzenie parametrów średnicy DN i zasięgu
    if diameter_dn and diameter_dn < 80:
        warnings.append(f"Uwaga: Średnica DN{diameter_dn} może nie zapewnić pełnego wydatku dla GCBA.")
    if distance_m > 300:
        warnings.append("Duża odległość (>300m): Rozważ zorganizowanie przetłaczania pompą pośrednią lub dowożenia.")
    if distance_m > 600:
        warnings.append("Krytyczna odległość (>600m): Budowa magistrali wężowej czasochłonna – priorytet dla dowożenia wody.")

    return WaterSupplyPlan(
        distance_m=distance_m,
        effective_distance_m=round(effective_dist, 1),
        sections_w75=sections,
        hydrant_type=hydrant_type,
        diameter_dn=diameter_dn,
        required_gear=gear,
        estimated_pressure_loss_bar=pressure_loss_bar,
        tactical_recommendation=tactical_rec,
        warnings=warnings,
    )
