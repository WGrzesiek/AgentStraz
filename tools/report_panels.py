"""Czytelna kalkulacja i wspólny plan z rzeczywistymi współrzędnymi."""
import copy
import importlib.util
import math
from pathlib import Path
from html import escape
from tools.building_sketch import _render_plan


def water_panel(result):
    def value(number, unit):
        return f'{number:.1f} {unit}' if number is not None else 'brak danych'
    def span(values, unit):
        return f"{values['min']:.1f}–{values['max']:.1f} {unit}"
    cards = [('Powierzchnia zabudowy', value(result['building'].get('footprint_area_m2'), 'm²')),
             ('Wysokość modelu', value(result['building'].get('height_m'), 'm')),
             ('Kubatura bryły', value(result['volume_m3'], 'm³'))]
    if result['fire_area_m2'] is not None:
        cards += [('Przyjęta powierzchnia gaszenia', value(result['fire_area_m2'], 'm²')),
                  ('Wymagany przepływ', span(result['flow_l_s'], 'l/s')),
                  ('Woda na minutę', span(result['flow_l_min'], 'l/min'))]
    html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-top:12px">'
    for label, number in cards:
        html += f'<div style="background:#0f172a;padding:12px;border-radius:8px"><div class="text-xs text-slate-400">{label}</div><strong style="font-size:18px;color:#bae6fd">{number}</strong></div>'
    html += '</div>'
    if result['fire_area_m2'] is not None:
        note = result['suppression'].get('area_assumption') or result['area_method']
        html += f'<p class="text-xs mt-3">{escape(note)}</p><p class="text-xs mt-2">Q = powierzchnia gaszenia × 0,08–0,10 l/(m²·s) = 4,8–6,0 l/(m²·min).</p>'
        html += '<table class="w-full text-sm mt-3"><caption class="text-left text-xs">Zapas wody — przykładowe czasy ciągłego podawania (założenia)</caption><thead><tr><th>Czas</th><th>Potrzebna woda</th></tr></thead><tbody>'
        for minutes in (10, 20, 30):
            volumes = {k: v * minutes / 1000 for k, v in result['flow_l_min'].items()}
            volume_label = f"{volumes['min']:.2f}–{volumes['max']:.2f} m³".replace(".", ",")
            html += f'<tr><td>{minutes} min</td><td>{volume_label}</td></tr>'
        html += '</tbody></table>'
        if result['water_volume_l'] is not None:
            html += f'<p class="text-sm mt-2">Zapas na zadane {result["duration_min"]:g} min: {span(result["water_volume_l"], "l")}</p>'
    else:
        html += '<p class="text-sm mt-3">Brak przyjętej powierzchni gaszenia — nie obliczono przepływu ani zapasu.</p>'
    html += '<p class="text-xs text-slate-400 mt-3">Scenariusz do oceny KDR. Obrys nie określa liczby kondygnacji ani faktycznej powierzchni pożaru. Bez obrony, strat i rezerwy; wydajność punktów wodnych niepotwierdzona.</p>'
    return html


def _report_coords():
    # Ten sam projektowy przelicznik co geokodowanie; działa również bez pyproj.
    spec = importlib.util.spec_from_file_location('report_coords', Path(__file__).resolve().parents[1] / 'mcp-servers/mcp-geoportal/src/coords.py')
    coords = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coords)
    return coords


def combined_plan(data):
    try:
        return _combined_plan(data)
    except (ValueError, KeyError, TypeError, IndexError, OverflowError):
        return '<section id="combined-plan"><h2>Plan łączony — obrysy budynków i punkty wodne</h2><p>Brak poprawnej geometrii do wspólnego szkicu.</p></section>'


def _combined_plan(data):
    plan = copy.deepcopy((data.get('building') or {}).get('site_plan') or {})
    if not plan.get('features') or plan.get('crs') != 'EPSG:2180':
        return '<section id="combined-plan"><h2>Plan łączony — obrysy budynków i punkty wodne</h2><p>Brak geometrii do wspólnego szkicu.</p></section>'
    coords = _report_coords()
    east, north = plan['origin_easting'], plan['origin_northing']
    points, rows = [], []
    radius = plan['radius_m']
    origin_lat, origin_lon = coords.puwg1992_to_wgs84(north, east)
    water = data.get('water_supply') or {}
    for kind, items in [('W', water.get('open_water_intakes', [])), ('H', water.get('hydrants', []))]:
        for i, item in enumerate(items, 1):
            try:
                location_note = ''
                if item.get('lat') is not None and item.get('lon') is not None:
                    lat, lon = float(item['lat']), float(item['lon'])
                else:
                    distance_input = float(item['distance_m'])
                    bearing_input = float(item['bearing_deg'])
                    if not (math.isfinite(distance_input) and 0 <= distance_input <= 500
                            and math.isfinite(bearing_input) and 0 <= bearing_input <= 360):
                        continue
                    # Punkt z podanej odległości i azymutu geograficznego.
                    phi, lam = math.radians(origin_lat), math.radians(origin_lon)
                    angle, arc = math.radians(bearing_input), distance_input / 6371000
                    phi2 = math.asin(math.sin(phi)*math.cos(arc) + math.cos(phi)*math.sin(arc)*math.cos(angle))
                    lam2 = lam + math.atan2(math.sin(angle)*math.sin(arc)*math.cos(phi), math.cos(arc)-math.sin(phi)*math.sin(phi2))
                    lat, lon = math.degrees(phi2), math.degrees(lam2)
                    location_note = 'Pozycja orientacyjna z podanego azymutu i odległości; '

                if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                n, e = coords.wgs84_to_puwg1992(lat, lon)
                distance = math.hypot(e-east, n-north)
                if distance > 500:
                    continue
                bearing = math.degrees(math.atan2(e-east, n-north)) % 360
                direction = ['N','NE','E','SE','S','SW','W','NW'][int((bearing+22.5)//45)%8]
                code = f'{kind}{i}'
                in_frame = max(abs(e-east), abs(n-north)) <= radius
                points.append((code, e, n, distance, direction, in_frame))
                frame_note = '' if in_frame else ' · poza kadrem szkicu'
                name = escape(str(item.get('name') or item.get('location_desc') or 'Hydrant'))
                rows.append(f'<li><strong>{code} · ~{distance:.0f} m · {direction}{frame_note}</strong> — {name}<br><span class="text-slate-400">{location_note}GPS {lat:.7f}, {lon:.7f}; {escape(str(item.get("source_retrieved_at") or item.get("retrieved_at") or "czas odczytu niepodany"))}</span></li>')
            except (KeyError, TypeError, ValueError):
                continue
    # Zachowujemy dokładnie kadr i skalę źródłowego szkicu budynków.
    scale = 240 / plan['radius_m']
    overlays = ['<defs><marker id="water-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#38bdf8"/></marker></defs>']
    wind = (data.get('weather') or {}).get('wind_deg')
    speed = (data.get('weather') or {}).get('wind_speed_kmh')
    if isinstance(wind, (int,float)) and math.isfinite(wind) and isinstance(speed,(int,float)) and speed > 0:
        # Przelicz kierunek geograficzny dymu na północ siatkową szkicu.
        info = data.get('incident_info') or {}
        if info.get('lat') is not None and info.get('lon') is not None:
            lat, lon = info['lat'], info['lon']
            a = math.radians((wind+180)%360)
            n0,e0 = coords.wgs84_to_puwg1992(lat,lon)
            n1,e1 = coords.wgs84_to_puwg1992(lat+100*math.cos(a)/111320,lon+100*math.sin(a)/(111320*math.cos(math.radians(lat))))
            grid_angle = math.atan2(e1-e0,n1-n0)
            half = math.radians(float((data.get('weather') or {}).get('hazard_cone_span_deg',60))/2)
            vertices = [(290+235*math.sin(grid_angle+d),290-235*math.cos(grid_angle+d)) for d in (-half,half)]
            overlays.append(f'<path d="M290 290L{vertices[0][0]:.2f} {vertices[0][1]:.2f} A235 235 0 0 1 {vertices[1][0]:.2f} {vertices[1][1]:.2f} Z" fill="#ef4444" opacity="0.23"><title>Warunkowy sektor zadymienia według zapisanego wiatru; zasięg poglądowy</title></path>')
    for code,e,n,distance,direction,in_frame in points:
        dx, dy = (e-east)*scale, -(n-north)*scale
        if not in_frame:
            # Utnij promień na granicy stałego kadru, bez grotu i symbolu celu.
            fraction = 240 / max(abs(dx), abs(dy))
            dx, dy = dx*fraction, dy*fraction
        x,y = 290+dx,290+dy
        mx,my = (290+x)/2,(290+y)/2
        angle = math.degrees(math.atan2(y-290,x-290))
        if angle > 90 or angle < -90:
            angle += 180
        marker = ' marker-end="url(#water-arrow)"' if in_frame else ''
        suffix = '' if in_frame else ' · poza kadrem'
        overlays.append(f'<line data-water-id="{code}" x1="290" y1="290" x2="{x:.2f}" y2="{y:.2f}" stroke="#38bdf8" stroke-width="2"{marker}/><text transform="translate({mx:.2f} {my:.2f}) rotate({angle:.2f})" y="-6" text-anchor="middle" font-size="10" fill="#bae6fd" stroke="#020617" stroke-width="3" paint-order="stroke">{code} ~{distance:.0f} m · {direction}{suffix}</text>')
        if in_frame:
            overlays.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#38bdf8"/><text x="{x+9:.2f}" y="{y-9:.2f}" font-size="12" fill="#bae6fd">{code}</text>')
    content = _render_plan(plan).replace('building-plan-clip','combined-plan-clip')
    content = content.replace('<rect x="50" y="50" width="480" height="480" fill="none"', '<g clip-path="url(#combined-plan-clip)">'+''.join(overlays)+'</g><rect x="50" y="50" width="480" height="480" fill="none"')
    return '<section id="combined-plan" class="bg-slate-900 border border-slate-800 rounded-xl p-4 card-box"><h2 class="font-bold text-slate-100 mb-3">🎯 Plan łączony — obrysy budynków i punkty wodne</h2>'+content+'<p class="text-xs text-sky-200 mt-3">Rzeczywiste obrysy budynków w stałej skali i kadrze. Warstwa orientacyjna: punkty do 500 m z azymutem podanym lub obliczonym ze współrzędnych. Dla punktów poza kadrem linia kończy się na jego granicy bez grotu i symbolu punktu; etykieta podaje pełną odległość do źródła wody. Niebieskie strzałki: kierunki do punktów wodnych. Odległości do oznaczonych współrzędnych w linii prostej, nie trasy dojścia ani długości węży. Symbole punktowe nie przedstawiają obrysów zbiorników. Czerwony: warunkowy sektor dymu, bez modelowania zasięgu.</p><ul class="text-xs space-y-3 mt-3">'+''.join(rows)+'</ul><p class="text-xs text-slate-400 mt-3">Możliwość poboru, dojazd i sprawność wymagają potwierdzenia. Zabudowa jest dostępna tylko w zakresie pobranych obrysów. Kierunki punktów odnoszą się do północy siatkowej EPSG:2180. Dane i pogoda zachowują czas pierwotnego rozpoznania.</p></section>'
