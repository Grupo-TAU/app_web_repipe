"""Genera logo-repipe-claro.png: el logo con las partes oscuras (azul tinta) en crema,
para que se lea sobre el banner verde oscuro del encabezado. El original no se modifica.

Uso: python scripts/generar_logo_claro.py
"""
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
CREMA = (255, 253, 222)
LUZ_OSCURO, LUZ_CLARO = 90, 50     # luminancia (0-255): por debajo del 2.º valor, todo crema; por encima del 1.º, intacto


def main():
    img = Image.open(RAIZ / "logo-repipe.png").convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            luz = 0.299 * r + 0.587 * g + 0.114 * b
            t = min(1.0, max(0.0, (LUZ_OSCURO - luz) / (LUZ_OSCURO - LUZ_CLARO)))   # 1 = muy oscuro
            px[x, y] = tuple(round(c + (m - c) * t) for c, m in zip((r, g, b), CREMA)) + (a,)
    img.save(RAIZ / "logo-repipe-claro.png")
    print("logo-repipe-claro.png generado")


if __name__ == "__main__":
    main()
