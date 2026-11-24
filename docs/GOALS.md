# TwinPeaks2D — cele

> SZKIC do decyzji autora. Statusy: `?` = do decyzji, `TODO`, `WIP`, `DONE`, `ODRZUCONE`.
> Każdy cel ma kryterium ukończenia, które da się sprawdzić.

## Wizja
- **Gatunek:** gra eksploracyjna w klimacie Twin Peaks z interakcjami, pobocznym wątkiem
  fabularnym i zagadką. Gracz sam decyduje, jak szybko rozwiązuje zagadkę i ile świata
  eksploruje (brak wymuszonej liniowości).
- **Interakcje:** klawisz akcji na obiekt/NPC, na który patrzy gracz; ekwipunek
  (przedmioty używane w zagadkach); stan świata zapamiętywany między mapami
  (otwarte drzwi, zabrane przedmioty, odbyte rozmowy).
- **Świat:** kilkanaście+ map → potrzebny prosty edytor map.
- **Platforma:** tylko Linux (Arch) autora; przenośność builda nie jest celem.
- **Budżet wydajności:** 16,6 ms na klatkę (60 FPS, jak ogranicznik `FPS`), 800×600 — decyzja B0.5 z 2026-11-21.
- **Cel edukacyjny:** wszystko po trochu — poprawność C i pamięć, wydajność, grafika.
- `?` Sposób przekazywania tekstu graczowi (opisy przedmiotów, dialogi) — do decyzji;
  obecnie brak renderowania tekstu/HUD.

---

## A. Poprawność i stabilność (fundament przed optymalizacją)

### A1 `?` Cache tekstur rzeczywiście deduplikuje -- DONE
Problem: `texman_load` porównuje `slots[i]->name`, ale pole `name` nigdy nie jest
ustawiane w `load_texture`. Każde wczytanie mapy dodaje nowe sloty; brak kontroli
`count < MAX_TEXTURES` → po kilku przejściach między mapami zapis poza tablicą.
Kryterium: wielokrotne przejścia między mapami nie zwiększają `tm->count`; ASan czysty.

### A2 `?` Odporność na błędy ładowania -- DONE
Problem: `load_texture` może zwrócić NULL, a `raycaster` dereferuje teksturę ściany
bez sprawdzenia; wyniki `malloc`/`fscanf` w parserze mapy nie są sprawdzane;
`fscanf("%s")` do `exits[4][16]` bez limitu długości.
Kryterium: brak pliku tekstury / błędna mapa → komunikat i czyste wyjście, nie crash.

### A3 `?` Mapowanie tekstury ścian przy bliskim podejściu -- DONE
Problem: `wall_height` jest obcinane do `SCREEN_HEIGHT` przed wyliczeniem `texY`,
więc przy ścianie tuż przed kamerą tekstura jest ściśnięta zamiast przycięta.
Brak ochrony przed `perpWallDist == 0`.
Kryterium: tekstura nie „pływa” przy podchodzeniu do ściany.

### A4 `?` (odłożone) Sporadyczny SIGSEGV przy wyjściu z gry
Problem: ok. 1 na 3 wyjścia kończy się SIGSEGV w `SDL_DestroyRenderer` → libSDL3 → Mesa
(raz w `free()`). Core dumpy 37845, 38912 (`coredumpctl info <pid>`). Proponowany eksperyment:
20× uruchomienie + SIGTERM na buildzie bieżącym / ASan / sprzed sprite'ów (d15bfe1).
Kryterium: 20 kolejnych wyjść bez crasha albo przyczyna wskazana poza kodem projektu.

### A5 `TODO` Błąd wyjść między mapami
Problem: `handle_exit` (`src/camera.c`) zawsze bierze pierwsze nie-NULL wyjście
(kolejność 2, 3, 1, 0), niezależnie od kafelka, na który wszedł gracz.
Kryterium: mapa z dwoma wyjściami prowadzi do dwóch różnych map.

## B. Wydajność obliczeniowa

### B0 `DONE` (budżet B0.5: 16,6 ms) Pomiar bazowy (warunek wstępny dla B1–B4)
Instrumentacja czasu klatki i sekcji (`/perf-measure`), zapisany wynik bazowy.
Kryterium: tabela czasów w `docs/perf-log.md` dla aktualnego commita.

### B1 `DONE` (B1.1–B1.3: −64% czasu; B1.4 overdraw: −19…−41% podłogi zależnie od widoku) Koszt podłogi i sufitu
`render_floor_ceiling` przetwarza każdy piksel ekranu (480 000/klatkę) z kilkoma
wywołaniami funkcji, operacjami zmiennoprzecinkowymi i modulo na piksel; część tych
pikseli jest potem nadpisywana przez ściany (overdraw).
Kryterium: ustalony procentowy zysk względem B0 (do określenia przez autora).

### B2 `DONE` (B2.1–B2.2: −29% czasu; zapis kolumnami zmierzony — koszt niemierzalny, bez zmian) Koszt rysowania ścian
Pętla wewnętrzna `raycaster` pisze kolumnami (dostęp do pamięci co 3200 B) przez
`put_pixel` z kontrolą granic i cieniowaniem per piksel.
Kryterium: j.w.

### B3 `DONE` Pętla gry niezależna od FPS
`SDL_Delay(16)` + czas pracy ≠ stałe 60 FPS; ruch kamery liczony „na klatkę”,
więc prędkość gracza zależy od wydajności.
Kryterium: prędkość ruchu identyczna przy sztucznym spowolnieniu klatki.

### B4 `DONE` (pomiar: -march=native/-flto w szumie; put_pixel/apply_shade poza ścieżką gorącą) Funkcje gorącej ścieżki a inlining
`put_pixel` i `apply_shade` są w innych jednostkach kompilacji niż pętle, które je
wołają. Do zbadania: czy kompilator je inlinuje, i co daje `-flto` vs przeniesienie.
Kryterium: decyzja poparta pomiarem.

## C. Oszczędność pamięci

### C1 `DONE` (122 przejścia: heap stały, ASan/LSan czyste — `docs/perf-log.md`) Bilans pamięci przy przejściach między mapami
Kryterium: zużycie pamięci stabilne po 20 przejściach (Valgrind/ASan bez wycieków
z kodu projektu).

### C2 `DONE` (`sprite_order` alokowane raz na mapę w `Grid`) Alokacje w każdej klatce
`render_sprites` alokowało tablicę odległości (`malloc`) i VLA w każdej klatce.
Kryterium: zero alokacji na stercie w pętli klatki.

## D. Funkcjonalność (z TODO w kodzie)
- D1 `DONE` Sprite'y renderowane do framebuffera — z_buffer, tekstury z tabeli tekstur mapy,
  przezroczystość (alfa), stoją na podłodze (skala 1.0 = wysokość ściany), odrzucanie przed sortowaniem.
- D5 `?` Las z animacją wiatru (wymaga D1)
  - D5.1 Przezroczystość sprite'ów (alfa z PNG zamiast czarnego tła BMP) — `DONE`; tekstury drzew — `DONE`
    (`helpers/generate_trees.py`: proceduralna daglezja 64×64 i 64×192, `--seed` = inne drzewo).
  - D5.2 Wiele drzew: odrzucanie poza polem widzenia i za odległością, rysowanie od przodu do tyłu
    z buforem pokrycia (bez overdraw — ta sama idea co odłożone B1.4).
  - D5.3 `DONE` (W1–W4, W6, W7; W5 odłożone) Wiatr — sprite'y zewnętrzne (drzewa, krzaki) kołyszą się delikatnie; wnętrza stoją.
    - W1 Pole `float wind` w `Sprite` + parser: opcjonalne 8. pole linii sprite'a
      `x y type texture scale collision_r [z [wind]]` (0 = nieruchomy, 1 = drzewo, ~0.5 = krzak);
      opis w `docs/map-format.md`.
    - W2 Czas gry: `world_time` (suma `dt`) w pętli `game.c`, przekazywany do `render_sprites`.
    - W3 `wind_sway(t, x, y)` → [−1, 1]: 2–3 sinusy fali biegnącej przez mapę (podmuchy)
      + faza per sprite z pozycji; stałe `WIND_*` w `constants.h`.
    - W4 `render_sprites`: dla `wind > 0` tablica przesunięć per wiersz
      `WIND_AMPLITUDE * wind * sway * szerokość * (1 - v)^2` (na stosie), `texX` liczone per piksel;
      sprite'y z `wind = 0` bez zmian.
    - W5 `ODŁOŻONE` (obecne mapy go nie wymagają) Poszerzenie zakresu kolumn i odrzucania
      o maksymalne przesunięcie (korona nie jest obcinana na brzegu ekranu ani sprite'a).
    - W6 Edytor: pole `wind` w modelu, odczyt/zapis (z `z`, gdy `wind ≠ 0`), walidacja `wind ≥ 0`,
      test w `editor/tests/test_txt_format.py`; pole „Wind” w panelu Sprite.
    - W7 Mapy: `wind` = 1 dla drzew w `maps/map2.txt`; wnętrza (`map.txt`) bez zmian.
    Kryterium: drzewa na `map2` kołyszą się niezsynchronizowanie, podmuch widocznie
    przechodzi przez las, podstawa stoi w miejscu, roślina w dinerze się nie rusza.
  - D5.4 Pomiar (profiler + callgrind, np. 200 drzew) względem budżetu klatki.
  - D5.5 Edytor: pędzel „rozsyp drzewa” (gęstość, losowa skala); opcjonalnie parametry
    wiatru per mapa.
  - D5.6 Opcjonalnie: parametry wiatru per mapa (siła, kierunek) zamiast stałych — razem z D5.5.
  - D5.7 `DONE` (D5.8 N7) Drzewa wyższe niż ściany: sprite z `scale` > 1 i wysoką teksturą (64×192).
    Dziś sprite za bliższą ścianą znika w całej kolumnie (`z_buffer`); ma być rysowany powyżej
    górnej krawędzi tej ściany (`wall_start[col]` z `raycaster`). Opcjonalnie niebo zamiast
    sufitu na mapach zewnętrznych.
    Kryterium: drzewo `scale 3` stojące za ścianą wystaje ponad nią.
  - D5.8 `DONE` (kierunek zmieniony na plan H — D5.9) Niebo, ściółka, ściana skraju lasu
    - N1 `DONE` `helpers/generate_outdoor.py`: `sky.png` (panorama 1024×256 na 360°, chmury,
      góry, linia jodeł) i `forest_floor.png` (64×64 bez szwów: mech, igły, szyszki).
    - N2–N3 `DONE` Sufit kafelka `-1` = otwarte niebo: `CEILING_SKY`, `Grid.sky_tex_id`
      (`sky.png` wczytywane tylko, gdy mapa go używa); `render_floor_ceiling` rysuje panoramę
      (kolumna z kąta promienia, `atan2` raz na kolumnę ekranu), bez przyciemniania; poza mapą
      sufit najbliższego kafelka brzegowego (`plane_tex_id`).
    - N4–N5 `DONE` Edytor: sufit `-1` (`CEILING_SKY`, walidacja, ostrzeżenie o braku `sky.png`),
      pozycja „(open sky, ceiling only)” w narzędziu Ceiling texture [6].
    - N6 `DONE` `map2`: niebo nad wszystkimi kafelkami, podłoga `forest_floor.png`.
    - N7 `DONE` = D5.7: bliższa ściana zasłania sprite tylko poniżej `wall_start[col]`.
    - N9 `DONE` Ściana skraju lasu `forest_edge.png` / `forest_edge2.png`
      (`generate_outdoor.py edge [--seed N --name ...]`, złożona z daglezji `render_fir`),
      nieprzezroczysta pod linią czubków.
    - N10 `DONE` Przezroczysta góra ściany: `Texture.top_opaque` (pierwszy nieprzezroczysty wiersz
      kolumny, liczony w `load_texture`); `raycaster` zaczyna ścianę od niego (`wall_start`), więc
      nad czubkami widać niebo i sprite'y zza ściany. Działa dla każdej tekstury ściany.
    - Stan przejściowy: `map2` ma ściany obrzeża `forest_edge*.png` — do zastąpienia w H4.
      Ściana skraju lasu zostaje jako narzędzie (np. gęsty las wewnątrz mapy).
    - Przeniesione: N8 (pomiar) → H5; N11 (mgła) → H2; N12 (`forest.jpeg`) → D5.10.
  - D5.9 `TODO` Otwarty teren bez „pudełka” — **plan H, oficjalny kierunek od 2026-11-24**.
    Na mapach zewnętrznych gracz nie widzi pionowej ściany: ziemia ciągnie się do horyzontu,
    wyżej niebo z linią drzew w oddali; granica mapy jest niewidzialna, ale blokuje ruch.
    Już działa: ruch poza mapę blokuje `is_wall` (`src/camera.c`), podłoga poza mapą = domyślna
    podłoga mapy, sufit poza mapą = niebo z kafelka brzegowego (N3), linia drzew w panoramie.
    Odrzucony wariant: ściana pomalowana „do połowy ziemia, wyżej niebo” — z bliska wygląda
    jak plakat (ziemia bez perspektywy, panorama rozjeżdża się z obrazem na ścianie, szwy
    w narożnikach).
    - H1 Promień opuszczający mapę z kafelka z niebem nie rysuje ściany: `z_buffer` = nieskończoność,
      kolumna bez ściany (`wall_start = wall_end = SCREEN_HEIGHT / 2`); niskie ściany po drodze
      nadal rejestrowane. Mapy wnętrz bez zmian (kafelki brzegowe bez nieba). Dotyczy `cast_ray`
      i `raycaster`; sprawdzić `render_low_walls` oraz N7 w `render_sprites` przy nieskończonym
      `z_buffer`.
    - H2 Podłoga do horyzontu + mgła w kolor horyzontu (dawne N11, część F3): na mapach z niebem
      podłoga, ściany, niskie ściany i sprite'y w oddali zlewają się z kolorem dolnego wiersza
      panoramy w tej samej kolumnie (`sky_u[x]`) zamiast czernieć; wypełnić wiersz horyzontu
      (`p == 0` w `render_floor_ceiling`, dziś pomijany). Ścieżka gorąca: mieszanie z kolorem
      zamiast samego mnożenia.
    - H3 Nowy typ kafelka „granica” (np. `TILE_BARRIER = 5`): blokuje ruch (`is_tile_solid`),
      niewidoczny, promień przez niego przechodzi (`cast_ray`); sprite'y mogą na nim stać.
      Edytor: `TileType`, kolor, narzędzie, walidacja (bez ostrzeżenia „sprite inside a wall”),
      `docs/map-format.md`.
    - H4 Przebudowa `map2`: zamiast ścian obrzeża pas 3–4 kafelków granicy z daglezjami
      (mapa powiększona), niebo nad całością.
    - H5 Pomiar (dawne N8/W8, `/perf-measure`): podłoga zawsze ~pół ekranu, więcej drzew.
      Najpierw naprawić `tools/bench/bench.c`: nie kompiluje się od W2 (`render_sprites`
      ma czwarty parametr `time_s`, wywołania w liniach 46 i 93); dodać pozę dla `map2`.
    Kryterium: w `map2` nie widać pionowej ściany; las ciągnie się za granicą, dalej ziemia
    przechodzi płynnie w linię drzew na horyzoncie; nie da się wyjść poza granicę; czas
    klatki w budżecie B0.5.
  - D5.10 `TODO` (dawne N12) Usunięcie `forest.jpeg`: używa go jeszcze `map.txt` (7 ścian
    w kolumnach 8–9 przy górnej krawędzi, pozycja 3 tabeli) — do decyzji, czym zastąpić;
    potem plik z `maps/textures/`; w testach edytora to tylko nazwy (bez pliku).
  - Opcjonalnie: 2–4 klatki animacji liści, opadające liście (mgła w oddali — D5.9 H2).
  Kryterium: scena z ≥ 200 drzewami kołysze się płynnie (drzewa niezsynchronizowane, widoczne
  podmuchy), czas klatki w budżecie B0.5.
- D2 `DONE` Tekstury per kafelek — numer tekstury kafelka: 0 = domyślna tekstura ścian mapy,
  k ≥ 1 = pozycja k−1 tabeli tekstur (mapy zmigrowane z 1 na 0); używają go ściany i niskie
  ściany; wybór w edytorze (E4). Format: `docs/map-format.md`.
- D3 `?` Zależne stałe w `constants.h` (TODO autora)
- D4 `?` Drzwi, przedmioty interaktywne, NPC (typy już zdefiniowane w `sprite.h`)
  - Drzwi: kilka drzwi na jednej ścianie prowadzących do różnych pomieszczeń (np. korytarz
    Grand Northern Hotel) → wyjścia przypisane do kafelka/drzwi zamiast stałych `exits[4][16]`
    w `Grid` (powiązane z A5 i E3).
- D6 `?` Koszt rysowania sprite'ów (pomiar S8 w `docs/perf-log.md`)
  Koszt to wypełnianie pikseli (~23 Ir/px, także przezroczystych), nie liczba sprite'ów;
  jeden sprite na cały ekran ≈ 2,9 ms (więcej niż ściany + podłoga). Kandydaci: zakresy
  nieprzezroczyste per kolumna tekstury, krok współrzędnych tekstury w stałym przecinku.
  Kryterium: sprite na cały ekran tańszy o ustalony % (pomiar jak S8).
- D7 `DONE` Sprite'y na wysokości — opcjonalne 7. pole `z` w linii sprite'a (podstawa
  w jednostkach wysokości ściany, 0 = podłoga); przy równej głębokości niższy sprite rysowany
  pierwszy (ciasto na stole-sprite'cie). Sprite'y zasłaniane przez bliższe niskie ściany (F5).

## E. Systemy gry (z wizji)
- E1 `?` Akcja „użyj/zbadaj” na obiekt w centrum ekranu (wymaga D1)
- E2 `?` Ekwipunek
- E3 `?` Stan świata trwały między mapami (dziś `handle_exit` ładuje mapę od zera)
- E4 `WIP` Edytor map (format `maps/*.txt`) — v1 w `editor/` (PySide6, PR #6): kafelki + sprite'y,
  walidacja, wybór tekstur z tabeli tekstur mapy; tekstury kafelków (miniatury na siatce),
  wysokość `z` sprite'ów + „On tile top” (sprite postawiony na niskiej ścianie dostaje jej wysokość).
  v2 (gałąź `editor-sprite-tools`): `DONE` edytor pikseli sprite'ów (`editor/tpedit/pixel_editor.py`:
  PNG z alfą, paleta z `helpers/generate_sprites.py`, Tools menu + „Edit…” w panelu Sprite),
  `DONE` „On sprite below” (z = wierzch najwyższego sprite'a w promieniu 0,25 kafelka, bez
  przezroczystych górnych wierszy tekstury). `TODO`: undo, start gracza
- E5 `?` Wyświetlanie tekstu / HUD (zależne od decyzji w Wizji)

## F. Kierunek wizualny (referencja: demo BLOK — retro PS1, wnętrza lat 90.)
Cel przykładowy: wnętrze Double R Diner (szachownica na podłodze, boazeria, lada ze
stołkami, boksy przy oknach, gablota z ciastami, ciepłe lampy).
- F1 `DONE` Post-process „retro” (`src/postfx.c`, ostatni krok klatki): pikselizacja blokami
  `POSTFX_PIXEL` (kolor środka bloku), `POSTFX_LEVELS` poziomów na kanał, dithering Bayer 4×4
  w rozdzielczości bloków (tablica LUT 16×256). Wybrany wariant: przebieg po gotowym obrazie
  800×600, nie niższa rozdzielczość wewnętrzna (ta wymagałaby zamiany ~50 stałych ekranu na
  zmienne). Klawisze: F2 wł./wył., F3 rozmiar bloku 1–4, F4 poziomy 256/32/16/8/4.
  Kryterium: efekt włączany/wyłączany klawiszem, czas klatki w budżecie B0.5.
- F2 `DONE` Podłoga i sufit per kafelek — opcjonalne pola kafelka `type:tex:height[:floor:ceiling]`
  (`docs/map-format.md`), `Tile.floor_tex_id/ceiling_tex_id`; `render_floor_ceiling` liczy pozycję
  w świecie w stałym przecinku 32.32 (kafelek = część całkowita) i zmienia teksturę tylko na
  granicy kafelka. Edytor: narzędzia Floor texture [5] / Ceiling texture [6].
  Kryterium: mapa z dwoma rodzajami podłogi (np. szachownica w dinerze, deski w kuchni).
- F3 `?` Oświetlenie: poziom światła per kafelek + mgła w kolor (nie tylko przyciemnianie).
  Kryterium: ciemny kąt i jasna strefa pod lampą na jednej mapie.
- F4 `?` Rekwizyty jako sprite'y (lada, stołki, boksy, gablota, szafa grająca) — oparte na
  D1 + D5.1; opcjonalnie sprite'y 8-kierunkowe dla dużych mebli.
  Kryterium: scena dinera z ≥ 10 rekwizytami, poprawne zasłanianie przez ściany.
- F5 `DONE` Ściany o różnej wysokości — kafelek o `height < 1` to niska ściana: promień
  przechodzi dalej (do `MAX_LOW_SEGS` = 8 na kolumnę), `render_low_walls` rysuje przednią ścianę
  (cała tekstura ściśnięta do wysokości) i wierzch dla `height < 0.5` (poniżej oczu), od
  najdalszej do najbliższej; sprite'y za ladą są przycinane. TODO: osobna tekstura wierzchu
  (np. obrus) — dziś tekstura kafelka, 1 kopia na kafelek.
  Kryterium: lada widoczna jako niska ściana, za nią widoczne tło.
- F6 `?` Mapa „Double R Diner” jako test całości.

---

## Kolejność
Rytm: bloki tematyczne — kończymy blok, zanim zaczniemy następny.
1. **A — fundament:** A1 (realny zapis poza tablicą po ~5 przejściach) → A2 → A3
2. **B0 — pomiar bazowy** + ustalenie budżetu wydajności w Wizji
3. **B + C — wydajność i pamięć:** B3 → B1 → B2 → B4 → C1 (C2 razem z D1)
   (B3 najpierw: ruch zależny od czasu, zanim optymalizacje zmienią czas klatki)
4. **D — silnik pod grę:** D3 → D2 → D1 (+ C2) → D5 → D4
5. **E — systemy gry:** E1 → E2 → E3 → E4 (E5 po decyzji o tekście)
6. **F — kierunek wizualny:** F1 (niezależne, można wcześniej) → F2 → F3 → F4 (po D1) → F5 → F6

**Bieżąca kolejność (aktualizacja 2026-11-24):** blok „las” (gałąź `visuals`): D5.3 wiatr,
D5.7 wysokie drzewa, D5.8 niebo/ściółka/ściana skraju lasu zrobione → **D5.9 plan H**
(H1 → H2 → H3 → H4 → H5) → D5.10 → dalej F → E. D6 (koszt sprite'ów) później;
A4/A5 — gdy autor je wybierze.
