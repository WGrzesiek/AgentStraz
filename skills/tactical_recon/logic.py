"""
Moduł analizy taktycznej rozpoznania wstępnego KDR.
Wyznacza wektor wiatru, sektor zadymienia, zagrożone posesje i zasady bezpieczeństwa.
"""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple


CARDINAL_DIRECTIONS = [
    ("N", "PÓŁNOCNY", 0.0),
    ("NNE", "PÓŁNOCNO-PÓŁNOCNO-WSCHODNI", 22.5),
    ("NE", "PÓŁNOCNO-WSCHODNI", 45.0),
    ("ENE", "WSCHODNIO-PÓŁNOCNO-WSCHODNI", 67.5),
    ("E", "WSCHODNI", 90.0),
    ("ESE", "WSCHODNIO-POŁUDNIOWO-WSCHODNI", 112.5),
    ("SE", "POŁUDNIOWO-WSCHODNI", 135.0),
    ("SSE", "POŁUDNIOWO-POŁUDNIOWO-WSCHODNI", 157.5),
    ("S", "POŁUDNIOWY", 180.0),
    ("SSW", "POŁUDNIOWO-POŁUDNIOWO-ZACHODNI", 202.5),
    ("SW", "POŁUDNIOWO-ZACHODNI", 225.0),
    ("WSW", "ZACHODNIO-POŁUDNIOWO-ZACHODNI", 247.5),
    ("W", "ZACHODNI", 270.0),
    ("WNW", "ZACHODNIO-PÓŁNOCNO-ZACHODNI", 292.5),
    ("NW", "PÓŁNOCNO-ZACHODNI", 315.0),
    ("NNW", "PÓŁNOCNO-PÓŁNOCNO-ZACHODNI", 337.5),
]


def degrees_to_direction(deg: float) -> Tuple[str, str]:
    """Zwraca skrót (np. NW) i polską nazwę kierunku wiatru."""
    normalized = deg % 360.0
    idx = int((normalized + 11.25) / 22.5) % 16
    code, name, _ = CARDINAL_DIRECTIONS[idx]
    return code, name


@dataclass
class NeighborObject:
    identifier: str              # np. "Sosnowa 16", "Magazyn drewna"
    distance_m: float
    bearing_deg: float           # azymut od ogniska pożaru do obiektu
    object_type: str = "budynek"


@dataclass
class TacticalReconResult:
    wind_direction_code: str
    wind_direction_name: str
    wind_degrees: float
    downwind_azimuth: float
    hazard_cone_span_deg: float
    wind_speed_kmh: float
    wind_gusts_kmh: float
    relative_humidity_pct: Optional[float]
    hazard_level: str
    threatened_objects: List[str]
    safe_approach_azimuths: str
    tactical_orders: List[str]
    smoke_summary: str


def is_in_cone(bearing: float, center_azimuth: float, half_span: float) -> bool:
    """Sprawdza czy dany azymut mieści się w stożku zagrożenia."""
    diff = abs((bearing - center_azimuth + 180.0) % 360.0 - 180.0)
    return diff <= half_span


def analyze_tactical_recon(
    wind_degrees: float,
    wind_speed_kmh: float,
    wind_gusts_kmh: Optional[float] = None,
    relative_humidity_pct: Optional[float] = None,
    temperature_c: Optional[float] = None,
    neighbors: Optional[List[NeighborObject]] = None,
) -> TacticalReconResult:
    """
    Przeprowadza analizę wektora wiatru, rozprzestrzeniania dymu i taktyki dla KDR.
    """
    code, name = degrees_to_direction(wind_degrees)
    downwind_azimuth = (wind_degrees + 180.0) % 360.0
    downwind_code, downwind_name = degrees_to_direction(downwind_azimuth)

    gusts = wind_gusts_kmh if wind_gusts_kmh is not None else wind_speed_kmh
    half_span = 45.0 if gusts > 35.0 else 30.0

    # Poziom zagrożenia wiatrowego
    if gusts >= 50.0:
        hazard_level = "KRYTYCZNY (Bardzo silne porywy wiatru - gwałtowne rozprzestrzenianie pożaru)"
    elif gusts >= 30.0:
        hazard_level = "WYSOKI (Silny wiatr, ryzyko przerzutu zarzewi ognia i żagwi)"
    elif wind_speed_kmh >= 15.0:
        hazard_level = "UMIARKOWANY (Wyraźny stożek zadymienia na poziomie gruntu)"
    else:
        hazard_level = "NISKI (Słaby wiatr, pionowy słup dymu)"

    # Filtrowanie zagrożonych obiektów
    threatened: List[str] = []
    if neighbors:
        for n in neighbors:
            if is_in_cone(n.bearing_deg, downwind_azimuth, half_span):
                threatened.append(
                    f"{n.identifier} ({n.object_type}, odległość: {int(n.distance_m)}m w sektorze {degrees_to_direction(n.bearing_deg)[0]})"
                )

    # Bezpieczne kierunki dojazdu i pozycjonowania wozów
    safe_approach = f"Od strony nawietrznej: {code} ({int(wind_degrees)}°) lub z flanki (boki strefy)."

    orders: List[str] = [
        f"Ustawienie wozów bojowych: bezwzględnie od strony nawietrznej ({code}) lub z flanki.",
        f"Główny sektor zagrożenia: {downwind_code} ({downwind_name}, kąt {int(downwind_azimuth)}° ± {int(half_span)}°).",
    ]

    if threatened:
        orders.append(
            f"OBRONA: Natychmiast podać prąd wody w obronie obiektów: {', '.join([t.split(' (')[0] for t in threatened])}."
        )

    if gusts >= 30.0:
        orders.append("Ostrzeżenie o żagwiach: kontrolować dachy i poszycie w odległości do 150m od zawietrznej.")

    if relative_humidity_pct is not None and relative_humidity_pct < 35.0:
        orders.append(
            f"Niska wilgotność powietrza ({relative_humidity_pct}%): ekstremalna podatność na zapalenie traw i drewna!"
        )

    smoke_summary = (
        f"Wiatr {name} ({code}, {int(wind_degrees)}°), {wind_speed_kmh} km/h (porywy: {gusts} km/h). "
        f"Wektor zadymienia skierowany na sektor {downwind_code} ({int(downwind_azimuth)}°)."
    )

    return TacticalReconResult(
        wind_direction_code=code,
        wind_direction_name=name,
        wind_degrees=wind_degrees,
        downwind_azimuth=downwind_azimuth,
        hazard_cone_span_deg=half_span * 2.0,
        wind_speed_kmh=wind_speed_kmh,
        wind_gusts_kmh=gusts,
        relative_humidity_pct=relative_humidity_pct,
        hazard_level=hazard_level,
        threatened_objects=threatened,
        safe_approach_azimuths=safe_approach,
        tactical_orders=orders,
        smoke_summary=smoke_summary,
    )
