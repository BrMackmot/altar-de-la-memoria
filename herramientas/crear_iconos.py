"""
Crea los íconos de la aplicación (icono-192.png e icono-512.png) con la paleta del altar:
fondo teal, arco dorado de nicho y una vela. Se usan cuando alguien "instala" el sitio en
su teléfono desde el navegador.

Uso, desde la raíz del repositorio:
    python herramientas/crear_iconos.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
TEAL, ORO, MARFIL, TERRA = (15, 76, 74), (215, 155, 29), (243, 234, 215), (184, 71, 42)


def dibujar(lado):
    s = lado / 512
    im = Image.new("RGB", (lado, lado), TEAL)
    d = ImageDraw.Draw(im)
    # franja de zigzag abajo
    paso = int(48 * s)
    for i, x in enumerate(range(0, lado, paso)):
        d.polygon([(x, lado), (x + paso // 2, lado - int(44 * s)), (x + paso, lado)], fill=ORO if i % 2 == 0 else TERRA)
    # arco del nicho
    cx, r = lado // 2, int(150 * s)
    base = int(410 * s)
    d.ellipse([cx - r - 14 * s, base - 2 * r - 90 * s, cx + r + 14 * s, base - 90 * s + 14 * s], fill=ORO)
    d.rectangle([cx - r - 14 * s, base - r - 90 * s, cx + r + 14 * s, base], fill=ORO)
    d.ellipse([cx - r, base - 2 * r - 76 * s, cx + r, base - 76 * s], fill=(10, 50, 49))
    d.rectangle([cx - r, base - r - 76 * s, cx + r, base], fill=(10, 50, 49))
    # vela y llama
    d.rectangle([cx - 16 * s, base - 150 * s, cx + 16 * s, base - 20 * s], fill=MARFIL)
    d.ellipse([cx - 14 * s, base - 205 * s, cx + 14 * s, base - 150 * s], fill=(255, 217, 120))
    return im


if __name__ == "__main__":
    for lado in (192, 512):
        destino = RAIZ / f"icono-{lado}.png"
        dibujar(lado).save(destino)
        print(f"Creado {destino.name}")
