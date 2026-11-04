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

## B. Wydajność obliczeniowa

### B0 `DONE` (budżet B0.5 — do decyzji) Pomiar bazowy (warunek wstępny dla B1–B4)
Instrumentacja czasu klatki i sekcji (`/perf-measure`), zapisany wynik bazowy.
Kryterium: tabela czasów w `docs/perf-log.md` dla aktualnego commita.

### B1 `WIP` (B1.1–B1.3 DONE: −64% czasu; B1.4 overdraw — plan gotowy, do decyzji) Koszt podłogi i sufitu
`render_floor_ceiling` przetwarza każdy piksel ekranu (480 000/klatkę) z kilkoma
wywołaniami funkcji, operacjami zmiennoprzecinkowymi i modulo na piksel; część tych
pikseli jest potem nadpisywana przez ściany (overdraw).
Kryterium: ustalony procentowy zysk względem B0 (do określenia przez autora).

### B2 `WIP` (B2.1–B2.2 DONE: −29% czasu; dalej: koszt zapisu kolumnami — do pomiaru) Koszt rysowania ścian
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

### C2 `?` (przesunięte za D1 — `render_sprites` jest obecnie wyłączone) Alokacje w każdej klatce
`render_sprites` alokuje tablicę odległości (`malloc`) i VLA w każdej klatce.
Kryterium: zero alokacji na stercie w pętli klatki.

## D. Funkcjonalność (z TODO w kodzie)
- D1 `?` Sprite'y renderowane do framebuffera (obecnie wyłączone, rysowały przez SDL_Renderer)
- D2 `?` Tekstury per kafelek (`texture_id` w `Tile` jest wczytywane, ale nieużywane)
- D3 `?` Zależne stałe w `constants.h` (TODO autora)
- D4 `?` Drzwi, przedmioty interaktywne, NPC (typy już zdefiniowane w `sprite.h`)

## E. Systemy gry (z wizji)
- E1 `?` Akcja „użyj/zbadaj” na obiekt w centrum ekranu (wymaga D1)
- E2 `?` Ekwipunek
- E3 `?` Stan świata trwały między mapami (dziś `handle_exit` ładuje mapę od zera)
- E4 `?` Edytor map (format `maps/*.txt`)
- E5 `?` Wyświetlanie tekstu / HUD (zależne od decyzji w Wizji)

---

## Kolejność
Rytm: bloki tematyczne — kończymy blok, zanim zaczniemy następny.
1. **A — fundament:** A1 (realny zapis poza tablicą po ~5 przejściach) → A2 → A3
2. **B0 — pomiar bazowy** + ustalenie budżetu wydajności w Wizji
3. **B + C — wydajność i pamięć:** B3 → B1 → B2 → B4 → C1 (C2 razem z D1)
   (B3 najpierw: ruch zależny od czasu, zanim optymalizacje zmienią czas klatki)
4. **D — silnik pod grę:** D3 → D2 → D1 (+ C2) → D4
5. **E — systemy gry:** E1 → E2 → E3 → E4 (E5 po decyzji o tekście)
