"""
Moduł analizy taktycznej wektora wiatru, rozprzestrzeniania dymu i strefy zagrożenia KDR.
"""

from typing import Dict, Any, Tuple


DIRECTIONS_16 = [
    ("N", "północny", 0),
    ("NNE", "północno-północno-wschodni", 22.5),
    ("NE", "północno-wschodni", 45),
    ("ENE", "wschodnio-północno-wschodni", 67.5),
    ("E", "wschodni", 90),
    ("ESE", "wschodnio-południowo-wschodni", 112.5),
    ("SE", "południowo-wschodni", 135),
    ("SSE", "południowo-południowo-wschodni", 157.5),
    ("S", "południowy", 180),
    ("SSW", "południowo-południowo-zachodni", 202.5),
    ("SW", "południowo-zachodni", 225),
    ("WSW", "zachodnio-południowo-zachodni", 247.5),
    ("W", "zachodni", 270),
    ("WNW", "zachodnio-północno-zachodni", 292.5),
    ("NW", "północno-zachodni", 315),
    ("NNW", "północno-północno-zachodni", 337.5),
]


def wind_deg_to_compass(deg: float) -> Tuple[str, str]:
    """
    Zamienia stopnie wiatru (0-360°) na kod róży wiatrów i opis słowny.
    np. 315° -> ('NW', 'północno-zachodni')
    """
    normalized = (deg + 11.25) % 360
    idx = int(normalized / 22.5) % 16
    code, name, _ = DIRECTIONS_16[idx]
    return code, name


def calculate_smoke_plume(wind_from_deg: float, wind_speed_kmh: float, gusts_kmh: float = 0.0) -> Dict[str, Any]:
    """
    Oblicza wektor przemieszczania się dymu / strefę zawietrzną na podstawie kierunku wiatru.
    Uwaga: wiatr wieje Z kierunku wind_from_deg, więc dym porusza się W kierunku (wind_from_deg + 180) % 360.
    """
    wind_code, wind_name = wind_deg_to_compass(wind_from_deg)

    # Kierunek, w którym znosi dym (downwind)
    downwind_deg = (wind_from_deg + 180.0) % 360.0
    downwind_code, downwind_name = wind_deg_to_compass(downwind_deg)

    # Stożek zadymienia: kąt ±30° od osi znoszenia dymu
    cone_min_deg = int((downwind_deg - 30.0 + 360.0) % 360.0)
    cone_max_deg = int((downwind_deg + 30.0) % 360.0)

    # Ocena dynamiki rozwoju pożaru i zagrożenia
    if wind_speed_kmh < 5:
        intensity = "SŁABY / CISZA"
        fire_spread_risk = "Niski wpływ wiatru. Dym unosi się pionowo lub rozchodzi nieregularnie."
        tactical_advice = "Możliwość gromadzenia się dymu i gazów pożarowych w obniżeniach terenu."
    elif wind_speed_kmh < 20:
        intensity = "UMIARKOWANY"
        fire_spread_risk = "Wyraźny stożek znoszenia dymu i gazów pożarowych."
        tactical_advice = f"Zabezpieczyć sektor {downwind_code} ({downwind_name}). Ewakuować osoby w strefie bezpośredniego zadymienia."
    elif wind_speed_kmh < 40:
        intensity = "DOŚĆ SILNY"
        fire_spread_risk = "Podwyższone ryzyko gwałtownego rozprzestrzeniania się frontu pożaru."
        tactical_advice = f"Priorytetowa obrona obiektów w sektorze {downwind_code}! Ryzyko przerzutu iskier i zarzewi ognia na sąsiednie dachy."
    else:
        intensity = "BARDZO SILNY / WICHRY"
        fire_spread_risk = "KRYTYCZNE zagrożenie pożarowe! Błyskawiczny rozwój frontu ogniowego."
        tactical_advice = f"ALARM: Zarządzić natychmiastową ewakuację sektora {downwind_code} w promieniu 150-300m! Zakaz wchodzenia rot gaśniczych po stronie zawietrznej."

    gust_alert = ""
    if gusts_kmh > wind_speed_kmh + 15 and gusts_kmh > 35:
        gust_alert = f"⚠️ UWAGA NA SILNE PORYWY do {int(gusts_kmh)} km/h – nagłe zmiany zachowania płomieni i zrzuty dymu ku ziemi!"

    return {
        "wind_from": {
            "degrees": int(wind_from_deg),
            "code": wind_code,
            "name": wind_name,
            "speed_kmh": round(wind_speed_kmh, 1),
            "gusts_kmh": round(gusts_kmh, 1) if gusts_kmh else None,
            "intensity": intensity,
        },
        "smoke_plume": {
            "travel_direction_code": downwind_code,
            "travel_direction_name": downwind_name,
            "travel_degrees": int(downwind_deg),
            "hazard_cone_range": f"{cone_min_deg}° – {cone_max_deg}° (sektor {downwind_code})",
        },
        "tactical_assessment": {
            "spread_risk": fire_spread_risk,
            "tactical_advice": tactical_advice,
            "gust_alert": gust_alert,
        },
    }
