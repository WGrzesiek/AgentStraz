"""Szkic 2D rzeczywistych obrysów w EPSG:2180, bez domyślnych budynków."""

import math
from html import escape


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Nieprawidłowa współrzędna szkicu.")
    return value


def render_building_sketch(building):
    plan = building.get("site_plan") or {}
    empty = '<p class="text-sm text-slate-400">Brak geometrii do szkicu budynków. Wymagane obrysy z paczki modeli, EGiB lub OSM.</p>'
    content = empty
    features = plan.get("features") or []
    if features and plan.get("crs") == "EPSG:2180":
        try:
            content = _render_plan(plan)
        except (ValueError, KeyError, TypeError, IndexError):
            content = empty
    return (
        '<section class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl card-box" id="building-sketch">'
        '<h2 class="font-bold text-sm text-slate-100 uppercase mb-3">Szkic budynków — obrysy z danych źródłowych</h2>'
        + content + '</section>'
    )


def _render_plan(plan):
    east = _number(plan["origin_easting"])
    north = _number(plan["origin_northing"])
    radius = _number(plan["radius_m"])
    if not 5 <= radius <= 1000:
        raise ValueError("Nieprawidłowy zasięg szkicu.")
    scale = 240 / radius
    selected_id = plan.get("selected_id")
    # Wybrany obiekt B1; pozostałe w kolejności stabilnej dla identyfikatorów.
    features = sorted(plan["features"], key=lambda f: (f.get("id") != selected_id, str(f.get("id", ""))))
    paths, rows, labels = [], [], []

    def xy(point):
        e, n = _number(point[0]), _number(point[1])
        if abs(e-east) > 100000 or abs(n-north) > 100000:
            raise ValueError("Obrys nie jest w lokalnym układzie szkicu.")
        return 290 + (e-east)*scale, 290 - (n-north)*scale

    for index, feature in enumerate(features[:200], 1):
        commands, points = [], []
        for polygon in feature["polygons"]:
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Niezamknięty obrys szkicu.")
                transformed = [xy(point) for point in ring]
                commands.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in transformed) + " Z")
            points.extend(xy(point) for point in polygon[0])
        if not points:
            continue
        selected = feature.get("id") == selected_id
        code = f"B{index}"
        identifier = escape(str(feature.get("id", "")))
        source = escape(str(feature.get("source") or "nie podano"))
        date = escape(str(feature.get("observed_at") or "nie podano"))
        height = feature.get("height_m")
        height_label = f"{_number(height):.2f} m" if height is not None else "brak danych"
        area = feature.get("footprint_area_m2")
        area_label = f"{_number(area):.2f} m²" if area is not None else "brak danych"
        title = f"{code}: {identifier}; wysokość {height_label}; obrys {area_label}; {source}; czas danych {date}"
        paths.append(f'<path data-building-id="{identifier}" d="{" ".join(commands)}" fill="{"#b91c1c" if selected else "#334155"}" '
                     f'stroke="{"#fca5a5" if selected else "#94a3b8"}" stroke-width="{2 if selected else 1}" fill-rule="evenodd"><title>{title}</title></path>')
        x = (min(p[0] for p in points) + max(p[0] for p in points)) / 2
        y = (min(p[1] for p in points) + max(p[1] for p in points)) / 2
        labels.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" font-size="10" font-weight="bold" '
                      f'fill="#fff" stroke="#0f172a" stroke-width="2.5" paint-order="stroke">{code}</text>')
        rows.append(f'<tr><td>{code}{" — analizowany" if selected else ""}</td><td>{height_label}</td><td>{area_label}</td>'
                    f'<td>{identifier}<br>{source}; dane: {date}</td></tr>')
    if not paths:
        raise ValueError("Brak obrysów.")
    bar_m = max((value for value in (1, 2, 5, 10, 20, 25, 50, 100, 200) if value <= radius/2), default=1)
    grid = "".join(f'<path d="M{v} 50V530 M50 {v}H530" stroke="#1e293b" stroke-width="1"/>' for v in range(50, 531, 60))
    selected_note = ("Czerwony: analizowany budynek. Szare: otaczające budynki." if selected_id
                     else "Nie wybrano budynku — pokazano dostępne obrysy do weryfikacji.")
    return f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 580 590" role="img" aria-label="Szkic obrysów budynków w skali, północ siatkowa u góry" style="width:100%;height:auto;max-width:600px;background:#020617;border-radius:8px">
      <defs><clipPath id="building-plan-clip"><rect x="50" y="50" width="480" height="480"/></clipPath></defs>
      <rect width="580" height="590" fill="#020617"/>{grid}
      <g clip-path="url(#building-plan-clip)">{''.join(paths)}{''.join(labels)}</g>
      <rect x="50" y="50" width="480" height="480" fill="none" stroke="#475569"/>
      <path d="M545 85V35 M545 35L539 48 M545 35L551 48" stroke="#e2e8f0" fill="none" stroke-width="2"/>
      <text x="545" y="26" text-anchor="middle" fill="#fff" font-size="12">N</text>
      <circle cx="290" cy="290" r="4" fill="#fff" stroke="#020617" stroke-width="2"><title>Punkt adresowy / punkt zgłoszenia; położenie ogniska pożaru niepotwierdzone</title></circle>
      <path d="M50 553H{50+bar_m*scale:.2f} M50 548V558 M{50+bar_m*scale:.2f} 548V558" stroke="#e2e8f0" fill="none" stroke-width="2"/>
      <text x="50" y="575" fill="#e2e8f0" font-size="12">{bar_m} m</text>
      <text x="530" y="575" text-anchor="end" fill="#94a3b8" font-size="11">Zasięg: ±{radius:g} m · EPSG:2180</text>
    </svg>
    <p class="text-xs text-slate-300 mt-2">{selected_note} Biały punkt: lokalizacja zgłoszenia/adresu.</p>
    <p class="text-xs text-slate-400 mt-1">Rzut 2D podstaw budynków. Północ siatkowa EPSG:2180; skala dotyczy obrysów, nie wielkości oznaczeń. Brak danych o drogach i przejściach między budynkami.</p>
    <details class="mt-3 text-xs"><summary class="cursor-pointer text-slate-300">Budynki na szkicu — wysokości, powierzchnie i źródła ({len(rows)})</summary>
      <div style="overflow-x:auto"><table class="w-full text-left mt-2" style="border-collapse:collapse"><thead><tr><th>Obiekt</th><th>Wysokość</th><th>Obrys</th><th>Identyfikator / źródło</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
    </details>'''
