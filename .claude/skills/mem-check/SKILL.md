---
name: mem-check
description: Check TwinPeaks2D for memory errors and leaks (out-of-bounds, use-after-free, leaks, uninitialized reads) with AddressSanitizer, UBSan and Valgrind, plus a manual ownership review. Use when the user asks about leaks, crashes, segfaults, memory usage or before merging changes to map/texture loading.
---

# Kontrola pamięci

Nie edytujesz plików. Uruchamiasz narzędzia, interpretujesz wyniki, wskazujesz przyczyny.

## Krok 1: Przegląd własności pamięci (statyczny)
Dla zakresu wskazanego przez autora (lub modułów `map.c`, `texture.c`,
`texturemanager.c`, `camera.c:handle_exit` jeśli nie wskazał):
- Kto alokuje, kto zwalnia, kiedy? Zrób tabelę: zasób → alokacja → zwolnienie → ścieżki błędów.
- Czy przy przejściu między mapami (`handle_exit`) coś rośnie bez końca?
  (stary `Grid` jest zwalniany — sprawdź, co dzieje się z teksturami w `TextureManager`)
- Tablice o stałym rozmiarze i ich granice: `slots[MAX_TEXTURES]`, `exits[4][16]`,
  `char name[128]`, bufory w `read_map_from_file` czytane przez `fscanf("%s")`.
- Pola struktur, które są czytane, a nigdy nie zapisane (odczyt niezainicjalizowanej pamięci).
- Wartości zwracane przez `malloc`, `fscanf`, `load_texture` — czy są sprawdzane?

## Krok 2: Sanitizery
```
make clean && make CC="clang -fsanitize=address,undefined -fno-omit-frame-pointer"
./twin_peaks
```
Poproś autora o scenariusz: uruchomienie, ruch, kilka przejść między mapami, wyjście ESC.
Uruchomienie gry wymaga zgody autora (otwiera okno).

Interpretacja:
- Raport ASan: pierwsza ramka stosu w kodzie projektu (nie w SDL) to miejsce do analizy.
- Wycieki zgłaszane wewnątrz SDL/sterowników grafiki (libGL, Mesa, X11) to zwykle
  szum — odfiltruj, chyba że stos przechodzi przez kod projektu.
- Uwaga: `sdl_cleanup` wywołuje `exit()`, więc LeakSanitizer zobaczy tylko to,
  czego nie zwolniono przed tym wywołaniem.

## Krok 3 (opcjonalnie): Valgrind
Na buildzie debug bez sanitizerów (`make clean && make`):
`valgrind --leak-check=full --track-origins=yes ./twin_peaks`
Valgrind lepiej niż ASan wykrywa odczyty niezainicjalizowanej pamięci (`--track-origins`).

## Raport
```
| # | Typ (leak / OOB / UAF / uninit / UB) | Plik:linia | Przyczyna | Jak potwierdzono |
```
Następnie: jeden problem rekomendowany do naprawy jako pierwszy + pytanie naprowadzające.
Pozostałe → lista „Zauważone przy okazji”.
