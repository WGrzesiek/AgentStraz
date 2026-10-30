---
name: water-supply-calc
description: Kalkulator taktyczny zaopatrzenia wodnego dla KDR i rot gaśniczych OSP/PSP. Oblicza zapotrzebowanie na odcinki wężowe W-75, wymagany osprzęt armatury wodnej (stojaki, klucze) oraz weryfikuje punkty czerpania wody (hydranty, cieki otwarte).
---

# 🚒 Skill: Kalkulator Zaopatrzenia Wodnego (water-supply-calc)

## 1. Przeznaczenie i Cel Operacyjny
Skill realizuje kluczowe obliczenia zasilania wodnego terenu akcji pożarowej zgodnie z zasadami i taktyką działań gaśniczych Państwowej Straży Pożarnej (PSP) oraz Ochotniczych Straży Pożarnych (OSP).

Na podstawie danych o odległości, typie hydrantu (nadziemny / podziemny), średnicy nominalnej (DN) lub naturalnych punktach czerpania wody generuje:
- Precyzyjne zapotrzebowanie na odcinki węży tłocznych W-75 (z uwzględnieniem naddatku terenowego).
- Wykaz niezbędnej armatury pożarniczej dla roty budującej linię zasilającą (klucze, stojaki hydrantowe).
- Szacunkową wydajność punktu i straty ciśnienia na linii głównej.
- Zalecenia taktyczne w przypadku czerpania ze zbiorników i cieków otwartych (motopompy M16/8, linie ssawne W-110).

---

## 2. Standardy i Normy Taktyczne PSP

| Parametr | Wartość standardowa | Uzasadnienie taktyczne |
| :--- | :--- | :--- |
| Długość 1 odcinka W-75 | **20 metrów** | Standardowy wąż tłoczny tłoczony na wozach GBA/GCBA. |
| Współczynnik naddatku terenowego | **15% (1.15)** | Omijanie przeszkód, krawężników, zakrętów i ukształtowania terenu. |
| Hydrant naziemny (pillar) | Klucz 7E / klucz do zasuw | Bezpośrednie wpięcie linii tłocznej W-75. |
| Hydrant podziemny (underground) | **Stojak hydrantowy DN80/2x75** + **klucz 7B/7C** | Bezwzględny wymóg zabrania stojaka i klucza podziemnego! |
| Nominalny wydatek DN80 | ~10 dm³/s (600–800 l/min) | Wystarcza na zasilenie 1–2 prądów gaśniczych (np. prądownice Turbo). |
| Nominalny wydatek DN100 | ~15–20 dm³/s (900–1200 l/min) | Stabilne zasilenie linii głównej dla GCBA. |
| Punkt czerpania wody otwartej | Motopompa M16/8 + W-110 | 2–3 odcinki ssawne W-110 (2.5m), smok ssawny, pływak, linka. |

---

## 3. Schemat Obliczeń (Algorytm)

1. **Liczba odcinków wężowych W-75:**
   $$\text{Długość trasy z naddatkiem} = \text{dystans\_m} \times (1 + \text{naddatek})$$
   $$\text{Liczba odcinków} = \lceil \frac{\text{długość z naddatkiem}}{20} \rceil$$

2. **Straty ciśnienia na linii tłocznej:**
   Dla nominalnego przepływu 800 l/min orientacyjna strata liniowa wynosi ok. 0.12 bar na każde 100 m węża W-75.

3. **Ocena wystarczalności zasilania:**
   - Dystans $\le 100$ m: *Zasilanie bezpośrednie z hydrantu (krótka linia).*
   - Dystans $100 - 300$ m: *Linia zasilająca magistralna W-75.*
   - Dystans $> 300$ m: *Rozważyć przetłaczanie pompą pośrednią lub dowożenie wody zastępami GCBA.*

---

## 4. Format Wejścia i Wyjścia

### Wejście JSON:
```json
{
  "distance_m": 95,
  "hydrant_type": "underground",
  "diameter_dn": 80,
  "target_flow_lpm": 800
}
```

### Wyjście JSON:
```json
{
  "sections_w75": 6,
  "effective_length_m": 120,
  "required_gear": [
    "Węże tłoczne W-75: min. 6 szt.",
    "Stojak hydrantowy DN80/2x75",
    "Klucz do hydrantów podziemnych (7B/7C)",
    "Klucze do łączników 75/52 (kpl.)"
  ],
  "estimated_pressure_loss_bar": 0.14,
  "tactical_recommendation": "Hydrant podziemny 95m. Rota wodna zabiera stojak hydrantowy i klucz 7B."
}
```
