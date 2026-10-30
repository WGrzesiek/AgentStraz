#!/usr/bin/env python3
"""Adres/GPS → darmowe źródła budynków → wspólny JSON, Markdown i HTML."""

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp-servers/mcp-geoportal/src"))
from building_client import get_building_details
from uug_client import geocode_address
from skills.water_supply_calc.building import calculate_building_water, building_water_lines
from tools.visualizer import render_html


def enrich_report(data, recon, *, suppression=None):
    result = copy.deepcopy(data)
    info = result.setdefault("incident_info", {})
    for coordinate in ("lat", "lon"):
        value = recon["coordinates"][coordinate]
        if info.get(coordinate) is not None and abs(float(info[coordinate]) - value) > 0.00001:
            raise ValueError("Lokalizacja raportu różni się od lokalizacji rozpoznania budynku.")
        info[coordinate] = value
    result["building_recon"] = recon
    result["building"] = recon["building"]
    if suppression is not None:
        result["suppression"] = suppression
    result["building_water"] = calculate_building_water(result["building"], result.get("suppression"))
    return result


def save_reports(data, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    # Sekcja Markdown korzysta bezpośrednio z tych samych obliczeń co JSON/HTML.
    lines = ["# Rozpoznanie budynku — dane do potwierdzenia w terenie",
             f"Adres: {data['incident_info'].get('address', 'nie podano')}",
             "", "## Kubatura i zapotrzebowanie wody", ""]
    lines.extend("- " + line for line in building_water_lines(data["building_water"]))
    for url in data["building_water"]["sources"]:
        lines.append("- Źródło kalkulacji: " + url)
    (output / "budynek.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "budynek.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "budynek.html").write_text(render_html(data), encoding="utf-8")
    return output.resolve()


async def main(args):
    data = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else {}
    if args.address:
        geo = await geocode_address(args.address)
        if not geo:
            raise ValueError("Nie znaleziono jednoznacznego adresu. Podaj dokładniejszy adres lub GPS.")
        lat, lon = geo.lat, geo.lon
        info = data.setdefault("incident_info", {})
        info.setdefault("address", geo.full_address)
        info["geocoding_source"] = geo.source
    elif args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    else:
        info = data.get("incident_info", {})
        lat, lon = info.get("lat"), info.get("lon")
        if lat is None or lon is None:
            raise ValueError("Podaj --address, parę --lat/--lon albo raport JSON ze współrzędnymi.")
    recon = await get_building_details(lat, lon, building_id=args.building_id, cache_dir=args.cache_dir)
    suppression = dict(data.get("suppression", {}))
    if args.fire_area_m2 is not None:
        suppression["fire_area_m2"] = args.fire_area_m2
    if args.duration_min is not None:
        suppression["duration_min"] = args.duration_min
    data = enrich_report(data, recon, suppression=suppression)
    output = save_reports(data, args.output_dir)
    print(f"Status budynku: {recon['status']}; raporty: {output}")
    for candidate in recon["candidates"][:10]:
        print(f"  {candidate['id']} | {candidate['source']} | {candidate['distance_m']} m | {candidate['footprint_area_m2']} m²")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--input", help="Istniejący raport JSON do uzupełnienia")
    parser.add_argument("--building-id", help="Potwierdzone id z listy kandydatów")
    parser.add_argument("--cache-dir")
    parser.add_argument("--fire-area-m2", type=float, help="Rozpoznana powierzchnia gaszenia (opcjonalna)")
    parser.add_argument("--duration-min", type=float, help="Założony czas działań (opcjonalny)")
    parser.add_argument("--output-dir", default="reports/building")
    arguments = parser.parse_args()
    if (arguments.lat is None) != (arguments.lon is None):
        parser.error("--lat i --lon należy podać razem")
    if arguments.address and arguments.lat is not None:
        parser.error("wybierz adres albo współrzędne")
    try:
        asyncio.run(main(arguments))
    except ValueError as error:
        parser.exit(2, f"Błąd: {error}\n")
