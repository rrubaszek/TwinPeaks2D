# TwinPeaks2D — instrukcje dla Claude

Doom-style, first-person game w C11 z użyciem SDL. 

## Zasady współpracy (NAJWAŻNIEJSZE — mają pierwszeństwo przed wszystkim poniżej)

1. **Autor pisze kod sam i z tobą.** Twoja rola domyślna: analiza, wyjaśnianie, plan, review, dopiero potem implementacja.
   Nie implementuj rozwiązań, dopóki autor wprost o to nie poprosi.
2. **Żadnych zmian bez zgody.** Zanim użyjesz Edit/Write na jakimkolwiek pliku w repo,
   pokaż dokładnie, co chcesz zmienić (plik, funkcja, diff lub opis) i poczekaj na „tak”.
   Zgoda dotyczy jednej zmiany, nie całej sesji.
3. **Jeden problem na raz.** Jeśli w trakcie zauważysz inne błędy lub okazje do
   optymalizacji — zapisz je na liście „Zauważone przy okazji” na końcu odpowiedzi
   i NIE zajmuj się nimi teraz.
4. **Problem dzielimy na etapy.** Każdy problem rozbij na kroki, z których każdy:
   - dotyka co najwyżej jednej funkcji (wyjątkowo dwóch, gdy zmiana sygnatury),
   - to maksymalnie ~20–30 linii zmienionego kodu,
   - kończy się stanem, który się kompiluje (`make`) i da się sprawdzić.
   Przedstaw plan etapów, potem realizujemy je pojedynczo. Po każdym etapie: stop,
   autor sprawdza, dopiero potem następny.
5. **Gdy autor prosi o kod** — dawaj fragment dla bieżącego etapu, nie cały plik.
   Wyjaśnij, dlaczego tak, i jaki jest koszt/kompromis.
6. **Nie zgaduj** — jeśli założenie (np. o zachowaniu SDL, formacie mapy) nie wynika
   z kodu, powiedz to i zaproponuj, jak to sprawdzić.
7. **Git**: nie commituj, nie pushuj, nie zmieniaj gałęzi. Commity robi autor.
   Możesz zaproponować komunikat commita.

## Budowanie i uruchamianie

- `make` — build debug (`-g -O0 -DDEBUG`), kompilator `clang`
- `make release` — build `-O2 -DNDEBUG`
- `make clean` — usuwa `build/` i binarkę
- `make run` — build debug + uruchomienie (`./twin_peaks`)
- Uwaga: `make` i `make release` dzielą katalog `build/`. Przy zmianie wariantu
  zawsze najpierw `make clean`, inaczej zostaną stare obiekty.
- Sanitizery bez zmiany Makefile:
  `make clean && make CC="clang -fsanitize=address,undefined -fno-omit-frame-pointer"`
- Gra wymaga środowiska graficznego (okno SDL) i tekstur w `maps/textures/`
  (w `.gitignore`, generowane przez `helpers/generate_textures.py`).
- Brak testów automatycznych. „Sprawdzenie” = kompiluje się bez ostrzeżeń
  + autor uruchamia grę.

## Architektura

| Moduł | Odpowiedzialność |
|---|---|
| `src/game.c` | `main`, pętla gry, init/cleanup SDL |
| `src/camera.c` | ruch, kolizje, obsługa wyjść między mapami (`handle_exit`) |
| `src/renderer.c` | DDA (`cast_ray`), ściany (`raycaster`), podłoga/sufit, niskie ściany (`render_low_walls`), sprite'y, cieniowanie |
| `src/framebuffer.c` | globalny framebuffer, `put_pixel`, `clear_framebuffer` |
| `src/map.c` | parser plików `maps/*.txt` → `Grid`, kafelki |
| `src/texture.c`, `src/texturemanager.c` | ładowanie PNG do `Uint32*`, cache tekstur po id |
| `include/constants.h` | rozdzielczość, FPS, FOV, limity |

Pętla klatki: input → `move` → `camera_get_view` → `clear_framebuffer` →
`raycaster` → `render_floor_ceiling` → `render_low_walls` → `render_sprites` → upload
tekstury → present → ogranicznik klatki (`SDL_Delay` na resztę budżetu).
Kolejność jest wymagana: `raycaster` zapisuje zakres pełnej ściany i niskie ściany per kolumna,
podłoga pomija zakres pełnej ściany, niskie ściany i sprite'y rysują się na podłodze.

**Ścieżka gorąca** (wykonywana per piksel / per kolumna, każda klatka):
`render_floor_ceiling` (pętla 800×600), wewnętrzna pętla `raycaster`, `put_pixel`,
`apply_shade`, `cast_ray`. Tu każda zmiana wymaga uwagi pod kątem wydajności.

## Konwencje kodu

- C11, `-Wall -Wextra -Wpedantic` — kod ma kompilować się bez nowych ostrzeżeń.
- Nagłówki projektu w `include/`, includowane jako `<nazwa.h>`.
- Funkcje `snake_case`, typy `PascalCase`, stałe `UPPER_CASE` w `constants.h`.
- Współrzędne: świat w pikselach (`Camera.x/y`), raycasting w przestrzeni kafelków
  (`CameraView.posX/posY` = świat / `tile_size`).
- Komentarze po angielsku, krótkie; TODO w kodzie to backlog autora — nie usuwaj ich.
- Kod modularny: nowa funkcjonalność = nowa funkcja/moduł, nie rozbudowa `main`.

## Cele projektu

Aktualne cele i ich priorytety są w `docs/GOALS.md`. Pracujemy nad tym celem,
który autor wskaże w danej sesji.

## Skille projektu

- `/perf-review` — statyczny przegląd wydajności (CPU, pamięć, cache) wskazanej funkcji
- `/perf-measure` — procedura pomiaru czasu klatki/funkcji przed i po zmianie
- `/mem-check` — wycieki, błędy dostępu do pamięci (ASan/UBSan/Valgrind)
