"""
Prepara sus videos, fotos, audios y música para publicarlos en la web.

Ponga los archivos originales (tal como salen del teléfono o la cámara) en estas carpetas:

    entrada/rio/       videos, fotos o audio de la memoria «El río»
    entrada/canto/     ... de «El canto»
    entrada/persona/   ... de «Una persona»
    entrada/musica/    una canción para la música de fondo (mp3, m4a o wav)
    entrada/pendientes_aval/  contenido sagrado o litúrgico que espera aprobación (no se publica)

y ejecute, desde la raíz del repositorio:

    python herramientas/preparar_medios.py

Qué hace, para cada memoria:
  - Video: recorta los segundos indicados en contenido.json ("recorte"), lo reduce a 1280 px
    como máximo, normaliza el volumen, suaviza el inicio y el final y lo deja en video/<memoria>.mp4.
    También saca una imagen de portada (video/<memoria>-portada.jpg).
  - Fotos: las endereza, las reduce a 1600 px y QUITA LOS DATOS OCULTOS (ubicación GPS, modelo
    de cámara, fecha). Quedan en fotos/<memoria>-1.jpg, -2.jpg...
  - Audio (si la memoria no tiene video): lo deja en audio/<memoria>.mp3.
  - Música: la deja en musica/fondo.mp3, más suave que las voces.
Al final actualiza contenido.json y sw.js (para que los teléfonos descarguen la versión nueva)
y muestra cuánto dura el recorrido completo.

Los archivos originales de entrada/ NO se suben a GitHub (están en .gitignore).

Requisitos: ffmpeg instalado (https://ffmpeg.org) y  pip install pillow
Fotos HEIC de iPhone: pip install pillow-heif  (o expórtelas como JPG).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:  # fotos HEIC del iPhone, opcional
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "entrada"
CONTENIDO = RAIZ / "contenido.json"
SW = RAIZ / "sw.js"

EXT_VIDEO = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".3gp", ".mts"}
EXT_FOTO = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
EXT_AUDIO = {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac", ".opus"}

LIMITE_MB = 8          # tamaño máximo recomendado por video
LADO_FOTO = 1600       # píxeles del lado más largo de cada foto
MUSICA_MAX_S = 240     # la música de fondo se corta a 4 minutos
PLACEHOLDER_ALT = "[Describa la foto en una frase: quién o qué se ve, sin nombres si no hay permiso]"


# ---------- utilidades ----------
def correr(orden):
    r = subprocess.run(orden, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg falló:\n" + r.stderr[-1500:])
    return r


def duracion(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(ruta)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def tiene_audio(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(ruta)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def archivos(carpeta, extensiones):
    if not carpeta.exists():
        return []
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in extensiones)


def mb(ruta):
    return ruta.stat().st_size / 1024 / 1024


def fmt(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


# ---------- video ----------
def preparar_video(origen, clave, recorte):
    inicio = float(recorte.get("inicio", 0))
    total = duracion(origen)
    dur = max(1.0, min(float(recorte.get("duracion", 45)), total - inicio))
    salida = RAIZ / "video" / f"{clave}.mp4"
    salida.parent.mkdir(exist_ok=True)
    fundido = f"fade=t=in:d=0.6,fade=t=out:st={max(0, dur - 0.8):.2f}:d=0.8"
    # Se prueba con calidad alta y, si pesa más de 8 MB, se baja la resolución por pasos.
    # El lado largo queda en 1280, 960 o 720 px: sirve para videos horizontales y verticales.
    for lado, crf in ((1280, 28), (1280, 32), (960, 32), (720, 34)):
        escala = f"scale='if(gte(iw,ih),min({lado},iw),-2)':'if(gte(iw,ih),-2,min({lado},ih))'"
        orden = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(inicio), "-t", f"{dur:.2f}", "-i", str(origen),
                 "-vf", f"{escala},{fundido},format=yuv420p", "-fpsmax", "30",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-movflags", "+faststart"]
        if tiene_audio(origen):
            orden += ["-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.5,afade=t=out:st={max(0, dur - 1):.2f}:d=1",
                      "-c:a", "aac", "-b:a", "96k", "-ac", "2"]
        else:
            orden += ["-an"]
        correr(orden + [str(salida)])
        if mb(salida) <= LIMITE_MB:
            break
    portada = RAIZ / "video" / f"{clave}-portada.jpg"
    correr(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(1.5, dur / 2):.2f}", "-i", str(salida),
            "-frames:v", "1", "-q:v", "4", str(portada)])
    aviso = f"  (pesa {mb(salida):.1f} MB, más de {LIMITE_MB}: acorte el recorte)" if mb(salida) > LIMITE_MB else ""
    print(f"  video   {origen.name} -> video/{clave}.mp4, segundos {fmt(inicio)}–{fmt(inicio + dur)} "
          f"de {fmt(total)}, {mb(salida):.1f} MB{aviso}")
    return salida, portada, duracion(salida)


# ---------- audio ----------
def preparar_audio(origen, destino, recorte=None, volumen="-16", maximo=None, fundido_s=1.0):
    inicio = float((recorte or {}).get("inicio", 0))
    total = duracion(origen)
    dur = total - inicio
    if recorte:
        dur = min(dur, float(recorte.get("duracion", dur)))
    if maximo:
        dur = min(dur, maximo)
    destino.parent.mkdir(exist_ok=True)
    correr(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(inicio), "-t", f"{dur:.2f}", "-i", str(origen), "-vn",
            "-af", f"loudnorm=I={volumen}:TP=-1.5:LRA=11,afade=t=in:d={fundido_s},"
                   f"afade=t=out:st={max(0, dur - fundido_s):.2f}:d={fundido_s}",
            "-c:a", "libmp3lame", "-b:a", "128k", "-ac", "2", str(destino)])
    return duracion(destino)


# ---------- fotos ----------
def preparar_fotos(lista, clave, anteriores):
    carpeta = RAIZ / "fotos"
    carpeta.mkdir(exist_ok=True)
    for vieja in carpeta.glob(f"{clave}-*.jpg"):
        vieja.unlink()
    previas = {f.get("origen"): f for f in anteriores if isinstance(f, dict)}
    resultado = []
    for i, origen in enumerate(lista, 1):
        try:
            im = Image.open(origen)
        except Exception as e:  # noqa: BLE001
            print(f"  [AVISO] no se pudo abrir {origen.name} ({e}). Si es HEIC: pip install pillow-heif")
            continue
        im = ImageOps.exif_transpose(im)          # endereza según la orientación de la cámara
        im = im.convert("RGB")
        im.thumbnail((LADO_FOTO, LADO_FOTO))
        destino = carpeta / f"{clave}-{i}.jpg"
        im.save(destino, "JPEG", quality=82, optimize=True, progressive=True)  # sin EXIF: sin GPS
        previa = previas.get(origen.name, {})
        resultado.append({
            "archivo": f"fotos/{destino.name}",
            "origen": origen.name,
            "alt": previa.get("alt", PLACEHOLDER_ALT),
            "credito": previa.get("credito", ""),
        })
        print(f"  foto    {origen.name} -> fotos/{destino.name} ({im.width}x{im.height}, sin datos GPS)")
    return resultado


# ---------- service worker ----------
def actualizar_sw(contenido):
    lista = ["./", "index.html", "contenido.json", "manifest.webmanifest", "icono-192.png", "icono-512.png",
             "libs/model-viewer.min.js", "modelo/altar.glb"]
    for m in contenido["memorias"].values():
        for campo in ("video", "poster", "audio"):
            if m.get(campo) and (RAIZ / m[campo]).exists():
                lista.append(m[campo])
        lista += [f["archivo"] for f in m.get("fotos", []) if (RAIZ / f["archivo"]).exists()]
    if contenido.get("musica", {}).get("archivo"):
        lista.append(contenido["musica"]["archivo"])
    texto = SW.read_text(encoding="utf-8")
    actual = re.search(r"const VERSION = 'altar-v(\d+)';", texto)
    nueva = int(actual.group(1)) + 1 if actual else 2
    texto = re.sub(r"const VERSION = '[^']*';", f"const VERSION = 'altar-v{nueva}';", texto)
    bloque = "const ARCHIVOS = [\n" + ",\n".join(f"  '{a}'" for a in lista) + "\n];"
    texto = re.sub(r"const ARCHIVOS = \[.*?\];", bloque, texto, flags=re.S)
    SW.write_text(texto, encoding="utf-8")
    return nueva, len(lista)


# ---------- principal ----------
def principal():
    if not shutil.which("ffmpeg"):
        raise SystemExit("Falta ffmpeg. Instálelo desde https://ffmpeg.org y vuelva a ejecutar.")
    if not ENTRADA.exists():
        for sub in ("rio", "canto", "persona", "musica"):
            (ENTRADA / sub).mkdir(parents=True, exist_ok=True)
        (ENTRADA / "pendientes_aval").mkdir(exist_ok=True)
        raise SystemExit("Creé la carpeta entrada/ con rio, canto, persona y musica. Ponga allí sus archivos y vuelva a ejecutar.")

    contenido = json.loads(CONTENIDO.read_text(encoding="utf-8"))
    duraciones = {}

    for clave, m in contenido["memorias"].items():
        carpeta = ENTRADA / clave
        print(f"\n{m.get('nombre', clave)} ({clave})")
        videos, fotos, audios = archivos(carpeta, EXT_VIDEO), archivos(carpeta, EXT_FOTO), archivos(carpeta, EXT_AUDIO)
        if not (videos or fotos or audios):
            print("  sin archivos nuevos en entrada/; se deja como está")
            continue
        recorte = m.get("recorte", {"inicio": 0, "duracion": 45})
        if videos:
            if len(videos) > 1:
                print(f"  [AVISO] hay {len(videos)} videos; se usa solo {videos[0].name}. Deje uno por memoria.")
            _, portada, d = preparar_video(videos[0], clave, recorte)
            m["video"], m["poster"] = f"video/{clave}.mp4", f"video/{portada.name}"
            duraciones[clave] = d
        else:
            m["video"], m["poster"] = "", ""
            vieja = RAIZ / "video" / f"{clave}.mp4"
            if vieja.exists():
                vieja.unlink()
                print(f"  se quitó video/{clave}.mp4 (era de ejemplo): esta memoria usará audio o fotos")
        if not audios and not (RAIZ / m.get("audio", "x")).is_file():
            m["audio"] = ""  # no hay audio: que la página no lo busque
        if audios and not videos:
            d = preparar_audio(audios[0], RAIZ / "audio" / f"{clave}.mp3", recorte)
            m["audio"] = f"audio/{clave}.mp3"
            duraciones[clave] = d
            print(f"  audio   {audios[0].name} -> audio/{clave}.mp3 ({fmt(d)})")
        m["fotos"] = preparar_fotos(fotos, clave, m.get("fotos", [])) if fotos else m.get("fotos", [])
        if clave not in duraciones and m["fotos"]:
            duraciones[clave] = max(15, 6 * len(m["fotos"]))
            print(f"  sin video ni audio: se mostrarán {len(m['fotos'])} fotos como diapositivas ({fmt(duraciones[clave])})")

    musicas = archivos(ENTRADA / "musica", EXT_AUDIO | EXT_VIDEO)
    if musicas:
        d = preparar_audio(musicas[0], RAIZ / "musica" / "fondo.mp3", volumen="-22", maximo=MUSICA_MAX_S, fundido_s=2.5)
        previa = contenido.get("musica") or {}
        contenido["musica"] = {"archivo": "musica/fondo.mp3", "volumen": previa.get("volumen", 0.3),
                               "credito": previa.get("credito", "[Autor de la música y permiso de uso]")}
        print(f"\nMúsica  {musicas[0].name} -> musica/fondo.mp3 ({fmt(d)}, suena bajo las pantallas sin video)")

    pendientes = [p for p in (ENTRADA / "pendientes_aval").glob("*") if p.is_file()] if (ENTRADA / "pendientes_aval").exists() else []
    if pendientes:
        print(f"\n{len(pendientes)} archivos esperan el aval de un mayor en entrada/pendientes_aval/ y NO se publican.")
        print("  Cuando un archivo sea aprobado, muévalo a la carpeta de su memoria y vuelva a ejecutar.")

    CONTENIDO.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    version, n = actualizar_sw(contenido)

    # Duración estimada del recorrido: 10 s + memorias + 30 s + 10 s
    for clave, m in contenido["memorias"].items():
        if clave not in duraciones:
            ruta = RAIZ / (m.get("video") or m.get("audio") or "")
            duraciones[clave] = duracion(ruta) if ruta.is_file() else max(15, 6 * len(m.get("fotos", [])))
    total = 10 + sum(duraciones.values()) + 30 + 10
    print(f"\ncontenido.json actualizado · sw.js en versión altar-v{version} ({n} archivos para modo sin internet)")
    print(f"Duración del recorrido: {fmt(total)}  (" + ", ".join(f"{k} {fmt(v)}" for k, v in duraciones.items()) + ")")
    if total > 4 * 60:
        print("  [AVISO] pasa de 4 minutos: reduzca 'duracion' en el recorte de alguna memoria.")
    pend = sum(1 for m in contenido["memorias"].values() for f in m.get("fotos", []) if f.get("alt", "").startswith("["))
    if pend:
        print(f"  Falta describir {pend} fotos: edite el campo 'alt' en contenido.json (lo leen los lectores de pantalla).")
    print("\nRecuerde: cada persona que aparece debe haber autorizado su uso (kit de validación, página 2).")


if __name__ == "__main__":
    principal()
