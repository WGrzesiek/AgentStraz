# 🚒 Inteligentny Asystent KDR dla Ochotniczej Straży Pożarnej (OSP)
### Koncepcja i Architektura Systemu Rozpoznania Terenu Akcji na Bazie Danych Przestrzennych i Agentów AI

---

## 1. Cel Projektu
Stworzenie autonomicznego agenta AI wspierającego **Kierującego Działaniem Ratowniczym (KDR)** oraz dyspozytorów OSP/PSP w pierwszych, krytycznych minutach po zadysponowaniu do zdarzenia.

Na podstawie adresu lub współrzędnych geograficznych zdarzenia agent automatycznie pobiera, przetwarza i syntetyzuje dane o infrastrukturze technicznej i terenie, dostarczając **zwięzłą Kartę Rozpoznania Bojowego**.

### Główne cele operacyjne:
- **Zasilanie wodne:** Natychmiastowa lokalizacja hydrantów (typ, średnica) oraz naturalnych punktów czerpania wody (cieki, stawy) wraz z wyliczeniem zapotrzebowania na odcinki wężowe W-75.
- **Bezpieczeństwo ratowników i mediów:** Wykrywanie przebiegu gazociągów (wysokie/średnie ciśnienie, przyłącza, zasuwy) oraz linii energetycznych i transformatorów.
- **Taktyka pożarowa i strefy zagrożenia:** Pobranie wektora wiatru w czasie rzeczywistym i wyznaczenie strefy rozprzestrzeniania się dymu / zagrożeń chemicznych.
- **Dostępność terenu:** Weryfikacja dróg pożarowych, mostków i dojazdów leśnych pod kątem tonażu wozów GCBA/GBA.

---

## 2. Architektura Rozwiązania

```
                          ┌─────────────────────────────────────┐
                          │    DYSPOZYCJA / KDR (Wejście)      │
                          │   np. "Sosnowa 14, Nowa Wieś"       │
                          └──────────────────┬──────────────────┘
                                             │
                                             ▼
                          ┌─────────────────────────────────────┐
                          │           AGENT GŁÓWNY AI           │
                          │   (Koordynator logiki i skilli)     │
                          └──────────────────┬──────────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
   ┌───────────────────────┐    ┌─────────────────────────┐    ┌───────────────────────┐
   │      MCP GUGiK /      │    │     MCP OSM FIRE        │    │      MCP METEO        │
   │      GEOPORTAL        │    │    (Overpass API)       │    │     (IMGW / Open)     │
   ├───────────────────────┤    ├─────────────────────────┤    ├───────────────────────┤
   │ • Geokodowanie PRG    │    │ • Hydranty (typ/DN)     │    │ • Prędkość wiatru     │
   │ • Działki (ULDK)      │    │ • Cieki / Stawy         │    │ • Kierunek wiatru (°) │
   │ • GESUT: Gaz i Prąd   │    │ • Drogi pożarowe        │    │ • Porywy / Ostrzeżenia│
   │ • BDOT10k: Budynki    │    │ • Miejsca zassania wody │    │ • Wilgotność / Temp.  │
   └───────────────────────┘    └─────────────────────────┘    └───────────────────────┘
               │                             │                             │
               └─────────────────────────────┼─────────────────────────────┘
                                             │ (Surowe dane przestrzenne)
                                             ▼
                          ┌─────────────────────────────────────┐
                          │            SKILLE AGENTA            │
                          │ • tactical-recon                    │
                          │ • water-supply-calc                 │
                          │ • hazmat-utilities-safety           │
                          └──────────────────┬──────────────────┘
                                             │
                                             ▼
                          ┌─────────────────────────────────────┐
                          │    KARTA ROZPOZNANIA BOJOWEGO       │
                          │  (Zwięzły meldunek: SMS/App/Radio)  │
                          └─────────────────────────────────────┘
```

---

## 3. Otwarte Źródła Danych Przestrzennych (Polska)

Polska posiada jedną z najlepiej rozwiniętych infrastruktur danych przestrzennych (SDI) w Europie, w większości dostępną **całkowicie bezpłatnie**:

| Zasób | Operator | Technologia / API | Dane dla strażaków |
| :--- | :--- | :--- | :--- |
| **PRG / EMUiA** | GUGiK | REST API (`services.gugik.gov.pl`) | Oficjalny rejestr adresów, precyzyjne punkty adresowe budynków. |
| **ULDK** | GUGiK | REST API (`uldk.gugik.gov.pl`) | Lokalizacja działki ewidencyjnej, obrys posesji. |
| **GESUT / KIEG** | GUGiK / Powiaty | WFS / WMS (`GetFeatureInfo`) | Sieci uzbrojenia terenu: **gazociągi (średnice, ciśnienia, przyłącza), linie energetyczne, stacje trafo, wodociągi**. |
| **BDOT10k** | GUGiK | WFS / Pakiety SHP/GML | Budynki, przeznaczenie obiektów, drogi leśne i pożarowe, pokrycie terenu. |
| **OpenStreetMap** | Społeczność OSM | Overpass API | Hydranty (`emergency=fire_hydrant`), średnice (`fire_hydrant:diameter`), cieki wodne (`waterway`), stawy (`natural=water`). |
| **Dane Synoptyczne** | IMGW-PIB | Otwarty REST API (`danepubliczne.imgw.pl`) | Rzeczywisty wiatr (kierunek, porywy), temperatura, wilgotność z najbliższej stacji. |
| **Hydroportal** | PGW Wody Polskie | WMS / WFS | Sieć hydrograficzna, dostępność cieków, wały przeciwpowodziowe. |

---

## 4. Specyfikacja Narzędzi MCP (Model Context Protocol)

### Serwer 1: `mcp-geoportal-gov-pl`
Integracja z oficjalnymi serwisami Głównego Urzędu Geodezji i Kartografii.

* **`geocode_address(address_string)`**
  * **Wejście:** `"Nowa Wieś, ul. Sosnowa 14"` lub `"Działka 123/4, obręb Lipowo"`
  * **Wyjście:** Współrzędne WGS84 (`lat`, `lon`), PUWG 1992 (`x`, `y`), identyfikator działki TERYT.
* **`get_underground_utilities(lat, lon, radius_m=150)`**
  * **Działanie:** Odpytanie Krajowej Ewidencji Sieci Uzbrojenia Terenu (GESUT) metodą WFS / GetFeatureInfo.
  * **Wyjście:**
    * Gaz: przebieg przewodów, rodzaj ciśnienia (niskie/średnie/wysokie), punkty wejścia do budynków, zasuwy.
    * Elektroenergetyka: linie napowietrzne, kable podziemne, transformatory słupowe i kontenerowe.
* **`get_building_details(lat, lon)`**
  * **Działanie:** Pobranie danych o budynku z BDOT10k / EGiB.
  * **Wyjście:** Liczba kondygnacji, powierzchnia zabudowy, funkcja (mieszkalny, przemysłowy, inwentarski).

---

### Serwer 2: `mcp-osm-fire-recon`
Szybka ekstrakcja danych taktycznych z OpenStreetMap via Overpass API.

* **`find_nearest_hydrants(lat, lon, radius_m=500, max_results=5)`**
  * **Zapytanie Overpass:** `node["emergency"="fire_hydrant"](around:radius, lat, lon);`
  * **Zwracane atrybuty:**
    * Odległość geometryczna i szacowana trasa dojścia.
    * Typ: nadziemny (`pillar`) vs podziemny (`underground`).
    * Średnica przyłącza: np. `DN80`, `DN100`.
* **`find_water_intakes(lat, lon, radius_m=1500)`**
  * **Zapytanie:** rzeki (`waterway=river|stream`), stawy (`natural=water`), punkty czerpania wody (`emergency=suction_point` / `water_point`).
  * **Zwracane atrybuty:** Odległość, klasa cieku, dostępność dla motopompy.
* **`check_access_roads(lat, lon)`**
  * **Zapytanie:** drogi dojazdowe, szerokość, nawierzchnia (`surface=asphalt|ground|gravel`), leśne dojazdy pożarowe (`fire_lane`).

---

### Serwer 3: `mcp-weather-safety`
Dane meteorologiczne do oceny rozwoju pożaru i strefy zadymienia.

* **`get_tactical_wind_and_weather(lat, lon)`**
  * **Działanie:** Pobranie stacji synoptycznej/telemetrycznej IMGW najbliższej miejsca akcji.
  * **Zwracane parametry:**
    * Kierunek wiatru w stopniach (0–360°) oraz słownie (np. NW - północno-zachodni).
    * Prędkość stała (km/h oraz m/s).
    * Prędkość w porywach.
    * Wilgotność względna powietrza (kluczowa dla pożarów traw i lasów).

---

## 5. Zestaw Skilli Agenta (Tactical Agent Skills)

Agent nie jest jedynie wyszukiwarką – posiada skille interpretujące dane pod kątem **Zasad Działań Ratowniczych PSP/OSP**:

### 1. `tactical-recon` (Rozpoznanie Wstępne KDR)
* **Zadanie:** Łączy dane adresowe, pogodowe i terenowe w jeden zwięzły meldunek.
* **Logika:**
  * Określa kierunek przemieszczania się dymu: jeśli wiatr wieje z kąta 315° (NW), sektor zagrożony to SE (południowy wschód).
  * Identyfikuje obiekty narażone na promieniowanie cieplne lub zadymienie w pasie wiatru.

### 2. `water-supply-calc` (Kalkulator Zasilania Wodnego)
* **Zadanie:** Przelicza odległość hydrantu na standardowe wyposażenie samochodu pożarniczego.
* **Logika:**
  * 1 odcinek węża tłocznego W-75 = 20 metrów.
  * Wyliczenie: `Liczba odcinków = ceil(odległość_po_drodze / 20) + rezerwa na zakręty (+10-20%)`.
  * Wskazanie sprzętu: jeśli hydrant jest podziemny, automatycznie dodaje adnotację: *"Wymaga zabrania stojaka hydrantowego i klucza podziemnego"*.

### 3. `hazmat-utilities-safety` (Bezpieczeństwo Mediów i Zagrożenia)
* **Zadanie:** Weryfikacja obecności instalacji stwarzających bezpośrednie zagrożenie wybuchem lub porażeniem.
* **Logika:**
  * Identyfikacja gazociągów w promieniu 50m od ogniska.
  * Ostrzeżenie o liniach wysokiego/średniego napięcia (ryzyko zerwania i zakaz podawania zwartych prądów gaśniczych).

---

## 6. Wzór Raportu Bojowego (Format Wynikowy)

Docelowy format prezentowany strażakom w terminalu, aplikacji mobilnej lub czytany syntezatorem głosu:

```markdown
🚨 KARTA ROZPOZNANIA MIEJSCA ZDARZENIA 🚨
Adres: Nowa Wieś, ul. Sosnowa 14
Koordynaty: 52.12345, 20.98765 | Działka nr: 142/2

💨 WARUNKI METEO (Stacja IMGW: 4.2 km):
• Wiatr: PÓŁNOCNO-ZACHODNI (NW, 315°), 18 km/h | Porywy: do 36 km/h
• Wektor zadymienia: Zagrożone sąsiednie posesje po stronie SE (ul. Sosnowa 16 i 18)

🚒 ZAOPATRZENIE WODNE:
1. Hydrant nadziemny DN80: 95 m (ul. Sosnowa 8)
   -> Wymaga: ~5 odcinków W-75
2. Hydrant podziemny DN100: 210 m (skrzyżowanie Sosnowa / Leśna)
   -> Wymaga: stojak hydrantowy, klucz podziemny, ~11 odcinków W-75
3. Otwarty ciek wodny: rzeczka Czarna (420 m na wschód)
   -> Możliwość zassania: motopompa M16/8, dojazd utwardzony od ul. Młyńskiej

⚠️ ZAGROŻENIA I MEDIA (GESUT):
• GAZ: Gazociąg średniego ciśnienia DN63 w ulicy. Przyłącze gazowe od zachodu.
  Skrzynka / zawór: zlokalizowany w linii ogrodzenia.
• ENERGETYKA: Linia napowietrzna nN wzdłuż drogi. 
  Trafo słupowe: 130 m na północ.
• DOSTĘPNOŚĆ: Droga gminna asfaltowa, szerokość 4.5 m. Wjazd dla GCBA bez utrudnień.
```

---

## 7. Plan Wdrożenia (Roadmap)

### Faza 1: MVP Silnika Danych (1–2 tygodnie)
- [ ] Implementacja serwera `mcp-osm-fire-recon` (Overpass API – hydranty i cieki wodne).
- [ ] Implementacja serwera `mcp-weather-safety` (dane wiatrowe z IMGW).
- [ ] Geokodowanie adresowe przez otwarte API GUGiK (PRG).
- [ ] Przygotowanie pierwszego skilla `tactical-recon`.

### Faza 2: Integracja Sieci Uzbrojenia Terenu (GESUT / KIEG) (2–3 tygodnie)
- [ ] Implementacja klienta WFS/WMS dla warstw uzbrojenia terenu GUGiK (gaz, prąd).
- [ ] Filtrowanie infrastruktury gazowej i elektroenergetycznej w promieniu zdarzenia.
- [ ] Skill `water-supply-calc` (kalkulacja linii gaśniczych).

### Faza 3: Interfejs i Integracje Bojowe (3–4 tygodnie)
- [ ] Wybór interfejsu docelowego:
  - Bot Telegram / Signal / Discord (błyskawiczny dostęp na smartfonach strażaków).
  - Web-panel na tablecie w kabinie wozu bojowego z interaktywną mapą (Leaflet/MapLibre).
- [ ] Integracja z systemami powiadamiania (np. nasłuch SMS z SWD PSP / e-Remiza / Terminal OSP).

---

## 8. Pytania i Decyzje Projektowe

Przed rozpoczęciem prac warto uzgodnić:
1. **Język serwerów MCP:** Rekomendowany **Python** (ze względu na biblioteki geodezyjne i GIS: `shapely`, `geopy`, `pyproj`, `owslib` dla WFS/WMS) lub **TypeScript** (`@modelcontextprotocol/sdk`).
2. **Zakres terytorialny na start:** Czy testujemy na wybranej gminie / powiecie (np. baza lokalnej jednostki OSP), czy od razu weryfikujemy w skali ogólnokrajowej?
3. **Kanał dostarczania raportu:** Jaki interfejs jest preferowany przez załogę (np. czat Telegram, dedykowana strona www, aplikacja PWA)?
