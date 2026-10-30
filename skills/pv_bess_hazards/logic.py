"""
Moduł analizy zagrożeń instalacjami fotowoltaicznymi (PV), magazynami energii (BESS)
oraz pojazdami elektrycznymi (EV) wg standardów KG PSP.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PVBessAssessment:
    has_pv: bool
    has_bess: bool
    has_ev: bool
    is_daylight: bool
    risk_level: str
    pwp_required: bool
    dc_voltage_warning: Optional[str]
    toxic_gas_warning: Optional[str]
    safe_distances: List[str]
    tactical_instructions: List[str]
    summary_bullet: str


def evaluate_pv_bess_hazards(
    has_pv: bool = False,
    pv_capacity_kw: Optional[float] = None,
    has_bess: bool = False,
    bess_capacity_kwh: Optional[float] = None,
    has_ev: bool = False,
    is_daylight: bool = True,
    pwp_switch_located: bool = False,
) -> PVBessAssessment:
    """
    Ocenia zagrożenia i generuje procedury taktyczne dla KDR.
    """
    if not (has_pv or has_bess or has_ev):
        return PVBessAssessment(
            has_pv=False,
            has_bess=False,
            has_ev=False,
            is_daylight=is_daylight,
            risk_level="BRAK ZAGROŻEŃ SPECJALNYCH",
            pwp_required=False,
            dc_voltage_warning=None,
            toxic_gas_warning=None,
            safe_distances=[],
            tactical_instructions=["Brak zgłoszonych instalacji PV, BESS lub ładowarek EV na posesji."],
            summary_bullet="Brak instalacji PV / magazynów energii.",
        )

    instructions: List[str] = []
    safe_dist: List[str] = []
    dc_warning = None
    toxic_warning = None

    # Sprawdzenie wymogu PWP (powyżej 6.5 kWp w prawie polskim)
    pwp_required = bool(pv_capacity_kw and pv_capacity_kw > 6.5)

    # 1. Analiza PV
    if has_pv:
        if is_daylight:
            dc_warning = (
                "UWAGA: PANELE PV POD NAPIĘCIEM DC (DO 1000V)! "
                "Wyłączenie zasilania AC nie wyłącza przewodów solarnych."
            )
            safe_dist.append("Prąd wody rozproszony: min. 1 metr od modułów i falownika.")
            safe_dist.append("Prąd wody zwarty: BEZWZGLĘDNY ZAKAZ z odległości poniżej 5 metrów.")
        else:
            dc_warning = "Noc: Ryzyko porażenia DC znikome, zachować standardową ostrożność instalacji elektroenergetycznej."

        if pwp_required:
            pwp_status = "zlokalizowany i wyłączony" if pwp_switch_located else "PILNIE ZLOKALIZOWAĆ I ROZŁĄCZYĆ (złącze ZK / wejście)"
            instructions.append(f"Przeciwpożarowy Wyłącznik Prądu (PWP): {pwp_status}.")

        instructions.append("Falownik / Inwerter: nie otwierać obudowy pod napięciem; gasić proszkiem gaśniczym lub CO2.")
        instructions.append("Uwaga na nośność dachu: dodatkowe obciążenie panelami (~15-20 kg/m²), ryzyko nagłego załamania konstrukcji.")

    # 2. Analiza Magazynów Energii (BESS)
    if has_bess:
        toxic_warning = (
            "ZAGROŻENIE CHEMICZNO-TOKSYCZNE (BESS Li-ion): ryzyko gwałtownej ucieczki termicznej (Thermal Runaway). "
            "Wydzielanie skrajnie toksycznego fluorowodoru (HF), cyjanowodoru i tlenku węgla!"
        )
        instructions.append("BEZWZGLĘDNY NAKAZ: Praca wszystkich rot w aparatach powietrznych AODO.")
        instructions.append("Taktyka gaśnicza BESS: intensywne i długotrwałe chłodzenie płaszczowe dużą ilością wody.")
        instructions.append("Zabezpieczenie przed wtórnym zapłonem: dozór obiektu przez min. 12-24h.")

    # 3. Analiza Pojazdów EV
    if has_ev:
        instructions.append("Pojazd elektryczny (EV): odłączyć przewód ładowania przed podjęciem gaszenia, chłodzić baterię podwoziową.")

    # Poziom ryzyka
    if has_bess and has_pv:
        risk_level = "BARDZO WYSOKI (Kombinacja napięcia stałego DC 1000V oraz toksyczności BESS Li-ion)"
    elif has_bess:
        risk_level = "WYSOKI (Magazyn energii Li-ion, ryzyko wybuchowe i toksyczne)"
    elif has_pv and is_daylight:
        risk_level = "PODWYŻSZONY (Napięcie stałe DC na dachu i przewodach)"
    else:
        risk_level = "UMIARKOWANY"

    summary = (
        f"⚡ ZAGROŻENIA ENERGETYCZNE: "
        f"{'Fotowoltaika (PV) ' + (f'{pv_capacity_kw}kW ' if pv_capacity_kw else '') if has_pv else ''}"
        f"{'+ Magazyn energii BESS ' + (f'{bess_capacity_kwh}kWh ' if bess_capacity_kwh else '') if has_bess else ''}"
        f"{'+ Stacja EV' if has_ev else ''}. {dc_warning or ''}"
    )

    return PVBessAssessment(
        has_pv=has_pv,
        has_bess=has_bess,
        has_ev=has_ev,
        is_daylight=is_daylight,
        risk_level=risk_level,
        pwp_required=pwp_required,
        dc_voltage_warning=dc_warning,
        toxic_gas_warning=toxic_warning,
        safe_distances=safe_dist,
        tactical_instructions=instructions,
        summary_bullet=summary.strip(),
    )
