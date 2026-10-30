# Darmowe źródła wymiarów budynków — bez kluczy API

## Użycie po adresie lub GPS

Python 3.10+, bez dodatkowych zależności dla komendy rozpoznania budynku:

```bash
python3 tools/building_recon.py --address "Łętkowice 25"
python3 tools/building_recon.py --lat 50.255076 --lon 20.173021
```

Powstają `reports/building/budynek.json`, `budynek.md` i `budynek.html`.
HTML zawiera szkic 2D rzeczywistych obrysów budynków: analizowany obiekt
wyróżniony na czerwono, sąsiednia zabudowa, punkt adresowy, północ siatkowa
EPSG:2180 i skala metryczna. Tabela pod szkicem podaje wysokości, powierzchnie,
identyfikatory oraz źródła. Obrysy są przekazywane w `building.site_plan`
bez parsowania tekstu i bez dublowania tego samego budynku z różnych rejestrów.
W szkicu nie odtwarzamy pomieszczeń, dojazdów ani nieznanej infrastruktury.

Raport tekstowy i HTML wskazują również TERYT powiatu oraz stan paczki:
automatycznie pobrana i zaindeksowana, użyta z cache lub zaindeksowana
z wcześniej pobranego ZIP. Datę danych źródłowych pokazujemy osobno od daty
utworzenia lokalnego indeksu. Starsze raporty JSON bez `site_plan` pokazują
komunikat o braku geometrii; ponowne rozpoznanie uzupełnia szkic.

To raport rozpoznania budynku; inne pola karty pozostają nieuzupełnione.
Aby uzupełnić istniejącą pełną kartę, podaj JSON z tymi samymi współrzędnymi:

```bash
python3 tools/building_recon.py --input reports/karta.json --output-dir reports/uzupelniona
```

Pozostałe sekcje JSON i raportu HTML są zachowywane. Plik Markdown tej komendy
zawiera sekcję budynku; pełną kartę Markdown generuje `generate_kdr_reports`,
któremu należy przekazać `building=wynik_rozpoznania['building']`.
Nie uzupełniaj karty rzeczywistego adresu danymi z fikcyjnego demo.

Opcjonalne `--fire-area-m2` i `--duration-min` oznaczają dane rozpoznane lub
jawne założenia użytkownika. Obrys budynku nie jest automatycznie powierzchnią
gaszenia, więc sam adres nie uruchamia kalkulacji wydatku wody.

## Źródła i kolejność wyboru

| Źródło | Pobierane dane | Ograniczenia |
| --- | --- | --- |
| GUGiK UUG / PRG | Punkt adresowy | Niejednoznaczny wynik UUG nie jest wybierany automatycznie |
| OSM Nominatim | Zapasowe geokodowanie | Cache godzinny, limit 1 żądanie/s na proces; bez masowego pobierania |
| GUGiK modele CityGML | Obrys podstawy, wysokość, identyfikator BDOT, data źródła | Preferowany najnowszy dostępny LoD1, starsze roczniki i LoD2 zapasowo |
| GUGiK EGiB WFS | Obrysy, rodzaj budynku, kondygnacje | Brak wysokości oznacza brak automatycznej kubatury |
| OSM Overpass | Obrysy ways/multipolygons, jawny tag `height`, data wersji | Dane społecznościowe; tag wysokości w metrach, bez zgadywania z `building:levels` |

Wywołania EGiB, indeksu modeli GUGiK i OSM są niezależne. Awaria jednego
źródła nie blokuje pozostałych. Raport pokazuje stan każdego źródła
(`ok`, `no_data`, `unavailable`), datę odczytu oraz czas danych, jeżeli źródło
go udostępnia. Czas wersji OSM lub rocznik modelu nie jest czasem pomiaru w terenie.
Nie mieszamy wysokości jednego obiektu z obrysem innego rejestru.

Automatyczny wybór wymaga jednego obrysu zawierającego punkt adresowy.
Priorytet: model GUGiK, EGiB, OSM. Nakładające się obrysy w źródle o wyższym
priorytecie blokują automatyczny wybór. Jeśli punkt leży przy drodze lub
bramie, wynik `selection_required` zawiera kandydatów do 80 m od punktu.
Nie wybieramy wtedy najbliższej stodoły jako domu.

Po potwierdzeniu obiektu można użyć jego id z JSON, np.:

```bash
python3 tools/building_recon.py --address "pełny adres" --building-id "id-z-listy-kandydatow"
```

## MCP i integracja raportu

Serwer `mcp-geoportal` ma narzędzie:

```text
get_building_details(lat, lon, building_id=None)
```

`full_site_recon(address_or_coords)` również zwraca `building` i pełny
`building_recon`. Słownik `building` można przekazać do istniejącego
`generate_kdr_reports(..., building=building, suppression=...)`.
Adapter skilli przenosi go do raportu HTML bez parsowania Markdown.

## Cache i limity

Indeks WMS `GetFeatureInfo` dostarcza rzeczywiste linki do paczek powiatowych.
Paczki krajowe są pomijane. Pierwsze zapytanie wymaga pobrania ZIP i zbudowania
lokalnego indeksu SQLite, kolejne odczytują dane z cache ważnego 7 dni.
Domyślny katalog: `reports/cache/buildings`; można ustawić
`BUILDING_CACHE_DIR` lub CLI `--cache-dir`.

Limity: 128 MiB pobranego ZIP, 512 MiB sumy plików GML po rozpakowaniu,
32 MiB na jeden GML. Przekroczenia pojawiają się w ostrzeżeniach i uruchamiają
próbę innego rocznika/źródła. Nie wypakowujemy ścieżek z archiwum na dysk.
Parsery GUGiK obsługują publikowane CityGML w EPSG:2180, EGiB pobierane jest
w EPSG:2180; inne CRS są odrzucane, zamiast interpretowane jako metry.
Rozpoznanie rozróżnia kolejność osi UUG, EGiB WFS i CityGML.

Publiczny Nominatim ma [zasady użycia](https://operations.osmfoundation.org/policies/nominatim/):
maksymalnie 1 żądanie/s na aplikację, cache, identyfikujący User-Agent,
atrybucja, bez autocomplete i masowego geokodowania. Cache geokodera jest także
zapisywany na dysku. Adres usługi można zmienić przez `NOMINATIM_SEARCH_URL`.

Publiczne usługi mogą odpowiadać wolno lub być niedostępne. Przy wielu
równoległych instancjach aplikacji limit geokodera powinien być wspólny dla
całego wdrożenia. Integracja jest przeznaczona do pojedynczych rozpoznań.

## Ograniczenia geometryczne

Kubatura to przybliżenie `powierzchnia obrysu × wysokość modelu`, również
przy danych LoD2. Program nie wyznacza dokładnej objętości zamkniętej siatki
dachu. Otwory w obrysach są odliczane. Nie wyznacza kubatury wewnętrznej,
powierzchni użytkowej, liczby mieszkańców ani rozpoznanej powierzchni pożaru.
Każdy wynik wymaga potwierdzenia zgodności obiektu i aktualności danych.

## Dokumentacja źródeł — sprawdzona 30.10.2026

- [GUGiK: modele 3D budynków](https://www.geoportal.gov.pl/pl/dane/inne-dane/modele-3d-budynkow/)
- [GUGiK: zintegrowany WFS EGiB](https://mapy.geoportal.gov.pl/wss/service/PZGIK/EGIB/WFS/UslugaZbiorcza)
- [GUGiK: indeks pobierania modeli](https://mapy.geoportal.gov.pl/wss/service/PZGIK/FOTO/WMS/ModeleBudynkow3D)
- [OSM: znaczenie height](https://wiki.openstreetmap.org/wiki/Key:height)
- [OSM: Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL)
- [OSMF: zasady Nominatim](https://operations.osmfoundation.org/policies/nominatim/)

Google Solar API nie jest używane: wymaga uwierzytelnienia. Ręczne pomiary
w Google Earth Pro pozostają możliwe poza automatycznym przepływem.

Gdy indeks usług GUGiK jest niedostępny, program korzysta ze świeżych lokalnych
indeksów zawierających obrysy w szukanej okolicy. Raport ostrzega, że nie
potwierdzono dostępności nowszej paczki. Nie zastępuje to bieżącego rozpoznania.
