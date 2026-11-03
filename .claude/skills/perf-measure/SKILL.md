---
name: perf-measure
description: Procedure for measuring TwinPeaks2D performance (frame time, per-function time, CPU profile) before and after a change. Use when the user wants numbers to compare an optimization, asks for FPS/frame time, profiling, perf or callgrind.
---

# Pomiar wydajności

Zasada: **bez pomiaru przed zmianą nie ma optymalizacji.** Zawsze mierz wersję bazową,
zapisz wynik, dopiero potem zmiana i drugi pomiar w identycznych warunkach.

## Ważne fakty o tym projekcie
- Pętla kończy się `SDL_Delay(16)`, więc FPS jest sztucznie ograniczony i NIE mówi nic
  o koszcie renderowania. Mierzymy **czas pracy w klatce** (od początku inputu do
  `SDL_RenderPresent`), nie FPS.
- Mierz build release: `make clean && make release`. Pomiar `-O0` jest bezwartościowy
  dla porównań optymalizacji.
- Pozycja kamery wpływa na wynik (bliska ściana = wysokie kolumny). Do porównań używaj
  tej samej pozycji startowej i nie ruszaj kamerą albo ustal powtarzalny scenariusz.

## Poziom 1: czas klatki i funkcji (instrumentacja)
Proponowane narzędzie — autor implementuje je sam (to dobre ćwiczenie):
- licznik oparty o `SDL_GetPerformanceCounter()` / `SDL_GetPerformanceFrequency()`,
- pomiar wokół: `render_floor_ceiling`, `raycaster`, uploadu tekstury, całej klatki,
- akumulacja przez N klatek (np. 300) i wypis średniej oraz maksimum w ms,
- całość pod `#ifdef PROFILE`, aby nie zaśmiecać normalnego buildu.
  Kompilacja: `make clean && make release CC="clang -DPROFILE"`.

Przy pierwszym użyciu tego skilla: jeśli instrumentacji nie ma w kodzie, opisz autorowi
etapy jej dodania (zgodnie z zasadą małych kroków z CLAUDE.md), nie pisz jej sam.

## Poziom 2: profil CPU (bez zmian w kodzie)
- Linux: `perf record -g ./twin_peaks` (pograj ~10 s, zamknij) → `perf report`
  Wymaga buildu z symbolami: `make clean && make release CC="clang -g"`.
- Alternatywa: `valgrind --tool=callgrind ./twin_peaks` (bardzo wolne, ale dokładne
  liczniki instrukcji, deterministyczne → dobre do porównań A/B) → `callgrind_annotate`.

## Poziom 3: asembler pojedynczej funkcji
Gdy pytanie brzmi „czy kompilator to zoptymalizował?”:
`clang -O2 -std=c11 -Iinclude $(sdl2-config --cflags) -S src/renderer.c -o - | less`

## Raport z pomiaru
Zawsze w tej formie, żeby dało się porównać sesje:

```
Commit: <hash>   Build: release (-O2)   Rozdzielczość: 800x600
Scenariusz: <pozycja/mapa/czas>
| Sekcja               | śr. ms | max ms | % klatki |
|----------------------|--------|--------|----------|
| render_floor_ceiling |        |        |          |
| raycaster            |        |        |          |
| upload + present     |        |        |          |
| cała klatka          |        |        |          |
```

Po zmianie: ta sama tabela + kolumna różnicy. Różnice <3% traktuj jako szum,
chyba że pomiar callgrind (deterministyczny) mówi inaczej.

Zaproponuj autorowi zapisanie wyników w `docs/perf-log.md` (dopisuje sam).
