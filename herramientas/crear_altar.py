"""
Construye el altar en 3D con código y lo guarda como modelo/altar.glb.

Un archivo .glb es el formato estándar de modelos 3D para la web. Aquí se arma pieza por
pieza con la biblioteca trimesh: base de madera, tela tejida, panel con nicho, vela y tres
soportes (el río, el canto, una persona). Las medidas están en metros: el altar mide 60 cm
de ancho, así que en realidad aumentada se ve a tamaño real sobre una mesa.

Si quiere cambiar colores, medidas o piezas, edite este archivo y vuelva a ejecutarlo.

Uso, desde la raíz del repositorio:
    python herramientas/crear_altar.py

Requisitos (una sola vez):
    pip install trimesh numpy pillow
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
from trimesh import transformations as T
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "modelo" / "altar.glb"
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # cámbiela si usa Windows o Mac

# Paleta del afiche
TEAL = (15, 76, 74)
ORO = (215, 155, 29)
TERRA = (184, 71, 42)
MARFIL = (243, 234, 215)
TINTA = (27, 37, 35)
MADERA = (92, 58, 36)


# ---------- texturas (se dibujan con Pillow) ----------
def franja_zigzag(d, x0, x1, y, alto, paso, colores):
    """Dibuja una franja de triángulos alternados, motivo de tejido."""
    for i, x in enumerate(range(x0, x1, paso)):
        c = colores[i % len(colores)]
        d.polygon([(x, y + alto), (x + paso // 2, y), (x + paso, y + alto)], fill=c)


def textura_panel():
    ancho, alto = 1200, 900
    im = Image.new("RGB", (ancho, alto), TEAL)
    d = ImageDraw.Draw(im)
    # Marco de zigzag arriba y abajo
    for y in (14, alto - 74):
        d.rectangle([0, y, ancho, y + 60], fill=TEAL)
        franja_zigzag(d, 0, ancho, y, 60, 60, [ORO, TERRA])
    # Campo marfil
    d.rounded_rectangle([60, 110, ancho - 60, alto - 120], radius=18, fill=MARFIL)
    # Título
    f1 = ImageFont.truetype(FUENTE, 66)
    f2 = ImageFont.truetype(FUENTE, 30)
    d.text((ancho // 2, 165), "ALTAR DE LA MEMORIA", font=f1, fill=TINTA, anchor="mm")
    d.text((ancho // 2, 225), "Memoria y fe afrocolombiana · CAEDI, Bogotá", font=f2, fill=TEAL, anchor="mm")
    # Nicho: arco pintado con halo de luz
    cx, base = ancho // 2, alto - 135
    r = 190
    d.ellipse([cx - r - 18, base - 2 * r - 120, cx + r + 18, base - 120 + 18], fill=ORO)
    d.rectangle([cx - r - 18, base - r - 120, cx + r + 18, base], fill=ORO)
    d.ellipse([cx - r, base - 2 * r - 102, cx + r, base - 102], fill=TEAL)
    d.rectangle([cx - r, base - r - 102, cx + r, base], fill=TEAL)
    d.ellipse([cx - 120, base - 330, cx + 120, base - 90], fill=(60, 120, 112))
    return im


def textura_tela():
    ancho, alto = 1200, 720
    im = Image.new("RGB", (ancho, alto), MARFIL)
    d = ImageDraw.Draw(im)
    for y, cols in ((0, [TEAL, ORO]), (alto - 60, [ORO, TERRA])):
        franja_zigzag(d, 0, ancho, y, 60, 60, cols)
    # Rombos centrales
    for fila, y in enumerate(range(110, alto - 110, 90)):
        for x in range(60 + (45 if fila % 2 else 0), ancho - 60, 90):
            d.polygon([(x, y - 30), (x + 30, y), (x, y + 30), (x - 30, y)], fill=(228, 214, 186))
    return im


# ---------- piezas ----------
def lineal(c):
    """glTF espera los colores planos en espacio lineal; los de la paleta están en sRGB."""
    return int(round(255 * (c / 255) ** 2.2))


def mat(color, rugosidad=0.7, metal=0.0, emisivo=None, textura=None):
    # trimesh recibe el color base como enteros de 0 a 255
    return PBRMaterial(
        baseColorFactor=[*(lineal(c) for c in color), 255] if textura is None else [255, 255, 255, 255],
        baseColorTexture=textura,
        roughnessFactor=rugosidad,
        metallicFactor=metal,
        emissiveFactor=[lineal(c) for c in emisivo] if emisivo else None,
    )


def con_material(malla, material):
    malla.visual = TextureVisuals(material=material, uv=getattr(malla.visual, "uv", None))
    return malla


def caja(ext, pos, material):
    m = trimesh.creation.box(extents=ext, transform=T.translation_matrix(pos))
    return con_material(m, material)


def cilindro(radio, alto, pos, material, secciones=48):
    """Cilindro vertical (eje Y) con la base en pos."""
    giro = T.rotation_matrix(-math.pi / 2, [1, 0, 0])
    m = trimesh.creation.cylinder(radius=radio, height=alto, sections=secciones)
    m.apply_transform(giro)
    m.apply_translation([pos[0], pos[1] + alto / 2, pos[2]])
    return con_material(m, material)


def cono(radio, alto, pos, material, secciones=48):
    giro = T.rotation_matrix(-math.pi / 2, [1, 0, 0])
    m = trimesh.creation.cone(radius=radio, height=alto, sections=secciones)
    m.apply_transform(giro)
    m.apply_translation(pos)
    return con_material(m, material)


def esfera(radio, pos, material, escala=(1, 1, 1)):
    m = trimesh.creation.icosphere(subdivisions=3, radius=radio)
    m.apply_transform(np.diag([*escala, 1]))
    m.apply_translation(pos)
    return con_material(m, material)


def cara_con_textura(ancho, alto, centro, imagen):
    """Plano vertical mirando a +Z con una imagen pegada."""
    w, h = ancho / 2, alto / 2
    cx, cy, cz = centro
    v = np.array([[cx - w, cy - h, cz], [cx + w, cy - h, cz], [cx + w, cy + h, cz], [cx - w, cy + h, cz]])
    uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    m = trimesh.Trimesh(vertices=v, faces=[[0, 1, 2], [0, 2, 3]], process=False)
    m.visual = TextureVisuals(uv=uv, material=mat(MARFIL, 0.9, textura=imagen))
    return m


def cara_horizontal(ancho, fondo, centro, imagen):
    """Plano horizontal (tela) mirando hacia arriba."""
    w, d = ancho / 2, fondo / 2
    cx, cy, cz = centro
    v = np.array([[cx - w, cy, cz + d], [cx + w, cy, cz + d], [cx + w, cy, cz - d], [cx - w, cy, cz - d]])
    uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    m = trimesh.Trimesh(vertices=v, faces=[[0, 1, 2], [0, 2, 3]], process=False)
    m.visual = TextureVisuals(uv=uv, material=mat(MARFIL, 0.95, textura=imagen))
    return m


# Posiciones de las tres memorias. Las usa index.html para los puntos de interés y la cámara.
PUESTOS = {"rio": (-0.20, 0.0, 0.10), "canto": (0.0, 0.0, 0.11), "persona": (0.20, 0.0, 0.10)}


def construir():
    escena = trimesh.Scene()
    Y_TELA = 0.045  # altura de la tela sobre el suelo

    # Base de madera y tela tejida
    escena.add_geometry(caja([0.62, 0.04, 0.36], [0, 0.02, 0], mat(MADERA, 0.8)), node_name="base")
    escena.add_geometry(cara_horizontal(0.60, 0.34, [0, Y_TELA, 0], textura_tela()), node_name="tela")

    # Panel trasero (tabla de madera + cara pintada)
    escena.add_geometry(caja([0.62, 0.47, 0.025], [0, 0.04 + 0.235, -0.165], mat(MADERA, 0.8)), node_name="panel_madera")
    escena.add_geometry(cara_con_textura(0.60, 0.45, [0, 0.04 + 0.235, -0.1515], textura_panel()), node_name="panel_cara")

    # Vela en el nicho. La llama brilla (emisiva) para que se vea encendida.
    x_nicho, z_nicho = 0.0, -0.10
    escena.add_geometry(cilindro(0.016, 0.085, [x_nicho, Y_TELA, z_nicho], mat(MARFIL, 0.6)), node_name="vela")
    escena.add_geometry(
        esfera(0.011, [x_nicho, Y_TELA + 0.085 + 0.018, z_nicho], mat((255, 217, 120), 0.3, emisivo=(255, 190, 64)), escala=(1, 1.7, 1)),
        node_name="llama",
    )
    escena.add_geometry(cilindro(0.032, 0.008, [x_nicho, Y_TELA, z_nicho], mat(ORO, 0.35, 0.8)), node_name="plato_vela")

    # Soportes de las tres memorias
    # El río: disco teal con tres franjas que imitan olas
    x, _, z = PUESTOS["rio"]
    escena.add_geometry(cilindro(0.058, 0.014, [x, Y_TELA, z], mat(ORO, 0.4, 0.7)), node_name="rio_base")
    escena.add_geometry(cilindro(0.050, 0.010, [x, Y_TELA + 0.014, z], mat(TEAL, 0.5)), node_name="rio_disco")
    for i, dz in enumerate((-0.022, 0.0, 0.022)):
        escena.add_geometry(caja([0.058, 0.006, 0.008], [x, Y_TELA + 0.027, z + dz], mat(MARFIL, 0.5)), node_name=f"rio_ola{i}")

    # El canto: tambor
    x, _, z = PUESTOS["canto"]
    escena.add_geometry(cilindro(0.058, 0.014, [x, Y_TELA, z], mat(ORO, 0.4, 0.7)), node_name="canto_base")
    escena.add_geometry(cilindro(0.036, 0.07, [x, Y_TELA + 0.014, z], mat(TERRA, 0.65)), node_name="canto_tambor")
    escena.add_geometry(cilindro(0.038, 0.006, [x, Y_TELA + 0.084, z], mat(MARFIL, 0.8)), node_name="canto_parche")
    escena.add_geometry(cilindro(0.038, 0.006, [x, Y_TELA + 0.040, z], mat(ORO, 0.4, 0.6)), node_name="canto_aro")

    # Una persona: figura sencilla (cuerpo y cabeza)
    x, _, z = PUESTOS["persona"]
    escena.add_geometry(cilindro(0.058, 0.014, [x, Y_TELA, z], mat(ORO, 0.4, 0.7)), node_name="persona_base")
    escena.add_geometry(cono(0.034, 0.075, [x, Y_TELA + 0.014, z], mat(TEAL, 0.6)), node_name="persona_cuerpo")
    escena.add_geometry(esfera(0.020, [x, Y_TELA + 0.014 + 0.075 + 0.012, z], mat(MARFIL, 0.6)), node_name="persona_cabeza")

    return escena


def principal():
    SALIDA.parent.mkdir(exist_ok=True)
    escena = construir()
    SALIDA.write_bytes(escena.export(file_type="glb"))
    caja_ = escena.bounds
    ancho, alto, fondo = (caja_[1] - caja_[0]) * 100
    print(f"Altar creado: {SALIDA} ({SALIDA.stat().st_size / 1024:.0f} KB)")
    print(f"Medidas reales: {ancho:.0f} cm de ancho, {alto:.0f} cm de alto, {fondo:.0f} cm de fondo")
    print(f"Piezas: {len(escena.geometry)}")


if __name__ == "__main__":
    principal()
