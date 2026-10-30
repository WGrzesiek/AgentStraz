# Kubatura i zapotrzebowanie wody

Projekt wcześniej nie obliczał kubatury. `skills/water_supply_calc/building.py`
udostępnia teraz `calculate_building_water(building, suppression)`.
`generate_kdr_reports` przyjmuje te same dwa opcjonalne słowniki; adapter
przenosi wejścia i wynik do JSON, a wizualizator liczy także bezpośrednio z JSON.
Sekcja jest widoczna w karcie Markdown, HTML i na wydruku.

## Źródła oficjalne — sprawdzone 30.10.2026

- [ZPE: Obliczanie sił i środków podczas zwalczania pożarów](https://zpe.gov.pl/a/obliczanie-sil-i-srodkow-podczas-zwalczania-pozarow/D15L55ToZ):
  wzór Q = A_g × I oraz tabela intensywności dla budynków mieszkalnych
  0,08–0,10 l/(m²·s), czyli 4,8–6 l/(m²·min).
- [KG PSP / CNBOP: Szkolenie dowódców OSP, marzec 2009, tabela 3.1](https://www.gov.pl/attachment/2b06ddfe-71f4-4fac-a55b-e6b18cde7808):
  potwierdza przedział dla budynków administracyjnych i mieszkalnych.
- [Rozporządzenie MSWiA z 24.07.2009, Dz.U. poz. 1030](https://eli.gov.pl/eli/DU/2009/1030/ogl):
  wymagania zaopatrzenia do zewnętrznego gaszenia stanowią odrębne zagadnienie.
  Program nie wyznacza zgodności budynku z tymi wymaganiami.

To materiały szkoleniowe, nie uniwersalna norma zużycia wody przy każdym pożarze.
Wartość **4 l/(m²·s)** nie jest współczynnikiem użytym w kalkulatorze.
Wynik jest przedziałem do oceny KDR, bez obrony sąsiednich obiektów, strat
i rezerw. Tabela zawiera odrębne pozycje m.in. dla piwnic i strychów;
obecny kalkulator obsługuje wyłącznie scenariusz pomieszczeń mieszkalnych.

## Wejście do raportu

Dodaj do głównego obiektu JSON:

```json
{
  "building": {
    "footprint_area_m2": 120,
    "height_m": 6,
    "source": "DEMO — wymiary fikcyjne"
  },
  "suppression": {
    "fire_area_m2": 100,
    "duration_min": 20
  }
}
```

Wynik: szacowana kubatura bryły 720 m³, wydatek 8–10 l/s
(480–600 l/min), zapas na zadane 20 minut 9600–12000 litrów.
Czas jest założeniem użytkownika, nie czasem wymaganym przepisami.

### Geometria

- `volume_m3`: kubatura podana ze źródła; ma pierwszeństwo przed wymiarami.
- Albo `footprint_area_m2 × height_m`: model prostopadłościanu.
  Powierzchnia zabudowy to rzut, a wysokość dotyczy całego modelu bryły,
  nie wysokości pojedynczej kondygnacji. Dach, uskoki, pustki i piwnice mogą
  istotnie zmienić wynik. To nie pomiar kubatury brutto według norm budowlanych.
- `source` i `observed_at`: źródło i opcjonalny czas danych, wyświetlane w raporcie.

Wymiary mogą teraz pochodzić z automatycznego rozpoznania po adresie:
`python3 tools/building_recon.py --address "Łętkowice 25"`.
Integracja wykorzystuje bezpłatne źródła GUGiK i OSM, bez kluczy API.
[Opis źródeł i wyboru budynku](building_sources.md).
Nie zgadujemy wysokości z liczby kondygnacji. Brak wymiarów daje komunikat
o brakujących danych zamiast przykładowej liczby.

### Woda z kubatury

Sama kubatura zewnętrznej bryły nie wyznacza powierzchni gaszenia. Preferowane
jest rozpoznane `suppression.fire_area_m2`. Gdy go brak, można jawnie podać:

```json
{
  "building": {
    "interior_volume_m3": 600,
    "mean_room_height_m": 3,
    "source": "DEMO — dane fikcyjne"
  },
  "suppression": {
    "affected_fraction": 0.5,
    "duration_min": 20
  }
}
```

Model A_g = V_wewnętrzna / h_pomieszczeń × udział objęty gaszeniem daje 100 m².
To **założenie geometryczne programu**, nie wzór z tabeli PSP/ZPE.
Nie przepisujemy automatycznie kubatury brutto do kubatury wewnętrznej.
Udział `(0, 1]` i średnia wysokość muszą być podane; brak danych blokuje
wyliczenie wydatku. Brak czasu blokuje tylko wyliczenie zapasu, nie wydatku.

## Uruchomienie

```bash
python3 skills/demo_runner.py --output-dir reports
python3 tools/visualizer.py --input reports/karta_skills.json --output reports/karta_woda.html
python3 -m unittest discover -s tests -v
```

Wszystkie dane demo są fikcyjne. Parser starszych kart Markdown nie przenosi
nowych obliczeń; do importu pełnej karty używaj JSON lub adaptera skilli.

## Czytelna kalkulacja i plan łączony w HTML

Sekcja wody przedstawia osobne karty powierzchni, wysokości, kubatury
i przepływu. Źródła oraz metadane pozostają w rozwijanej sekcji na dole.
Dla przyjętej powierzchni gaszenia tabela pokazuje zapas na przykładowe
10, 20 i 30 minut ciągłego podawania. Są to założenia, bez rezerwy.

Raport testowy Łętkowice 25 przyjmuje jawny scenariusz: powierzchnia
gaszenia równa jednemu rzutowi budynku (127,38 m²). Nie oznacza to
rozpoznania powierzchni pożaru ani sumy powierzchni kondygnacji.
Generator nie podstawia obrysu automatycznie w innych raportach.

Na końcu HTML plan łączony nakłada obrysy EPSG:2180, warunkowy sektor
dymu i punkty wodne z GPS. Strzałki pokazują odległości w linii prostej
do oznaczonych współrzędnych, nie trasy wężowe. Nie są rysowane obrysy
zbiorników bez geometrii. Poszerzenie widoku nie dodaje brakującej zabudowy.
Dane mapy i pogody zachowują czas pierwotnego rozpoznania.
