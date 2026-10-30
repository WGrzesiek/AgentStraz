# 💨 mcp-weather-safety

Serwer MCP (Model Context Protocol) integrujący dane meteorologiczne z **IMGW-PIB (Instytut Meteorologii i Gospodarki Wodnej)** oraz siatki Open-Meteo na potrzeby oceny taktycznej wiatru i wektora zadymienia dla **Kierującego Działaniem Ratowniczym (KDR) OSP/PSP**.

---

## 🛠️ Dostępne Narzędzia (Tools)

| Narzędzie | Opis |
| :--- | :--- |
| `get_tactical_wind_and_weather(lat, lon)` | Pobiera aktualny kierunek i prędkość wiatru, porywy, temperaturę i wilgotność z najbliższej stacji IMGW-PIB. Wylicza wektor znoszenia dymu. |
| `get_smoke_and_hazard_zone(lat, lon, override_wind_deg, override_speed_kmh)` | Wyznacza kątowy stożek zadymienia ($\pm 30^\circ$) oraz strefę zagrożoną dla sąsiednich posesji. Umożliwia nadpisanie kierunku wiatru obserwacją ratowników z terenu akcji. |
| `get_meteo_tactical_brief(lat, lon)` | Generuje zwięzły meldunek radiowy gotowy do wklejenia do Karty Rozpoznania Bojowego. |

---

## 🚀 Uruchomienie

### Wymagania:
- Python >= 3.10
- Narzędzie `uv` (zalecane) lub standardowy `pip`

### Uruchomienie przez `uv`:
```bash
uv run --directory mcp-servers/mcp-weather-safety python -m src.server
```

### Konfiguracja w `mcp_config.json`:
```json
{
  "mcpServers": {
    "weather-safety": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ścieżka/do/agent/mcp-servers/mcp-weather-safety",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```
