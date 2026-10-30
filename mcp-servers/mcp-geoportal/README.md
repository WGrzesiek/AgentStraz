# 🌍 mcp-geoportal-gov-pl

Serwer MCP (Model Context Protocol) integrujący oficjalne polskie usługi geodezyjne i przestrzenne **Głównego Urzędu Geodezji i Kartografii (GUGiK) / Geoportal.gov.pl**.

Zaprojektowany specjalnie pod kątem wsparcia **Kierującego Działaniem Ratowniczym (KDR) w Ochotniczej i Państwowej Straży Pożarnej (OSP/PSP)**.

---

## 🛠️ Dostępne Narzędzia (Tools)

| Narzędzie | Opis |
| :--- | :--- |
| `geocode_address(address)` | Zamiana adresu tekstowego na współrzędne GPS (WGS84) i PUWG 1992 przez bazę PRG/EMUiA. |
| `get_parcel_info(lat, lon)` | Identyfikacja działki katastralnej (numer, TERYT, gmina, powiat, obrys WKT) przez ULDK. |
| `get_utilities_near_point(lat, lon, radius_m)` | Wykrywanie sieci podziemnych z bazy GESUT (gazociągi n/c, ś/c, w/c, przyłącza, linie kablowe i napowietrzne, stacje trafo). |
| `get_utilities_map_url(lat, lon, box_size_m)` | Generowanie bezpośredniego adresu URL do rastrowej mapy uzbrojenia terenu (WMS GetMap) do wyświetlenia na tablecie. |
| `full_site_recon(address_or_coords)` | Kompleksowe rozpoznanie adresu w jednym wywołaniu (współrzędne + działka + media). |

---

## 🚀 Uruchomienie

### Wymagania:
- Python >= 3.10
- Narzędzie `uv` (zalecane) lub standardowy `pip`

### Uruchomienie przez `uv` (bez instalacji globalnej):
```bash
uv run --directory mcp-servers/mcp-geoportal python -m src.server
```

### Konfiguracja w Antigravity / Claude Desktop (`mcp_config.json`):
```json
{
  "mcpServers": {
    "geoportal": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ścieżka/do/agent/mcp-servers/mcp-geoportal",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```

---

## 📡 Oficjalne Endpointy GUGiK wykorzystywane przez serwer:
1. **PRG/EMUiA (UUG):** `https://services.gugik.gov.pl/uug`
2. **ULDK (Działki):** `https://uldk.gugik.gov.pl/`
3. **KIUT (GESUT WMS):** `https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaUzbrojeniaTerenu`
