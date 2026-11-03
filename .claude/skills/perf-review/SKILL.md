---
name: perf-review
description: Static performance review of C code in TwinPeaks2D (CPU time, memory, cache behaviour) for one function or file the user names. Use when the user asks whether code is fast/efficient, asks to review performance, or before/after optimizing the renderer. Produces findings only, never edits code.
---

# Przegląd wydajności (statyczny)

Cel: znaleźć koszty w JEDNEJ wskazanej funkcji lub pliku. Nie edytujesz plików.
Jeśli użytkownik nie wskazał zakresu — zapytaj, co przeglądamy.

## Krok 1: Ustal kontekst wykonania
- Ile razy na klatkę wykonuje się ten kod? (raz / per kolumnę = 800 / per piksel = 480 000)
- Policz rząd wielkości operacji na klatkę i na sekundę przy 60 FPS.
- Zaznacz, czy kod jest na ścieżce gorącej (patrz CLAUDE.md).

## Krok 2: Przejdź listę kontrolną
Dla każdego punktu: znaleziono / nie dotyczy. Podawaj numery linii.

**Praca w pętli**
- Obliczenia niezależne od zmiennej pętli (do wyniesienia przed pętlę)
- Wywołania funkcji per piksel (`put_pixel`, `apply_shade`) — czy kompilator je zinlinuje?
  Funkcje w osobnym `.c` bez LTO NIE zostaną zinlinowane między jednostkami kompilacji.
- Sprawdzanie granic, które można wykonać raz dla całego zakresu
- Dzielenie i modulo w pętli wewnętrznej (`%`, `/` na int i double)
- `floor()`, `sin/cos/tan` w pętli; mieszanie `float`/`double` (konwersje)
- Rozgałęzienia zależne od danych w pętli wewnętrznej

**Pamięć i cache**
- Kolejność dostępu do framebuffera/tekstur: wierszowo (dobrze) czy kolumnowo (skoki co
  `SCREEN_WIDTH * 4` bajtów — gorzej). Raycaster ścian pisze kolumnami — oceń koszt.
- Rozmiar struktur w gorącej ścieżce, wyrównanie, padding
- Alokacje (`malloc`/VLA) w każdej klatce
- Overdraw: piksele zapisywane więcej niż raz na klatkę (clear → floor/ceiling → walls)

**Pamięć ogólnie**
- Każdy `malloc` ma odpowiadający `free`? Ścieżki błędów zwalniają zasoby?
- Rośnie zużycie pamięci przy przejściach między mapami?
- Zapisy poza tablicą o stałym rozmiarze (`MAX_TEXTURES`, `exits[4][16]`, bufory nazw)

## Krok 3: Raport
Format:

```
## Zakres: <funkcja/plik>, wykonania na klatkę: <N>

| # | Linia | Problem | Szacowany wpływ | Pewność |
|---|-------|---------|-----------------|---------|

Wpływ: wysoki / średni / niski — uzasadnij liczbą operacji, nie intuicją.
Pewność: "pomiar potrzebny", jeśli bez profilera nie da się tego rozstrzygnąć.
```

Następnie:
- **Rekomendowany pierwszy problem** — jeden, z największym stosunkiem zysku do ryzyka.
- **Pytanie naprowadzające** dla autora, jak mógłby to rozwiązać (nie gotowe rozwiązanie).
- **Jak zmierzyć efekt** — odeślij do `/perf-measure`.

## Zasady
- Nie przepisuj kodu. Najwyżej pseudokod 3–5 linii ilustrujący ideę, jeśli autor poprosi.
- Mikrooptymalizacje (np. zamiana mnożenia na przesunięcie) zgłaszaj tylko, gdy
  `-O2` ich sam nie zrobi — jeśli nie masz pewności, zaproponuj sprawdzenie asemblera
  (`clang -O2 -S`).
- Czytelność ma wartość: jeśli optymalizacja daje <5% a komplikuje kod, napisz to.
