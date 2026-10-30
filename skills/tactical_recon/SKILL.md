---
name: tactical-recon
description: Skill analizy taktycznej rozpoznania wstępnego KDR (Kierującego Działaniem Ratowniczym). Oblicza wektor wiatru, sektor zadymienia i zagrożenia pożarowego (downwind cone), identyfikuje zagrożone obiekty sąsiednie oraz wyznacza bezpieczne pozycje wozów bojowych i kierunki natarcia/obrony.
---

# 💨 Skill: Rozpoznanie Taktyczne i Wektor Zagrożeń (tactical-recon)

## 1. Przeznaczenie Operacyjne
Skill wspiera KDR w podjęciu kluczowych decyzji w pierwszych minutach po przybyciu na miejsce zdarzenia (lub jeszcze w trakcie dojazdu). Na podstawie danych o wietrze (IMGW) i otaczającej zabudowie (BDOT10k/OSM) wyznacza strefy zagrożenia i zasady bezpieczeństwa pożarniczego.

---

## 2. Standardy i Zasady Taktyki Pożarniczej PSP

1. **Ustawienie wozów pożarniczych (GBA/GCBA/SD):**
   - Samochody bojowe i ratownicy zajmują pozycje **od strony nawietrznej (upwind)** lub z flanki.
   - Bezwzględny zakaz wjazdu w gęsty dym i strefę zawietrzną (ryzyko odcięcia drogi odwrotu, zgaśnięcia silnika z braku tlenu, zatrucia roty).

2. **Wyznaczenie Stożka Zawietrznego (Downwind Hazard Cone):**
   - Jeśli wiatr wieje z kierunku $\alpha$ (np. $315^\circ$ NW), to dym, iskry i gazy pożarowe przemieszczają się w kierunku $\alpha + 180^\circ$ (np. $135^\circ$ SE).
   - Szerokość stożka wynosi standardowo $\pm 30^\circ$ (lub $\pm 45^\circ$ przy porywach powyżej $35\text{ km/h}$).

3. **Wpływ Prędkości Wiatru:**
   - **$< 15\text{ km/h}$**: Stabilny słup konwekcyjny, dym unosi się w górę.
   - **$15 - 30\text{ km/h}$**: Wyraźny rozwój poziomy, zadymienie na poziomie gruntu do $100-200\text{ m}$.
   - **$> 30\text{ km/h}$**: Zagrożenie przerzutem żagwi (lotnych zarzewi ognia) na sąsiednie dachy i poszycie. Konieczność podania prądów wody w obronie.

4. **Wilgotność Powietrza:**
   - Wilgotność względna poniżej $30\%$ oznacza skrajnie wysoką łatwopalność materiałów palnych (trawy, dachy z gontu, ściółka).

---

## 3. Format Wyjściowy

Skill generuje:
- Kierunek wektora wiatru i zadymienia w języku polskim (np. `NW (315°) -> sektor SE`).
- Listę zagrożonych posesji w osi wiatru.
- Instrukcję ustawienia wozów bojowych dla KDR.
- Priorytety taktyczne: Natarcie vs Obrona.
