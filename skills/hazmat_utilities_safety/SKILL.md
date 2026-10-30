---
name: hazmat-utilities-safety
description: Skill analizy bezpieczeństwa infrastruktury technicznej (GESUT) i substancji niebezpiecznych dla KDR. Identyfikuje gazociągi (ciśnienia, zasuwy, przyłącza), elektroenergetykę (linie napowietrzne, stacje trafo) oraz butle propan-butan (LPG), wyznaczając strefy izolacji i procedury współdziałania z pogotowiami branżowymi.
---

# ⚠️ Skill: Bezpieczeństwo Mediów i Zagrożeń (hazmat-utilities-safety)

## 1. Przeznaczenie Operacyjne
Infrastruktura techniczna stanowi najczęstsze bezpośrednie zagrożenie życia dla ratowników podczas pożarów budynków.
Skill przetwarza dane z Krajowej Ewidencji Sieci Uzbrojenia Terenu (GESUT) oraz zgłoszenia KDR, wyznaczając strefy zagrożenia wybuchem i porażeniem prądem.

---

## 2. Zasady Bezpieczeństwa PSP

### A. Gazociągi (Paliwa Gazowe)
* **Gazociąg średniego / wysokiego ciśnienia:**
  * W przypadku podejrzenia rozszczelnienia: strefa izolacji min. **50 metrów**.
  * Zlokalizowanie kurka głównego gazu (standardowo szafka gazowa w linii ogrodzenia posesji).
  * Natychmiastowe wezwanie Pogotowia Gazowego (tel. 992) za pośrednictwem Stanowiska Kierowania (SK).

### B. Elektroenergetyka
* **Linie napowietrzne nN (0.4 kV):**
  * Ryzyko przepalenia i zerwania przewodów w wyniku płomieni i promieniowania cieplnego.
  * Wyznaczenie strefy zagrożenia pod przewodami (napięcie krokowe).
* **Linie Średniego Napięcia (SN 15 kV) i Wysokiego Napięcia (WN 110 kV):**
  * Bezwzględny zakaz zbliżania się sprzętem (drabiny mechaniczne SD, podnośniki SH) na odległość mniejszą niż **5 metrów**.
  * Całkowity zakaz podawania zwartego strumienia wody na urządzenia SN/WN.
* **Transformatory słupowe i stacje kontenerowe:**
  * Zagrożenie wybuchem oleju transformatorowego.

### C. Butle z Gazem Płynnym (LPG 11 kg)
* W polskich realiach wiejskich i podmiejskich (teren działania OSP) butle 11 kg są powszechne w kuchniach i kotłowniach.
* Ryzyko wybuchu fizycznego typu BLEVE.
* Wymóg: chłodzenie butli rozproszonym prądem wody zza osłony stałej oraz kontrola pirometrem (temperatura poniżej 50°C przed przemieszczeniem).

---

## 3. Format Wyjściowy

Skill generuje:
- Podsumowanie instalacji gazowych i elektroenergetycznych w rejonie zdarzenia.
- Wykaz działań natychmiastowych dla pierwszej roty (odcięcie kurka, bezpiecznik główny).
- Zadysponowane pogotowia ratunkowe/techniczne (Gazowe, Energetyczne).
