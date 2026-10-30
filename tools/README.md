# 🛠️ Narzędzie Wizualizacji Karty Rozpoznania Bojowego KDR (HTML)

Moduł `tools.visualizer` umożliwia automatyczne generowanie interaktywnej **Karty Rozpoznania Bojowego KDR** w formacie pojedynczego, responsywnego pliku HTML.

---

## 🚀 Kluczowe Funkcjonalności

1. **Wektorowy Schemat Taktyczny Terenu (SVG):**
   - Promień 500 m wokół obiektu (pierścienie odległości 100m, 200m, 300m, 500m).
   - Dynamiczny **stożek zadymienia i znoszenia skażeń** obliczany na podstawie kierunku wiatru.
   - Oznaczenie hydrantów z podziałem na nadziemne i podziemne wraz z liczbą odcinków W-75 przekazaną w danych.
   - Oznaczenia punktów wodnych ze znanym azymutem, w promieniu do 500 m; media opisane w osobnych kartach.
   - SVG nie wymaga map zewnętrznych; pełne stylowanie HTML wymaga zewnętrznego skryptu Tailwind.
2. **Kalkulator Zaopatrzenia Wodnego:**
   - Prezentacja liczby odcinków W-75 z danych wejściowych; w integracji ze skillami oblicza ją `water_supply_calc`.
   - Ostrzeżenie i wymóg sprzętowy dla hydrantów podziemnych (*"Wymagany stojak hydrantowy i klucz podziemny"*).
3. **Meteo i Róża Wiatrów:**
   - Tarcza wiatrowskazu, porywy, prędkość w km/h i m/s.
   - Wykaz obiektów bezpośrednio zagrożonych w sektorze zawietrznym.
4. **Zagrożenia i Media (GESUT):**
   - Gazociąg (ciśnienie, zasuwa przyłącza).
   - Energetyka (linie napowietrzne, trafo, zakaz zwartego prądu gaśniczego).
   - Dostępność dojazdu dla wozów GCBA.
5. **Generowanie Meldunku Radiowego:**
   - Gotowy tekst do zameldowania dyspozytorowi (SKKP) z przyciskiem szybkiego kopiowania do schowka.
6. **Tryb Drukuj / PDF:**
   - Zoptymalizowany arkusz stylów do natychmiastowego druku karty w kabinie wozu bojowego.

---

## 💻 Użycie z Wiersza Poleceń (CLI)

```bash
# 1. Generowanie przykładowej karty (Demo)
python tools/visualizer.py --demo --output karta_demo.html

# 2. Generowanie z pliku JSON
python tools/visualizer.py --input examples/sample_recon.json --output wynik.html

# 3. Generowanie ze standardowego meldunku Markdown (AGENTS.md)
python tools/visualizer.py --text-input examples/sample_recon.md --output wynik.html

# 4. Automatyczne otwarcie w przeglądarce
python tools/visualizer.py --demo --open
```

---

## 🐍 Użycie jako Moduł Python

```python
from tools.visualizer import render_html, parse_text_recon, generate_report_file

# Parsowanie raportu tekstowego i generowanie HTML
html_str = render_html(dane_raportu)

# Zapis do pliku
generate_report_file("examples/sample_recon.json", "karta_wynikowa.html")
```

## Integracja ze skillami

`python3 skills/demo_runner.py --output-dir reports` generuje Markdown, JSON i HTML z tych samych wyników przez `tools.skill_report.build_visualizer_data`. Parser tekstowy obsługuje podstawowy szablon AGENTS.md. Braki danych nie są uzupełniane z demo.

## Hydranty Geoportalu K-GESUT

```bash
python3 tools/hydrant_recon.py --address "Łętkowice 25" --radius-m 500
# Ognisko pożaru wskazane dokładnym GPS; uzupełnienie istniejącego raportu:
python3 tools/hydrant_recon.py --input raport.json --radius-m 1500 --output-dir reports/hydrants
```

Zwraca JSON, HTML i sekcję Markdown zaopatrzenia wodnego. Ognisko to podany GPS
lub punkt adresowy (nie automatycznie środek płonącego budynku). Wyniki są sortowane
po odległości w linii prostej, zawierają GPS, kierunek, źródło/czas odczytu i datę
rekordu. Szacunek W-75 uwzględnia 15% naddatku, wymaga sprawdzenia trasy.
Nie określa typu hydrantu, DN, wydajności ani sprawności na podstawie symbolu.
MCP: `get_hydrants_near_point(lat, lon, radius_m=500)`; automatycznie także
`full_site_recon`, pole `water_supply` przekazuj bezpośrednio do wizualizatora.

Źródło: https://mapy.geoportal.gov.pl/wss/geosrv/MapServer_KGESUT_WMS/wms
Warstwa `hydranty`, WMS 1.3 GetFeatureInfo/GML. WFS GetFeature na tej usłudze
podczas testu 30.10.2026 wymagał autoryzacji, dlatego używany jest publiczny WMS.
Zapytanie obszarowe wykorzystuje obraz 3×3 i `MAP_RESOLUTION=1`; geometrie punktów
są filtrowane do zadanego promienia (10–3000 m). Przy limicie odpowiedzi lub
nieodczytanej geometrii status `partial`: najbliższy tylko spośród odczytanych.
`no_data` oznacza brak wyników w usłudze, `unavailable` błąd/awarię. Żaden z nich
nie oznacza braku hydrantów w terenie. Pozostałe źródła istniejącego raportu
zachowane są w `other_source_hydrants`, bez automatycznego scalania tożsamości.
