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
