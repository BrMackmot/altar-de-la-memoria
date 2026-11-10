"""
Servidor Flask del Altar de la Memoria.

Hace dos cosas:
  1. Entrega la experiencia (index.html, sw.js, libs, modelo 3D, video, audio).
  2. Recibe las memorias que la gente deja en el capítulo 5, las guarda y deja
     que un mayor de la comunidad las apruebe antes de mostrarlas.

Uso local:
    pip install -r requirements.txt
    python app.py
    (abra http://localhost:5000 ; la cámara en el teléfono exige HTTPS, ver LEEME.md)

Variables de entorno:
    ADMIN_KEY   clave para ver y aprobar aportes (obligatoria para usar /api/admin/*)
    DATOS_DIR   carpeta donde se guardan los aportes (por defecto ./datos)

Los aportes se guardan en datos/memorias.jsonl, una línea por aporte.
Nunca se publican sin aprobación y los marcados como sagrados no salen por la API pública.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

RAIZ = Path(__file__).resolve().parent
DATOS = Path(os.environ.get("DATOS_DIR", RAIZ / "datos"))
ARCHIVO = DATOS / "memorias.jsonl"
MAX_TEXTO = 280
CERROJO = threading.Lock()

# Solo estos archivos y carpetas se entregan. El resto del repositorio (datos, código) no sale.
ARCHIVOS_PUBLICOS = {"index.html", "sw.js", "manifest.webmanifest", "icono-192.png", "icono-512.png", "contenido.json"}
CARPETAS_PUBLICAS = {"libs", "audio", "video", "modelo", "fotos", "musica"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # un aporte de texto no necesita más


# ---------- almacenamiento ----------
def _leer():
    if not ARCHIVO.exists():
        return []
    with ARCHIVO.open(encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def _escribir(registros):
    DATOS.mkdir(parents=True, exist_ok=True)
    tmp = ARCHIVO.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(ARCHIVO)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _admin_ok():
    clave = os.environ.get("ADMIN_KEY", "")
    enviada = request.headers.get("X-Admin-Key", "")
    return bool(clave) and hmac.compare_digest(clave, enviada)


def _publico(r):
    """Lo único que sale a la vista pública: nada de tokens ni de fechas exactas."""
    return {
        "id": r["id"],
        "texto": r["texto"],
        "nombre": r.get("nombre") if r["aparece"] == "con" else None,
    }


# ---------- páginas ----------
@app.get("/")
def inicio():
    return send_from_directory(RAIZ, "index.html")


@app.get("/<path:ruta>")
def estaticos(ruta):
    # Se resuelve la ruta real y se exige que quede dentro de una carpeta pública
    # (así "libs/../app.py" no sirve para sacar el código del servidor).
    real = (RAIZ / ruta).resolve()
    if real.is_file():
        rel = real.relative_to(RAIZ) if RAIZ in real.parents else None
        if rel is not None and (
            rel.as_posix() in ARCHIVOS_PUBLICOS
            or (len(rel.parts) >= 2 and rel.parts[0] in CARPETAS_PUBLICAS)
        ):
            return send_from_directory(RAIZ, rel.as_posix(), conditional=True)
    abort(404)


# ---------- API ----------
@app.post("/api/memorias")
def crear():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify(error="Formato inválido"), 400

    texto = str(d.get("texto", "")).strip()
    if not texto:
        return jsonify(error="Falta el texto"), 400
    if len(texto) > MAX_TEXTO:
        return jsonify(error=f"El texto supera {MAX_TEXTO} caracteres"), 400

    aparece = d.get("aparece")
    if aparece not in ("con", "sin"):
        return jsonify(error="Indique si quiere aparecer con nombre"), 400

    p = d.get("permisos") or {}
    permisos = {
        "experiencia": bool(p.get("experiencia")),
        "archivo": bool(p.get("archivo")),
        "sagrado": bool(p.get("sagrado")),
    }
    if permisos["sagrado"]:
        # Lo sagrado nunca se muestra ni se archiva fuera de CAEDI
        permisos["experiencia"] = permisos["archivo"] = False
    elif not (permisos["experiencia"] or permisos["archivo"]):
        return jsonify(error="Elija al menos un uso o marque sagrado"), 400

    token = secrets.token_urlsafe(16)
    registro = {
        "id": secrets.token_hex(6),
        "token_hash": _hash(token),
        "texto": texto,
        "aparece": aparece,
        "permisos": permisos,
        "recibido": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aprobado": False,  # lo cambia un mayor, nunca el servidor solo
    }
    with CERROJO:
        registros = _leer()
        registros.append(registro)
        _escribir(registros)
    # El token solo se entrega esta vez: sirve para que la persona retire su aporte
    return jsonify(id=registro["id"], token=token), 201


@app.delete("/api/memorias/<id_>")
def retirar(id_):
    token = request.headers.get("X-Token", "")
    with CERROJO:
        registros = _leer()
        for r in registros:
            if r["id"] == id_:
                if not token or not hmac.compare_digest(r["token_hash"], _hash(token)):
                    return jsonify(error="Token inválido"), 403
                registros.remove(r)
                _escribir(registros)
                return jsonify(ok=True)
    return jsonify(error="No existe"), 404


@app.get("/api/memorias")
def publicas():
    """Solo aportes aprobados, autorizados para la experiencia y no sagrados."""
    lista = [
        _publico(r) for r in _leer()
        if r["aprobado"] and r["permisos"]["experiencia"] and not r["permisos"]["sagrado"]
    ]
    return jsonify(lista)


@app.get("/api/admin/memorias")
def admin_lista():
    if not _admin_ok():
        return jsonify(error="No autorizado"), 401
    return jsonify([{k: v for k, v in r.items() if k != "token_hash"} for r in _leer()])


@app.post("/api/admin/memorias/<id_>/aprobar")
def admin_aprobar(id_):
    if not _admin_ok():
        return jsonify(error="No autorizado"), 401
    with CERROJO:
        registros = _leer()
        for r in registros:
            if r["id"] == id_:
                if r["permisos"]["sagrado"]:
                    return jsonify(error="Es contenido sagrado: no se aprueba para publicar"), 409
                r["aprobado"] = bool((request.get_json(silent=True) or {}).get("aprobado", True))
                _escribir(registros)
                return jsonify(ok=True, aprobado=r["aprobado"])
    return jsonify(error="No existe"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
