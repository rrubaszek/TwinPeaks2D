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
- **Budżet wydajności:** `?` — ustalany po pomiarze bazowym B0 (800×600).
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

### B0 `DONE` (budżet B0.5 — do decyzji) Pomiar bazowy (warunek wstępny dla B1–B4)
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
  - D5.1 Przezroczystość sprite'ów (alfa z PNG zamiast czarnego tła BMP) — `DONE`; tekstury drzew — `TODO`.
  - D5.2 Wiele drzew: odrzucanie poza polem widzenia i za odległością, rysowanie od przodu do tyłu
    z buforem pokrycia (bez overdraw — ta sama idea co odłożone B1.4).
  - D5.3 Czas w rendererze (suma `dt`) + wiatr: przesunięcie `texX` w poziomie, rosnące ku
    koronie (`amplitude * wind(t, drzewo) * (1 - v)^2`), faza per drzewo z pozycji, podmuchy
    jako suma 2–3 sinusów wędrująca przez mapę.
  - D5.4 Pomiar (profiler + callgrind, np. 200 drzew) względem budżetu klatki.
  - D5.5 Edytor: pędzel „rozsyp drzewa” (gęstość, losowa skala); opcjonalnie parametry
    wiatru per mapa.
  - Opcjonalnie: 2–4 klatki animacji liści, opadające liście, mocniejsza mgła w oddali,
    `forest.jpeg` jako ściana „skraju lasu” za sprite'ami.
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
  v2: edytor pikseli sprite'ów (na bazie `helpers/generate_sprites.py`), „On sprite below”
  (z = wierzch sprite'a pod spodem), undo, start gracza
- E5 `?` Wyświetlanie tekstu / HUD (zależne od decyzji w Wizji)

## F. Kierunek wizualny (referencja: demo BLOK — retro PS1, wnętrza lat 90.)
Cel przykładowy: wnętrze Double R Diner (szachownica na podłodze, boazeria, lada ze
stołkami, boksy przy oknach, gablota z ciastami, ciepłe lampy).
- F1 `?` Post-process „retro”: renderowanie w niższej rozdzielczości wewnętrznej +
  powiększenie bez wygładzania, redukcja liczby kolorów na kanał, dithering uporządkowany
  (Bayer). Parametry regulowane stałymi (jak w BLOK: pikselizacja, precyzja koloru).
  Kryterium: efekt włączany/wyłączany klawiszem, czas klatki w budżecie B0.5.
- F2 `?` Podłoga i sufit per kafelek (dziś jedna tekstura na mapę: `floor_tex_id`,
  `ceiling_tex_id`) — wymaga zmiany formatu mapy i edytora (E4).
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

**Bieżąca kolejność (aktualizacja 2026-11-07):** D2, F5, D7 zrobione → narzędzia sprite'ów
w edytorze (E4 v2, osobna gałąź) → F → E. D6 (koszt sprite'ów) później; A4/A5 — gdy autor je wybierze.
