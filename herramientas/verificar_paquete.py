"""
Revisa que el repositorio esté completo ANTES de subirlo a GitHub y de probarlo en el teléfono.

En la Sección 1 la cámara no arrancó porque faltaban archivos en el repositorio
(error RA_07). Este script evita ese problema: lee contenido.json y comprueba que
cada video, foto, audio y música que se menciona exista de verdad.

Uso, desde la carpeta raíz del repositorio:
    python herramientas/verificar_paquete.py
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OBLIGATORIOS = ["index.html", "contenido.json", "sw.js", "manifest.webmanifest", "icono-192.png",
                "icono-512.png", "libs/model-viewer.min.js", "modelo/altar.glb", ".nojekyll"]
LIMITE_MB = 8


def tam(ruta):
    return f"{ruta.stat().st_size / 1024 / 1024:.1f} MB"


def main():
    faltan, avisos = 0, 0
    print("Archivos del sitio")
    for nombre in OBLIGATORIOS:
        ruta = RAIZ / nombre
        if ruta.exists():
            print(f"  [ok]    {nombre}")
        else:
            print(f"  [FALTA] {nombre}")
            faltan += 1

    contenido = json.loads((RAIZ / "contenido.json").read_text(encoding="utf-8"))
    sw = (RAIZ / "sw.js").read_text(encoding="utf-8")
    print("\nMemorias (según contenido.json)")
    for clave, m in contenido["memorias"].items():
        partes = []
        for campo in ("video", "audio"):
            if m.get(campo):
                ruta = RAIZ / m[campo]
                if not ruta.exists():
                    print(f"  [FALTA] {clave}: {m[campo]}")
                    faltan += 1
                else:
                    partes.append(f"{campo} {tam(ruta)}")
                    if ruta.stat().st_size > LIMITE_MB * 1024 * 1024:
                        print(f"  [AVISO] {m[campo]} pesa más de {LIMITE_MB} MB")
                        avisos += 1
        for f in m.get("fotos", []):
            if not (RAIZ / f["archivo"]).exists():
                print(f"  [FALTA] {clave}: {f['archivo']}")
                faltan += 1
            if f.get("alt", "").startswith("["):
                avisos += 1
        if m.get("fotos"):
            partes.append(f"{len(m['fotos'])} fotos")
        if not partes:
            print(f"  [FALTA] {clave}: no tiene video, audio ni fotos")
            faltan += 1
        else:
            print(f"  [ok]    {clave}: " + ", ".join(partes))
        for campo in ("lugar", "quien", "texto"):
            if str(m.get(campo, "")).startswith("["):
                print(f"  [AVISO] {clave}: falta completar «{campo}» en contenido.json")
                avisos += 1

    musica = contenido.get("musica") or {}
    if musica.get("archivo"):
        ruta = RAIZ / musica["archivo"]
        print(f"\nMúsica: {'[ok] ' + tam(ruta) if ruta.exists() else '[FALTA]'} {musica['archivo']}")
        faltan += 0 if ruta.exists() else 1
        if "[" in musica.get("credito", ""):
            print("  [AVISO] complete el crédito y la licencia de la música en contenido.json")
            avisos += 1

    print("\nModo sin internet (sw.js)")
    listados = re.findall(r"'([^']+)'", sw.split("const ARCHIVOS", 1)[1].split("];", 1)[0])
    perdidos = [a for a in listados if a != "./" and not (RAIZ / a).exists()]
    print(f"  {len(listados)} archivos listados; {len(perdidos)} no existen" + (f": {perdidos}" if perdidos else ""))
    avisos += len(perdidos)

    print()
    if faltan:
        print(f"RESULTADO: faltan {faltan} archivos. No lo suba ni lo pruebe en el teléfono todavía.")
        sys.exit(1)
    print(f"RESULTADO: el paquete está completo ({avisos} avisos para revisar).")


if __name__ == "__main__":
    main()
