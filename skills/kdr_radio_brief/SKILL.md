---
name: kdr-radio-brief
description: Generator zwięzłego meldunku radiowego KDR (zgodnego ze standardem korespondencji radiowej PSP/OSP) oraz pełnej Karty Rozpoznania Bojowego. Integruje wyniki rozpoznania taktycznego, zasilania wodnego, instalacji PV/BESS i mediów w gotowy komunikat do odczytania przez radio lub syntezator mowy (TTS).
---

# 📻 Skill: Generator Meldunku Radiowego KDR (kdr-radio-brief)

## 1. Przeznaczenie Operacyjne
Pierwszy zastęp OSP przybyły na miejsce zdarzenia ma obowiązek w ciągu 1–2 minut nadać do Stanowiska Kierowania (SKKP / SKKM) **meldunek o sytuacji zastanej**. KDR działa pod presją czasu i emocji.

Skill syntetyzuje dane ze wszystkich modułów i generuje:
1. **Gotowy meldunek radiowy (Radio Brief)** – do natychmiastowego odczytania przez radio lub odsłuchania przez syntezator mowy (TTS) w kabinie wozu bojowego.
2. **Kartę Rozpoznania Bojowego (Combat Recon Sheet)** – sformatowaną wizualnie dla KDR na tablet/smartfon.

---

## 2. Standard Meldunku Radiowego PSP (Zasady Korespondencji)

Struktura meldunku wstępnego KDR do SK:
1. **Identyfikacja i lokalizacja:** Kto mówi, dokładny adres i obiekt.
2. **Sytuacja pożarowa:** Co i w jakim stopniu się pali, zagrożenie dla ludzi.
3. **Wektor zadymienia i wiatr:** W jakim kierunku rozprzestrzenia się strefa zagrożenia.
4. **Zasilanie wodne:** Skąd i jak realizowane jest zaopatrzenie w wodę (hydrant, liczba odcinków W-75, armatura).
5. **Media i zagrożenia:** Gaz, linie energetyczne, PV/BESS, butle LPG.
6. **Zapotrzebowanie na Siły i Środki (SiŚ):** Wezwanie pogotowi branżowych (gazowe, energetyczne), dodatkowych GCBA.
