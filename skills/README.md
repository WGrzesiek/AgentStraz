# 🚒 Pakiet Skilli Taktycznych KDR dla Ochotniczej Straży Pożarnej (OSP)

Katalog zawiera zestaw modularnych skilli operacyjnych dla autonomicznego agenta pożarniczego **AgentStraz**. Każdy skill odpowiada za konkretną domenę taktyczną i opiera się na **Zasadach Działań Ratowniczych Państwowej Straży Pożarnej (PSP)** oraz normach pożarniczych.

---

## 🗂️ Spis Skilli w Pakiecie

| Katalog Skilla | Nazwa | Przeznaczenie operacyjne | Standard PSP / Norma |
| :--- | :--- | :--- | :--- |
| [`water_supply_calc`](./water_supply_calc/) | **Kalkulator Zasilania Wodnego** | Wyliczenie liczby odcinków węży W-75 (20m), naddatku terenowego, armatury (stojaki, klucze 7B/7E) i strat ciśnienia na magistrali. | Standard W-75, 20m/odcinek, armatura DIN/PN. |
| [`tactical_recon`](./tactical_recon/) | **Rozpoznanie Taktyczne i Wektor Wiatru** | Obliczenie stożka zadymienia (downwind hazard cone), identyfikacja zagrożonych obiektów po zawietrznej, bezpieczne pozycje wozów bojowych (upwind). | Zasady pozycjonowania wozów bojowych PSP. |
| [`hazmat_utilities_safety`](./hazmat_utilities_safety/) | **Bezpieczeństwo Mediów i GESUT** | Wykrywanie gazociągów, stref wybuchowych, linii elektroenergetycznych nN/SN/WN, stacji trafo oraz procedury dot. butli propan-butan 11kg (BLEVE). | Wytyczne KG PSP ds. instalacji gazowych i elektroenergetycznych. |
| [`pv_bess_hazards`](./pv_bess_hazards/) | **Fotowoltaika i Magazyny Energii** | Wykrywanie zagrożeń napięciem stałym DC do 1000V, procedury PWP (>6.5kW), ucieczka termiczna w bateriach Li-ion, toksyczny fluorowodór (HF), bezpieczne odległości prądów wody. | Wytyczne KG PSP dot. gaszenia instalacji fotowoltaicznych i BESS. |
| [`kdr_radio_brief`](./kdr_radio_brief/) | **Meldunek Radiowy KDR i Karta Bojowa** | Synteza wszystkich danych w gotowy meldunek radiowy dla dyspozytora SKKP/SKKM (pod TTS) oraz sformatowaną Kartę Rozpoznania Bojowego dla KDR na tablet. | Zasady korespondencji radiowej w sieciach MSWiA / PSP. |

---

## 🚀 Jak uruchomić demonstrację skilli?

W katalogu projektu uruchom skrypt demonstracyjny:

```bash
python skills/demo_runner.py
```

Skrypt przeprowadzi symulację zdarzenia pożarowego przy ul. Sosnowej 14 w Nowej Wsi, uruchomi wszystkie skille i wygeneruje kompletną Kartę Rozpoznania Bojowego oraz gotowy tekst meldunku radiowego.

---

## 🧪 Architektura i Testy

Każdy skill posiada:
1. `SKILL.md` – pełna specyfikacja domenowa, taktyka PSP, reguły promptu agenta, format JSON wejścia i wyjścia.
2. `logic.py` – deterministyczna, przetestowana jednostkowo logika algorytmiczna w Pythonie (dataclass, typowanie, obsługa błędów brzegowych).
3. `__init__.py` – czysty interfejs eksportu funkcji.

Testy jednostkowe znajdują się w katalogu `tests/test_skills.py` i mogą być uruchomione przez:
```bash
pytest
# lub
python3 -m unittest discover -s tests -v
```

Demo zapisuje również `reports/karta_skills.md`, `reports/karta_skills.json` i `reports/karta_skills.html`. Katalog wyjściowy zmienisz opcją `--output-dir`. HTML powstaje bezpośrednio z wyników skilli przez adapter `tools/skill_report.py`.
