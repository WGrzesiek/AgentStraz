# 🚒 mcp-osm-fire-recon

Serwer MCP (Model Context Protocol) analizujący infrastrukturę pożarniczą na podstawie **OpenStreetMap (Overpass API)** dla potrzeb **Kierującego Działaniem Ratowniczym (KDR) OSP/PSP**.

---

## 🛠️ Dostępne Narzędzia (Tools)

| Narzędzie | Opis |
| :--- | :--- |
| `find_nearest_hydrants(lat, lon, radius_m, max_results)` | Lokalizuje hydranty w promieniu zdarzenia, podaje odległość, azymut, typ (nadziemny/podziemny), średnicę (DN80/100) oraz szacowane zapotrzebowanie na odcinki W-75. Ostrzega o wymogu stojaka i klucza podziemnego. |
| `find_water_sources(lat, lon, radius_m, max_results)` | Wyszukuje otwarte punkty czerpania wody (rzeki, stawy, jeziora, baseny ppoż.) i sugeruje odpowiedni sprzęt (motopompa M16/8 vs pompa pływająca Niagara). |
| `check_access_and_hazards(lat, lon, radius_m)` | Wykrywa oznaczone leśne dojazdy pożarowe oraz drogi gruntowe/nieutwardzone stwarzające ryzyko ugrzęźnięcia dla ciężkich wozów GCBA. |
| `get_water_supply_tactical_brief(lat, lon)` | Zbiorczy meldunek zaopatrzenia wodnego w 1 wywołaniu gotowy do przekazania rotom gaśniczym przez radio. |

---

## 🚀 Uruchomienie

### Wymagania:
- Python >= 3.10
- Narzędzie `uv` (zalecane) lub standardowy `pip`

### Uruchomienie przez `uv`:
```bash
uv run --directory mcp-servers/mcp-osm-fire-recon python -m src.server
```

### Konfiguracja w `mcp_config.json`:
```json
{
  "mcpServers": {
    "osm-fire-recon": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ścieżka/do/agent/mcp-servers/mcp-osm-fire-recon",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```
