"""Szacunek geometrii i wody dla budynku mieszkalnego; bez domyślnych wymiarów."""

import math

SOURCE_URL = "https://zpe.gov.pl/a/obliczanie-sil-i-srodkow-podczas-zwalczania-pozarow/D15L55ToZ"
PSP_SOURCE_URL = "https://www.gov.pl/attachment/2b06ddfe-71f4-4fac-a55b-e6b18cde7808"
SOURCE_CHECKED = "2026-10-30"


def _positive(value, name, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: wymagana liczba.")
    if not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        raise ValueError(f"{name}: wymagana skończona liczba {'nieujemna' if allow_zero else 'dodatnia'}.")
    return value


def calculate_building_water(building=None, suppression=None):
    """Kontrakt JSON opisano w docs/building_water.md.

    V=A*h to model prostopadłościanu, nie pomiar kubatury brutto wg norm.
    A_g=V_wew/h_pom*f jest jawnym scenariuszem, nie prawem fizycznym.
    Natężenie 0.08–0.10 l/(m² s) pochodzi z tabeli dla budynków mieszkalnych.
    """
    building, suppression = building or {}, suppression or {}
    for key in ("volume_m3", "footprint_area_m2", "height_m", "interior_volume_m3", "mean_room_height_m"):
        if building.get(key) is not None:
            _positive(building[key], key)
    for key in ("fire_area_m2", "duration_min"):
        if suppression.get(key) is not None:
            _positive(suppression[key], key)
    fraction = suppression.get("affected_fraction")
    if fraction is not None:
        _positive(fraction, "affected_fraction")
        if fraction > 1:
            raise ValueError("affected_fraction musi być w zakresie (0, 1].")

    volume = building.get("volume_m3")
    volume_method = "Kubatura podana; wymaga potwierdzenia źródła i zakresu."
    if volume is not None and building.get("recon_status") == "selected":
        volume_method = "Szacunkowa kubatura bryły zewnętrznej: obrys × wysokość modelu; dach i wnętrze nie są odwzorowane dokładnie."
    if volume is None and building.get("footprint_area_m2") is not None and building.get("height_m") is not None:
        volume = building["footprint_area_m2"] * building["height_m"]
        _positive(volume, "volume_m3")
        volume_method = "V = powierzchnia zabudowy × wysokość; uproszczona bryła prostopadłościenna (szacunek)."
    if volume is None:
        volume_method = "Brak kubatury: podaj volume_m3 lub footprint_area_m2 i height_m."

    area = suppression.get("fire_area_m2")
    area_method = "Powierzchnia gaszenia podana przez użytkownika/KDR."
    if area is None:
        interior = building.get("interior_volume_m3")
        height = building.get("mean_room_height_m")
        if interior is not None and height is not None and fraction is not None:
            area = interior / height * fraction
            _positive(area, "fire_area_m2")
            area_method = "A_g = kubatura wewnętrzna / średnia wysokość pomieszczeń × udział objęty gaszeniem; scenariusz szacunkowy."
        else:
            area_method = "Brak powierzchni gaszenia: podaj fire_area_m2 albo interior_volume_m3, mean_room_height_m i affected_fraction. Kubatura bryły nie zastępuje kubatury wewnętrznej."

    duration = suppression.get("duration_min")
    result = {
        "status": "estimated" if area is not None else "insufficient_data",
        "building": dict(building), "suppression": dict(suppression),
        "volume_m3": volume, "volume_method": volume_method,
        "fire_area_m2": area, "area_method": area_method,
        "intensity_l_s_m2": {"min": 0.08, "max": 0.10},
        "flow_l_s": None, "flow_l_min": None, "water_volume_l": None,
        "duration_min": duration,
        "sources": [SOURCE_URL, PSP_SOURCE_URL], "sources_checked_on": SOURCE_CHECKED,
        "warnings": [
            "Szacunek natarcia dla budynku mieszkalnego do oceny KDR. Nie obejmuje obrony, strat ani rezerwy; nie stosować automatycznie do piwnic, poddaszy, PV/BESS ani innych materiałów.",
            "To kalkulacja taktyczna Q = A_g × I, a nie wymagane prawem zaopatrzenie do zewnętrznego gaszenia. Nie potwierdza wydajności hydrantów.",
        ],
    }
    if area is not None:
        result["flow_l_s"] = {"min": area * 0.08, "max": area * 0.10}
        result["flow_l_min"] = {key: value * 60 for key, value in result["flow_l_s"].items()}
        if duration is not None:
            result["water_volume_l"] = {key: value * duration for key, value in result["flow_l_min"].items()}
    return result


def building_water_lines(result):
    """Wspólne treści do Markdown/HTML, bez parsowania tekstu raportu."""
    def span(values, unit):
        return f"{values['min']:.1f}–{values['max']:.1f} {unit}"

    lines = [
        f"Kubatura budynku: {result['volume_m3']:.1f} m³" if result["volume_m3"] is not None else "Kubatura budynku: brak danych",
        result["volume_method"],
        f"Źródło wymiarów: {result['building'].get('source') or 'nie podano'}; czas danych: {result['building'].get('observed_at') or 'nie podano'}.",
        result["area_method"],
    ]
    for key, label, unit in [("footprint_area_m2", "Powierzchnia zabudowy", "m²"), ("height_m", "Wysokość", "m")]:
        if result["building"].get(key) is not None:
            lines.append(f"{label}: {result['building'][key]:.2f} {unit}")
    building = result["building"]
    if building.get("source_url"):
        lines.append(f"Źródło geometrii: {building['source_url']}")
    if building.get("retrieved_at"):
        lines.append(f"Odczyt danych: {building['retrieved_at']} (to nie data pomiaru).")
    if building.get("model_cached_at"):
        lines.append(f"Indeks modeli w cache: {building['model_cached_at']}")
    if building.get("model_package"):
        package = building["model_package"]
        state = {"cached": "wykorzystano pobraną paczkę i gotowy indeks",
                 "downloaded": "pobrano automatycznie i zbudowano indeks",
                 "indexed_from_cache": "zbudowano indeks z wcześniej pobranej paczki"}.get(package.get("status"), "stan niepotwierdzony")
        lines.append(f"Paczka powiatu (TERYT {package.get('county_code', 'nieznany')}): {state}.")
    if building.get("recon_status"):
        label = {"selected": "wybrano obiekt — wymaga potwierdzenia w terenie",
                 "selection_required": "wymagany wybór obiektu",
                 "unavailable": "brak danych do dopasowania"}.get(building["recon_status"], "niepotwierdzone")
        lines.append(f"Dopasowanie budynku: {label}")
    for check in building.get("source_checks", []):
        label = {"ok": "dane dostępne", "no_data": "brak obiektów w odpowiedzi",
                 "unavailable": "źródło niedostępne"}.get(check["status"], "niepotwierdzona")
        lines.append(f"Dostępność {check['source']}: {label}")
    lines.extend(building.get("data_warnings", []))
    lines.extend(building.get("candidate_summary", []))
    if result["fire_area_m2"] is not None:
        lines += [f"Powierzchnia gaszenia: {result['fire_area_m2']:.1f} m²",
                  "Intensywność: 0,08–0,10 l/(m²·s) = 4,8–6,0 l/(m²·min)",
                  f"Wydatek wody: {span(result['flow_l_s'], 'l/s')} ({span(result['flow_l_min'], 'l/min')})"]
    if result["water_volume_l"] is not None:
        lines.append(f"Zapas na {result['duration_min']:g} min: {span(result['water_volume_l'], 'l')}")
    else:
        lines.append("Zapas wody: brak danych — wymagany czas działań i powierzchnia gaszenia.")
    lines.extend(result["warnings"])
    return lines
