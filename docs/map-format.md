# Format mapy `maps/*.txt`

Czytany przez `read_map_from_file` (`src/map.c`), zapisywany przez edytor (`editor/tpmap/txt_format.py`).
Tokeny rozdzielone białymi znakami; poza linią sprite'a (pole `z`) podział na linie nie ma znaczenia.

```
w h tile_size                        rozmiar w kafelkach, rozmiar kafelka w pikselach świata
wall floor ceiling                   domyślne tekstury (pliki w maps/textures/)
count name...                        tabela tekstur mapy (0..MAX_TEXTURES nazw)
type:texture:height  × w, h wierszy  kafelki
exit0 exit1 exit2 exit3              ścieżka mapy (np. maps/map2.txt) albo NULL
sprite_count
x y type texture scale collision_r [z]   jedna linia na sprite
```

## Kafelki `type:texture:height`

| `type` | Znaczenie | Blokuje ruch | Rysowany |
|---|---|---|---|
| 0 | pusty | nie | nie |
| 1 | ściana | tak | tak |
| 2 | wyjście | nie | nie (wejście → `handle_exit`) |
| 3 | drzwi (D4, jeszcze nieobsługiwane) | nie | nie |
| 4 | niska ściana (lada, stół) | tak | tak |

- `texture`: 0 = domyślna tekstura ścian mapy (`wall`), k ≥ 1 = pozycja k−1 tabeli tekstur.
  Liczba spoza `0..count` → błąd wczytania. Ma znaczenie tylko dla kafelków rysowanych (1, 4).
- `height` (w wysokościach ściany, oczy kamery na 0.5):
  - `≥ 1` — pełna ściana, promień się na niej kończy;
  - `< 1` — niska ściana: promień idzie dalej, widać, co za nią; przednia ściana ma całą
    teksturę ściśniętą do wysokości (tekstury lad rysuje się w docelowych proporcjach);
  - `< 0.5` — dodatkowo widać wierzch (tekstura kafelka, 1 kopia na kafelek; TODO: osobna
    tekstura wierzchu).
  - Kolizja zależy tylko od typu (1 i 4 blokują), nie od wysokości.

## Wyjścia

Cztery pozycje; indeks to strona, po której gracz pojawia się w następnej mapie
(0 = N, 1 = S, 2 = W, 3 = E). Znany błąd A5: `handle_exit` zawsze używa pierwszego
nie-`NULL` wyjścia (kolejność 2, 3, 1, 0), niezależnie od kafelka.

## Sprite'y `x y type texture scale collision_r [z]`

- `x y` — pozycja w kafelkach (2.5 = środek kafelka 2).
- `type` — 0 statyczny, 1 interaktywny, 2 drzwi, 3 NPC (`SpriteType` w `include/sprite.h`).
- `texture` — indeks w tabeli tekstur mapy (od 0, inaczej niż kafelki!).
- `scale` — wysokość w wysokościach ściany (1.0 = ściana / człowiek, 0.3 = kubek).
  Szerokość z proporcji tekstury; piksele z alfą 0 są przezroczyste.
- `collision_r` — promień w kafelkach na przyszłą interakcję/kolizję (gra jeszcze go nie używa).
- `z` (opcjonalne, domyślnie 0) — wysokość podstawy w wysokościach ściany. Ciasto na ladzie
  0.5 → `z = 0.5`. Edytor zapisuje `z` tylko, gdy ≠ 0.
- Przy równej głębokości (sprite'y w tym samym punkcie) niższy `z` rysowany jest pierwszy —
  ciasto na stole-sprite'cie leży na wierzchu.
- Sprite'y są zasłaniane przez pełne ściany i przez bliższe niskie ściany.

## Przykład: lada z ciastem

```
4 3 100
drapes.jpeg floor.png floor.png
2 diner_counter.png sprite_pie.png
1:0:1.0 1:0:1.0 1:0:1.0 1:0:1.0
1:0:1.0 4:1:0.5 0:0:0.0 1:0:1.0
1:0:1.0 1:0:1.0 1:0:1.0 1:0:1.0
NULL NULL NULL NULL
1
1.5 1.5 1 1 0.25 0.0 0.5
```

Lada (1,1) ma teksturę `diner_counter.png` (pozycja 0 tabeli → numer kafelka 1) i wysokość 0.5;
ciasto (pozycja 1 tabeli) stoi na jej wierzchu (`z = 0.5`).
