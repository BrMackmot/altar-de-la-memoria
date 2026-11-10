"""
Prueba automática del servidor (app.py) con el cliente de pruebas de Flask.
No abre puertos ni toca la carpeta datos/ real: usa una carpeta temporal.

Uso, desde la raíz del repositorio:
    python herramientas/probar_servidor.py
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ["DATOS_DIR"] = tempfile.mkdtemp()
os.environ["ADMIN_KEY"] = "clave-de-prueba"

import app as servidor  # noqa: E402

c = servidor.app.test_client()
fallos = 0


def comprobar(nombre, condicion):
    global fallos
    print(("  [ok]    " if condicion else "  [FALLA] ") + nombre)
    fallos += 0 if condicion else 1


buenos = {"texto": "Mi abuela cantaba al río.", "aparece": "con",
          "permisos": {"experiencia": True, "archivo": False, "sagrado": False}}

print("Archivos")
comprobar("GET / entrega index.html", c.get("/").status_code == 200)
comprobar("GET /modelo/altar.glb", c.get("/modelo/altar.glb").status_code == 200)
comprobar("GET /sw.js", c.get("/sw.js").status_code == 200)
comprobar("GET /video/rio.mp4", c.get("/video/rio.mp4").status_code == 200)
comprobar("app.py no se entrega", c.get("/app.py").status_code == 404)
comprobar("datos/ no se entrega", c.get("/datos/memorias.jsonl").status_code == 404)
comprobar("no sale de la carpeta (../)", c.get("/libs/../app.py").status_code == 404)

print("Crear aporte")
r = c.post("/api/memorias", json=buenos)
comprobar("aporte válido -> 201 con id y token", r.status_code == 201 and {"id", "token"} <= set(r.json))
idv, tok = r.json["id"], r.json["token"]
comprobar("texto vacío -> 400", c.post("/api/memorias", json={**buenos, "texto": " "}).status_code == 400)
comprobar("texto de 281 caracteres -> 400", c.post("/api/memorias", json={**buenos, "texto": "a" * 281}).status_code == 400)
comprobar("sin ningún permiso -> 400", c.post("/api/memorias", json={**buenos, "permisos": {}}).status_code == 400)
comprobar("cuerpo no JSON -> 400", c.post("/api/memorias", data="hola").status_code == 400)

print("Aprobación")
comprobar("lista pública vacía antes de aprobar", c.get("/api/memorias").json == [])
comprobar("admin sin clave -> 401", c.get("/api/admin/memorias").status_code == 401)
H = {"X-Admin-Key": "clave-de-prueba"}
lista = c.get("/api/admin/memorias", headers=H).json
comprobar("admin ve el aporte, sin token_hash", len(lista) == 1 and "token_hash" not in lista[0])
comprobar("aprobar -> 200", c.post(f"/api/admin/memorias/{idv}/aprobar", headers=H).status_code == 200)
pub = c.get("/api/memorias").json
comprobar("aparece en la lista pública tras aprobar", len(pub) == 1 and pub[0]["texto"] == buenos["texto"])
comprobar("lista pública no trae token ni permisos", set(pub[0]) == {"id", "texto", "nombre"})

print("Sagrado")
s = c.post("/api/memorias", json={**buenos, "permisos": {"experiencia": True, "archivo": True, "sagrado": True}})
comprobar("sagrado se acepta", s.status_code == 201)
ids = s.json["id"]
comprobar("sagrado no se puede aprobar (409)", c.post(f"/api/admin/memorias/{ids}/aprobar", headers=H).status_code == 409)
lista = c.get("/api/admin/memorias", headers=H).json
reg = [x for x in lista if x["id"] == ids][0]
comprobar("sagrado guardado sin permisos de uso", not reg["permisos"]["experiencia"] and not reg["permisos"]["archivo"])
comprobar("sagrado nunca sale en la lista pública", all(x["id"] != ids for x in c.get("/api/memorias").json))

print("Retirar")
comprobar("retirar con token falso -> 403", c.delete(f"/api/memorias/{idv}", headers={"X-Token": "falso"}).status_code == 403)
comprobar("retirar sin token -> 403", c.delete(f"/api/memorias/{idv}").status_code == 403)
comprobar("retirar con su token -> 200", c.delete(f"/api/memorias/{idv}", headers={"X-Token": tok}).status_code == 200)
comprobar("ya no está en la lista pública", c.get("/api/memorias").json == [])
comprobar("retirar de nuevo -> 404", c.delete(f"/api/memorias/{idv}", headers={"X-Token": tok}).status_code == 404)

print()
print("RESULTADO:", "todo bien" if not fallos else f"{fallos} fallos")
sys.exit(1 if fallos else 0)
