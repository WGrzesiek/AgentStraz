#!/usr/bin/env python3
"""Uzupełnia raport JSON/HTML o hydranty Geoportalu wokół ogniska pożaru."""
import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'mcp-servers/mcp-geoportal/src'))
from hydrant_client import get_hydrants_near_point
from uug_client import geocode_address
from tools.visualizer import render_html


def enrich_hydrants(data, recon):
    result = copy.deepcopy(data)
    info = result.setdefault('incident_info', {})
    for key in ('lat', 'lon'):
        value = recon['origin'][key]
        if info.get(key) is not None and abs(float(info[key])-value) > 0.00001:
            raise ValueError('Ognisko pożaru różni się od lokalizacji raportu.')
        info[key] = value
    water = result.setdefault('water_supply', {})
    # Zachowaj pozostałe źródła, w tym OSM, jako oddzielne niezweryfikowane dane.
    # Nie łącz lokalizacji bez potwierdzenia tożsamości hydrantów.
    if water.get('hydrants') and not water.get('hydrant_recon'):
        water['other_source_hydrants'] = water['hydrants']
    water['hydrants'] = recon['hydrants']
    water['hydrant_recon'] = recon
    return result


def hydrant_lines(recon):
    lines = [f"Geoportal K-GESUT — status: {recon['status']}; promień {recon['radius_m']} m.",
             f"Źródło: {recon['source_url']} | Pobrano: {recon['retrieved_at']}", recon['notice']]
    for i, h in enumerate(recon['hydrants']):
        label = 'Najbliższy odczytany hydrant' if i == 0 else 'Hydrant alternatywny'
        lines.append(f"{label} {h['id']}: {h['distance_m']} m w linii prostej, "
                     f"{h['location_desc']}; ~{h['estimated_w75_hoses']} odcinków W-75 "
                     f"(szacunek +15%); typ/DN nieznane; data źródła: {h['source_date'] or 'nie podano'}.")
    if not recon['hydrants']:
        lines.append('Nie wskazano hydrantu — brak potwierdzonych danych lokalizacyjnych z tej usługi.')
    return lines


async def main(args):
    data = json.loads(Path(args.input).read_text()) if args.input else {}
    if args.address:
        geo = await geocode_address(args.address)
        if not geo:
            raise ValueError('Nie znaleziono jednoznacznego adresu. Podaj GPS ogniska pożaru.')
        lat, lon = geo.lat, geo.lon
        data.setdefault('incident_info', {}).setdefault('address', geo.full_address)
    elif args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    else:
        info = data.get('incident_info', {})
        lat, lon = info.get('lat'), info.get('lon')
        if lat is None or lon is None:
            raise ValueError('Podaj adres, GPS albo raport JSON ze współrzędnymi.')
    recon = await get_hydrants_near_point(lat, lon, args.radius_m)
    data = enrich_hydrants(data, recon)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'hydranty.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'hydranty.html').write_text(render_html(data), encoding='utf-8')
    (output / 'hydranty.md').write_text('🚒 ZAOPATRZENIE WODNE:\n' + '\n'.join(hydrant_lines(recon)) + '\n', encoding='utf-8')
    print(f"Status: {recon['status']}; hydranty: {len(recon['hydrants'])}; raport: {output.resolve()}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input')
    parser.add_argument('--address')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--radius-m', type=int, default=500)
    parser.add_argument('--output-dir', default='reports/hydrants')
    args = parser.parse_args()
    if (args.lat is None) != (args.lon is None) or (args.address and args.lat is not None):
        parser.error('Podaj adres albo parę --lat/--lon.')
    try:
        asyncio.run(main(args))
    except ValueError as error:
        parser.exit(2, f'Błąd: {error}\n')
