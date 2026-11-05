Build: release (-O2) -DPROFILE   Rozdzielczość: 800x600   CPU: i7-5500U, zasilacz, governor schedutil
Scenariusz: map.txt, pozycja startowa (x=400, y=500, angle=4.7), kamera nieruchoma
3 serie × 300 klatek po odrzuceniu serii rozgrzewkowej; rozrzut między seriami < 1,5%

| Sekcja               | śr. ms | max ms | % klatki |
|----------------------|--------|--------|----------|
| clear_framebuffer    |  0.290 |  1.414 |    1.4%  |
| render_floor_ceiling | 14.451 | 20.130 |   68.7%  |
| raycaster            |  5.461 |  9.736 |   26.0%  |
| upload + present     |  0.778 |  2.967 |    3.7%  |
| cała klatka          | 21.030 | 28.266 |  100.0%  |

Callgrind (release -g, 1 klatka, ten sam widok) — instrukcje na klatkę:
| Funkcja (inclusive)  | Ir         | uwagi                                  |
|----------------------|------------|----------------------------------------|
| render_floor_ceiling | 45 070 616 | 479 200× put_pixel, 958 400× floor()   |
| raycaster            | 20 190 592 | per-pixel put_pixel, 800× cast_ray     |
| put_pixel (łącznie)  |     —      | ~841 tys. wywołań/klatkę, niezinlinowana |

Wynik perf

Udział w czasie całego programu:


|       Funkcja        |    %    |
|----------------------|---------|
| render_floor_ceiling | 59,0    |
| raycaster            | 22,8    |
| put_pixel            | 6,5     |
| floor (libm + PLT)   | ok. 5,2 |
| clear_framebuffer    | 3,1     |

Co kosztuje wewnątrz render_floor_ceiling (perf przypisuje próbkę instrukcji następującej po tej wolnej, więc to przybliżenie):


|                     Źródło                     |  Linie  |   ~% funkcji  |
|------------------------------------------------|---------|----------|
| 2× idiv (% tex->width/height)                  | 306–307 | ok. 26%  |
| cieniowanie (apply_shade) int→float→int na piksel | 311  | 25–30%   |
| odczyt tekseli                                 | 309     | ok. 13%  |
---

## Po B1.1–B1.3 + B2.1–B2.2 (commit 5bff22b, 2026-11-04)

Build: release (-O2) -DPROFILE   Rozdzielczość: 800x600   CPU: i7-5500U, schedutil
Scenariusz: map.txt, pozycja startowa, kamera nieruchoma; ogranicznik klatki (B3.5)
4 serie × 300 klatek po odrzuceniu serii rozgrzewkowej; rozrzut między seriami ~±5%

Zmiany: B1.1 współrzędne tekstury podłogi 16.16 (bez `idiv`/`floor()` per piksel),
B1.2 + B2.2 cieniowanie całkowite `shade_mul` (mnożnik raz na wiersz/kolumnę),
B1.3 + B2.1 zapis bezpośrednio do `framebuffer` (bez `put_pixel`).

| Sekcja               | śr. ms | max ms | % klatki | po B3.5 | różnica |
|----------------------|--------|--------|----------|---------|---------|
| clear_framebuffer    |  0.429 |  1.886 |    5.0%  |  0.465  |  −8% (szum) |
| render_floor_ceiling |  4.028 |  8.043 |   47.2%  | 11.150  | **−64%** |
| raycaster            |  3.035 |  9.414 |   35.6%  |  4.251  | **−29%** |
| upload + present     |  0.976 |  3.537 |   11.4%  |  0.718  | +36% (*) |
| cała klatka          |  8.530 | 18.919 |  100.0%  | 16.623  | **−49%** |

(*) Kod uploadu się nie zmienił. Prawdopodobnie efekt taktowania CPU: pętla teraz śpi
~50% klatki, więc schedutil częściej obniża zegar (niezweryfikowane).
Wniosek jak wcześniej: ms porównywać razem z Ir.

Callgrind (release -g, 2015 klatek, ten sam widok) — instrukcje na klatkę:
| Funkcja (inclusive)  | Ir         | B0         | różnica | Ir/piksel |
|----------------------|------------|------------|---------|-----------|
| render_floor_ceiling | 17 298 584 | 45 070 616 | **−62%** | 36 (było 94) |
| raycaster            |  9 701 260 | 20 190 592 | **−52%** | —         |

Obecny podział: podłoga/sufit ~47%, ściany ~36%, upload ~11%, clear ~5%.
Overdraw podłogi (~75% pikseli w tym widoku) — plan B1.4 odłożony do decyzji.

## B4: flagi kompilatora (commit 5bff22b)

Ten sam scenariusz, 4 serie × 300 klatek na wariant, uruchamiane kolejno.

| Wariant                    | podłoga ms | ściany ms | klatka ms |
|----------------------------|------------|-----------|-----------|
| -O2                        | 3.60 (**)  | 3.12 (**) | 8.11 (**) |
| -O2 -march=native          | 3.50       | 3.20      | 8.14      |
| -O2 -march=native -flto    | 3.44       | 2.84      | 7.89      |

(**) bez 1. serii (10,2 ms, odstająca); ze wszystkimi czterema: 3.80 / 3.32 / 8.64.
Rozrzut między seriami ±8% → różnice wariantów (≤3% na klatce) mieszczą się w szumie.
`put_pixel` i `apply_shade` nie są już na ścieżce gorącej (B1.3, B2.1, B2.2), więc
pierwotne pytanie B4 o inlining jest nieaktualne.
Wniosek: zmiana flag w Makefile niepotrzebna.

## C1: pamięć przy przejściach między mapami (commit 5bff22b)

Metoda: build debug, gdb zatrzymany przed pierwszą klatką, `handle_exit(&cam, &game)`
wywołane 2× (rozgrzewka: wczytanie tekstur map2) + 20× + 100× (map.txt ↔ map2.txt),
`malloc_stats()` po każdej fazie.

| Faza          | heap in use (B) | texman count |
|---------------|-----------------|--------------|
| po 2 przejściach   | 16 744 400 | 3 |
| po 22 przejściach  | 16 744 608 | 3 |
| po 122 przejściach | 16 744 608 | 3 |

+208 B jednorazowo (bufor libc/stdio przy pierwszych `printf`), potem brak wzrostu.
ASan+UBSan: te same 122 przejścia — brak błędów; normalne uruchomienie + SIGTERM
(czyste wyjście przez `sdl_cleanup`) — LeakSanitizer bez raportu.
Valgrind memcheck pominięty (mesa pod valgrindem bardzo wolna; ASan wystarczył).

## S8: koszt sprite'ów — 200 sprite'ów (11b5f6d vs 11b5f6d + S4/S5, 2026-11-05)

Metoda: headless bench (bez okna i present) — ten sam kod `render_floor_ceiling`,
`raycaster`, `render_sprites` co w grze, build `-O2 -g`, CPU i7-5500U.
Mapa testowa (generowana poza repo, stałe ziarno): 24×24, ściany na brzegach, 5 filarów,
200 sprite'ów z 5 PNG (`generate_sprites.py`), scale 0.3–1.0.
„stary” = commit 11b5f6d (przed S4/S5), „nowy” = S4 (bufor sortowania per mapa) + S5 (odrzucanie
przed sortowaniem). 3 serie × 300 klatek naprzemiennie stary/nowy + callgrind 1 klatka na widok.

Widoki:
- A (1200, 1150, 0.3) — środek sali, dużo sprite'ów w polu widzenia, stołek i roślina blisko
- B (300, 1150, π) — przodem do zachodniej ściany, ~1 sprite widoczny
- C (995, 1139, 0) — 0,4 kafelka od rośliny; dwie rośliny zasłaniają cały ekran (najgorszy przypadek)

Czasy (ms, średnia z 3 serii × 300 klatek):
| Widok | Sekcja               | seria 1 st/nw | seria 2 st/nw | seria 3 st/nw | śr. stary | śr. nowy |
|-------|----------------------|---------------|---------------|---------------|-----------|----------|
| A     | render_floor_ceiling | 2.207 / 2.145 | 2.325 / 2.312 | 2.499 / 2.412 | 2.34      | 2.29     |
| A     | raycaster            | 0.379 / 0.353 | 0.401 / 0.420 | 0.506 / 0.429 | 0.43      | 0.40     |
| A     | render_sprites       | 0.628 / 0.579 | 0.651 / 0.598 | 0.698 / 0.617 | 0.66      | 0.60     |
| B     | render_floor_ceiling | 2.139 / 2.148 | 2.240 / 2.460 | 2.243 / 2.671 | 2.21      | 2.43     |
| B     | raycaster            | 1.089 / 1.090 | 1.192 / 1.399 | 1.137 / 1.481 | 1.14      | 1.32     |
| B     | render_sprites       | 0.042 / 0.024 | 0.045 / 0.026 | 0.045 / 0.030 | 0.044     | 0.027    |
| C     | render_floor_ceiling | 2.063 / 2.227 | 2.574 / 2.216 | 2.334 / 2.228 | 2.32      | 2.22     |
| C     | raycaster            | 0.299 / 0.331 | 0.397 / 0.328 | 0.350 / 0.322 | 0.35      | 0.33     |
| C     | render_sprites       | 2.814 / 2.935 | 3.449 / 2.910 | 3.156 / 2.982 | 3.14      | 2.94     |

Rozrzut ms między seriami ±10–15% (podłoga i ściany w B różnią się, choć kod jest ten sam) —
miarodajny jest callgrind.

Callgrind (1 klatka, Ir inclusive):
| Widok | Funkcja              | stary      | nowy       | różnica |
|-------|----------------------|------------|------------|---------|
| A     | render_floor_ceiling | 17 299 364 | 17 299 364 | 0       |
| A     | raycaster            |  1 926 577 |  1 926 577 | 0       |
| A     | render_sprites       |  5 322 163 |  5 055 767 | −5%     |
| A     | qsort (+ komparator) |     78 852 |      4 599 | −94%    |
| B     | render_floor_ceiling | 17 299 364 | 17 299 364 | 0       |
| B     | raycaster            |  6 542 423 |  6 542 423 | 0       |
| B     | render_sprites       |    253 844 |    184 585 | −27%    |
| B     | qsort (+ komparator) |     78 324 |         19 | —       |
| C     | render_floor_ceiling | 17 299 364 | 17 299 364 | 0       |
| C     | raycaster            |  1 857 689 |  1 857 689 | 0       |
| C     | render_sprites       | 23 596 360 | 23 227 758 | −1.6%   |
| C     | qsort (+ komparator) |     78 230 |      6 336 | —       |

Rozkład w widoku C (nowy, pętla wewnętrzna `render_sprites`): ~980 tys. iteracji na klatkę
(ekran 2× — dwie nakładające się rośliny), ~23 Ir/piksel: odczyt tekseli + clamp `texY`,
`if` na alfę, `shade_mul`. Piksele przezroczyste kosztują prawie tyle co widoczne.
W widoku B pętla odrzucania 200 sprite'ów to ~9 tys. Ir (~45 Ir/sprite).

Wnioski:
- S5 (odrzucanie): −5% Ir przy wielu sprite'ach w kadrze, −27% przy kilku; praca per sprite
  (transformacja + sortowanie 200 szt.) była już tania (~80 tys. Ir, ~0,2% klatki).
- Koszt = wypełnianie pikseli. Jeden sprite na cały ekran ≈ 2,9 ms, więcej niż podłoga + ściany.
- Bufor pokrycia front-to-back (D5.2) teraz nieuzasadniony: nie pomaga na przezroczyste piksele
  ani na pojedynczy duży sprite. Kandydaci na dalsze kroki: zakres nieprzezroczystych wierszy
  per kolumna tekstury (liczony przy wczytaniu), krok stałoprzecinkowy bez clampa w pętli
  (jak B1/B2 dla ścian).
