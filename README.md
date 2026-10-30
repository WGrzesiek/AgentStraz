# 🚒 AgentStraz — asystent rozpoznania dla KDR OSP/PSP

Agent zbiera dane o miejscu zdarzenia na podstawie adresu, GPS, działki lub zgłoszenia SWD/e-Remiza. Łączy informacje o wodzie, pogodzie, infrastrukturze i dojeździe, aby przygotować Kartę Rozpoznania Miejsca Zdarzenia oraz projekt meldunku radiowego.

Wspiera przygotowanie zastępu i ocenę sytuacji przez KDR. Brak wpisu w źródle nie potwierdza braku zagrożenia, a obliczenia nie potwierdzają sprawności hydrantu, wydajności ani przejezdności dojazdu.

## Co zawiera projekt

| Element | Odpowiedzialność |
| --- | --- |
| `mcp-servers/mcp-geoportal` | Geokodowanie, działki ULDK, zapytania i mapy uzbrojenia KIUT |
| `mcp-servers/mcp-osm-fire-recon` | Hydranty, punkty czerpania wody i drogi z OSM/Overpass |
| `mcp-servers/mcp-weather-safety` | IMGW, Open-Meteo i orientacyjny kierunek znoszenia dymu |
| `skills/` | Pięć skilli: rozpoznanie, zasilanie wodne, media, PV/BESS, meldunek KDR; każdy zawiera `SKILL.md` i kod Python |
| `tools/skill_report.py` | Przekazanie wyników skilli bezpośrednio do kontraktu raportu HTML |
| `tools/visualizer.py` | Karta HTML: schemat SVG, woda, media, pogoda, meldunek, druk |
| `examples/` | Fikcyjne scenariusze JSON/Markdown i wygenerowane karty HTML |
| `test_recon_pipeline.py` | Osobny skrypt integracyjny odpytujący rzeczywiste zewnętrzne usługi |

[AGENTS.md](AGENTS.md) opisuje pracę agenta i szablon karty, [specyfikacja](AGENT_OSP_SPECYFIKACJA.md) zawiera pierwotną koncepcję i plan rozwoju. Plan nie stanowi potwierdzenia dostępności wszystkich danych z tych źródeł.

## Wspólne demo: skille → Markdown / JSON / HTML

Python 3.10+, bez dodatkowych zależności:

```bash
python3 skills/demo_runner.py --output-dir reports
```

Otwórz `reports/karta_skills.html`. W tym samym katalogu powstają `karta_skills.md` i `karta_skills.json`. Wszystkie trzy korzystają z tych samych wyników skilli. Demo nie odpytuje MCP i ma oznaczenie **DEMO — DANE FIKCYJNE**.

## Raport z własnych danych

Raport zawiera **kubaturę budynku i szacunkowe zapotrzebowanie wody**.
Kubatura jest liczona z podanej powierzchni zabudowy i wysokości albo przyjmowana
ze wskazanego źródła. Wydatek dla pomieszczeń mieszkalnych wynosi
`powierzchnia gaszenia × 0,08–0,10 l/(m²·s)` według materiałów ZPE i KG PSP/CNBOP.
Do wyznaczenia powierzchni gaszenia z kubatury wewnętrznej potrzebne są jawne
założenia; sam adres nie zapewnia wymiarów. Braki danych są widoczne w raporcie.
[Kontrakt wejścia, źródła i ograniczenia](docs/building_water.md).

Automatyczne pobranie obrysu i wysokości po adresie, **bez kluczy API**:

```bash
python3 tools/building_recon.py --address "Łętkowice 25"
```

Komenda korzysta z GUGiK CityGML (LoD1/LoD2), EGiB WFS i OSM; wynik zapisuje
w `reports/building/` jako JSON, Markdown i HTML. Modele powiatowe są cache'owane.
Narzędzie MCP `get_building_details` i `full_site_recon` udostępniają te same dane.
[Darmowe źródła, wybór budynku i uzupełnianie istniejącej karty](docs/building_sources.md).

```bash
python3 tools/visualizer.py --input examples/sample_recon.json --output reports/karta_json.html
python3 tools/visualizer.py --text-input examples/sample_recon.md --output reports/karta_md.html
python3 tools/visualizer.py --demo --output reports/karta_demo.html
```

JSON z `examples/sample_recon.json` pokazuje kontrakt wizualizatora. Parser Markdown obsługuje podstawowy szablon z `AGENTS.md`; do pełnego przekazywania wyników skilli używaj adaptera `build_visualizer_data` i JSON. Nieuzupełnione pola nie są pobierane z demo. Schemat rysuje punkty wodne tylko ze znanym azymutem i odległością do 500 m. Stożek dymu jest orientacyjną ilustracją kierunku, a nie modelem dyspersji.

HTML używa zewnętrznego skryptu Tailwind do stylowania; pełny wygląd wymaga dostępu do tego zasobu. Dane karty oraz SVG są zapisane w pliku. Opisy taktyczne w zaimportowanych skillach wymagają weryfikacji merytorycznej przed zastosowaniem operacyjnym.

## Serwery MCP i rozpoznanie online

```bash
uv run --directory mcp-servers/mcp-geoportal python -m src.server
uv run --directory mcp-servers/mcp-osm-fire-recon python -m src.server
uv run --directory mcp-servers/mcp-weather-safety python -m src.server
```

Konfigurację klienta zawiera `mcp_config.json`. Ścieżki względne wymagają uruchomienia klienta z katalogu projektu; w kliencie desktopowym można zastąpić je ścieżkami bezwzględnymi. Szczegóły narzędzi i zależności znajdują się w README poszczególnych serwerów.

Aktualny skrypt `test_recon_pipeline.py` wypisuje dane online do konsoli. Nie jest jeszcze połączony automatycznie z pełnym raportem skilli. Dane demonstracyjne i wyniki usług online pozostają rozróżnione.

## Testy

Testy skilli i integracji raportu, bez sieci i zależności:

```bash
python3 -m unittest discover -s tests -v
```

Testy poszczególnych serwerów uruchamiaj osobno (każdy ma własny pakiet `src`):

```bash
uv run --directory mcp-servers/mcp-geoportal --with pytest python -m pytest tests
uv run --directory mcp-servers/mcp-osm-fire-recon --with pytest python -m pytest tests
uv run --directory mcp-servers/mcp-weather-safety --with pytest python -m pytest tests
```

Oryginalne paczki w `do polaczenia/` pozostają lokalnie i są pomijane przez Git. Połączony kod znajduje się w katalogu głównym projektu.
