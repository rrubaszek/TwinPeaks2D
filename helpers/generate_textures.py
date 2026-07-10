from PIL import Image, ImageDraw
import os

# Konfiguracja tekstur (nazwa pliku, kolor tła, kolor wzoru)
textures = {
    "diner_wall_wood.bmp": ((101, 67, 33), (139, 90, 43)),       # Brązowe panele
    "diner_wall_red.bmp": ((139, 0, 0), (255, 0, 0)),            # Czerwona tapeta
    "diner_floor.bmp": ((0, 100, 0), (0, 150, 0)),               # Zielone kafelki
    "diner_counter.bmp": ((180, 180, 180), (255, 0, 0)),         # Lada z wisienkami
    "diner_door.bmp": ((120, 80, 40), (80, 50, 20)),             # Drewniane drzwi
    "diner_window.bmp": ((20, 20, 40), (100, 100, 150)),         # Ciemne okno
    "sprite_coffee.bmp": ((0, 0, 0), (200, 200, 200)),           # Dzbanek (tło czarne dla przezroczystości)
    "sprite_pie.bmp": ((0, 0, 0), (200, 50, 50)),                # Cherry pie
    "kitchen_wall.bmp": ((200, 200, 200), (255, 255, 255)),      # Białe kafelki
    "kitchen_floor.bmp": ((50, 50, 50), (30, 30, 30))            # Ciemna podłoga
}

output_dir = "../maps/textures"
os.makedirs(output_dir, exist_ok=True)

for name, (bg_color, fg_color) in textures.items():
    # Tworzenie obrazu 64x64
    img = Image.new('RGB', (64, 64), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Rysowanie prostej szachownicy/ramki żeby tekstura nie była płaska
    for x in range(0, 64, 16):
        for y in range(0, 64, 16):
            if (x // 16 + y // 16) % 2 == 0:
                draw.rectangle([x, y, x+15, y+15], fill=fg_color)
                
    # Zapis do prostego formatu BMP, który łatwo wczytać w C
    img.save(os.path.join(output_dir, name))

print(f"Wygenerowano {len(textures)} tekstur w folderze '{output_dir}'.")