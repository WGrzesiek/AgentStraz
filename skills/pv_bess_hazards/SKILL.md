---
name: pv-bess-hazards
description: Skill analizy zagrożeń ze strony fotowoltaiki (PV), magazynów energii (BESS / Li-ion) oraz pojazdów elektrycznych (EV). Wyznacza procedury bezpieczeństwa elektrycznego i toksykologicznego wg standardów KG PSP (napięcie stałe DC do 1000V, wyłącznik PWP, fluorowodór HF, bezpieczne odległości prądów gaśniczych).
---

# ⚡ Skill: Zagrożenia Fotowoltaiką, Magazynami Energii i EV (pv-bess-hazards)

## 1. Przeznaczenie Operacyjne
Nowoczesne budynki mieszkalne i komercyjne powszechnie posiadają mikroinstalacje fotowoltaiczne, przydomowe magazyny energii oraz stacje ładowania samochodów elektrycznych. W warunkach pożaru stanowią one **śmiertelne zagrożenie porażeniem prądem stałym (DC)** oraz **skażeniem toksycznym**.

Skill analizuje parametry instalacji i generuje natychmiastowe wytyczne dla KDR i rot gaśniczych.

---

## 2. Standardy i Zasady Taktyki KG PSP

### A. Napięcie Stałe (DC) paneli fotowoltaicznych
- **Napięcie do 1000V DC:** Po wyłączeniu zasilania AC w budynku przewody DC od paneli do inwertera **pozostają pod pełnym napięciem w dzień**!
- **Gaszenie wodą urządzeń pod napięciem (do 1 kV):**
  - **Prąd zwarty wody:** Bezwzględny zakaz z odległości mniejszej niż **5 metrów**.
  - **Prąd rozproszony (kroplisty/mgłowy):** Dopuszczalny z odległości min. **1 metra** (przy ciśnieniu min. 4 bar).
  - Wewnątrz pomieszczeń inwertera: priorytet dla gaśnic proszkowych (ABC) lub śniegowych (CO₂).

### B. Przeciwpożarowy Wyłącznik Prądu (PWP)
- W Polsce dla instalacji PV o mocy **powyżej 6.5 kWp** wymagany jest wyłącznik PWP oraz uzgodnienie ppoż.
- KDR otrzymuje przypomnienie o natychmiastowym sprawdzeniu lokalizacji wyłącznika PWP (zwykle obok złącza ZK lub wejścia głównego).

### C. Magazyny Energii (BESS) i Pojazdy EV (Li-ion)
- **Zjawisko Thermal Runaway (Ucieczka termiczna):** Egzotermiczna reakcja łańcuchowa w ogniwach litowo-jonowych.
- **Emisja skrajnie toksycznych gazów:** Fluorowodór (HF), cyjanowodór (HCN), tlenek węgla (CO).
- **Zasady ochrony ratowników:**
  - Bezwzględny nakaz pracy rot w **Aparatach Ochrony Dróg Oddechowych (AODO)**.
  - Zakaz otwierania obudowy baterii.
  - Długotrwałe chłodzenie płaszczowe dużą ilością wody (zabezpieczenie przed re-ignicją przez min. 24h).

---

## 3. Format Wyjściowy

Skill generuje:
- Stopień zagrożenia elektrycznego i toksycznego.
- Ostrzeżenie o napięciu DC i wyłączniku PWP.
- Bezpieczne odległości podawania prądów wody.
- Wytyczne dot. aparatów AODO i chłodzenia magazynów BESS.
