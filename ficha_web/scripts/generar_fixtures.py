"""Genera las fotos de ejemplo del modo mock (patrones de color con texto, no fotos reales).

Uso: python scripts/generar_fixtures.py
Deja fixtures/fotos/1001/{general,acceso_1,acceso_2,1,2}.jpg (la Fig. 3 falta a propósito).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESTINO = Path(__file__).resolve().parent.parent / "fixtures" / "fotos" / "1001"
FOTOS = {
    "general": (70, 110, 150),
    "acceso_1": (150, 110, 70),
    "acceso_2": (110, 70, 150),
    "1": (60, 140, 90),
    "2": (160, 80, 80),
}


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    fuente = ImageFont.load_default(size=90)
    for nombre, color in FOTOS.items():
        ancho, alto = (1200, 900) if not nombre.isdigit() else (1920, 1080)   # figuras 16:9
        img = Image.new("RGB", (ancho, alto), color)
        d = ImageDraw.Draw(img)
        for k in range(-alto, ancho, 60):   # franjas diagonales
            d.line([(k, 0), (k + alto, alto)], fill=tuple(min(255, c + 25) for c in color), width=18)
        d.text((ancho // 2, alto // 2), (nombre if nombre.isdigit() is False else f"Fig {nombre}").replace("_", " "), fill="white", font=fuente, anchor="mm")
        img.save(DESTINO / f"{nombre}.jpg", quality=80)
    print(f"{len(FOTOS)} imágenes en {DESTINO}")


if __name__ == "__main__":
    main()
