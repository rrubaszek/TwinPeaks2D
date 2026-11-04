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
| raycaster           pixel, 800× cast_ray   |
| put_pixel (łącznie) ań, niezinlinowana   |


| section              |  avg ms |  max ms | % frame |
| clear_framebuffer    |   0.341 |   0.786 |    2.2% |
| render_floor_ceiling |  11.723 |  17.888 |   75.5% |
| raycaster            |   2.694 |   6.921 |   17.4% |
| upload + present     |   0.726 |   1.812 |    4.7% |
| frame (no delay)     |  15.517 |  21.163 |  100.0% |

| section              |  avg ms |  max ms | % frame |
| clear_framebuffer    |   0.410 |   0.910 |    2.5% |
| render_floor_ceiling |  11.519 |  15.637 |   71.3% |
| raycaster            |   3.493 |   6.929 |   21.6% |
| upload + present     |   0.690 |   1.361 |    4.3% |
| frame (no delay)     |  16.146 |  21.897 |  100.0% |