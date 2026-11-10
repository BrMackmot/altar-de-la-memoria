# Altar de la Memoria 3D · prototipo de realidad aumentada (CAEDI, Bogotá)

Un altar en 3D que se mira en pantalla o se pone sobre una mesa con realidad aumentada, sin imprimir nada. Recorrido guiado de unos 3 minutos: bienvenida, tres memorias (el río, el canto, una persona) con video, fotos y música, un espacio para dejar la propia memoria con permisos, y cierre.

Actividad 2.1 · Electiva II · Mundos Inmersivos, Voces Visibles (USTA).

## Estructura

| Carpeta o archivo | Qué es |
|---|---|
| `index.html` | La experiencia completa |
| `contenido.json` | **Los textos y medios de cada memoria.** Aquí se edita lugar, nombre, transcripción, descripción de fotos y crédito de la música, sin tocar el código |
| `video/`, `fotos/`, `audio/`, `musica/` | Medios ya preparados para la web (los genera `preparar_medios.py`) |
| `modelo/altar.glb` | El altar 3D (lo genera `crear_altar.py`) |
| `libs/` | El visor 3D `<model-viewer>` |
| `sw.js`, `manifest.webmanifest`, iconos | Modo sin internet e instalación en el teléfono |
| `app.py` | Servidor Flask opcional para recibir aportes |
| `herramientas/` | Scripts en Python |
| `entrada/` | Sus archivos originales. **No se sube a GitHub** |

## 1. Agregar o cambiar videos, fotos, audio y música

1. Ponga los originales en `entrada/rio/`, `entrada/canto/`, `entrada/persona/` y `entrada/musica/`. En cada memoria puede haber:
   - **un video**, o
   - **un audio** (por ejemplo una nota de voz del teléfono o un canto grabado) **y fotos**: las fotos pasan como diapositivas mientras suena el audio, o
   - **solo fotos**: pasan como diapositivas con la música de fondo.
2. Ejecute `python herramientas/preparar_medios.py`. Comprime, recorta a 45 s, quita la ubicación GPS de las fotos, actualiza `contenido.json` y `sw.js`, y dice cuánto dura el recorrido.
3. Para elegir otra parte de un video, cambie `"recorte": {"inicio": 20, "duracion": 45}` en `contenido.json` y vuelva a ejecutar.
4. Edite en `contenido.json` el `lugar`, `quien` y `texto` de cada memoria, y la descripción (`alt`) de cada foto.
5. Ejecute `python herramientas/verificar_paquete.py` antes de subir.

Requisitos: Python 3, `pip install pillow trimesh numpy flask`, y ffmpeg (https://ffmpeg.org). Fotos HEIC de iPhone: `pip install pillow-heif` o expórtelas como JPG.

## 2. Publicar en GitHub Pages

1. En github.com, **New repository**. Nombre, por ejemplo, `altar-de-la-memoria`. Márquelo **Public**. No agregue README.
2. En el repositorio vacío: **uploading an existing file**. Arrastre **el contenido** de esta carpeta (no la carpeta misma), con todas las subcarpetas. **No arrastre `entrada/`.** Commit changes.
3. **Settings → Pages → Build and deployment → Deploy from a branch → main / (root) → Save.**
4. Espere 1 o 2 minutos. El enlace será `https://SU-USUARIO.github.io/altar-de-la-memoria/`. Ábralo en el teléfono.
5. Cada vez que cambie medios: ejecute `preparar_medios.py` (sube la versión en `sw.js` sola) y vuelva a subir los archivos cambiados, incluido `sw.js`.

GitHub Pages no ejecuta Python: allí el formulario guarda el aporte solo en el teléfono y lo dice. Para recibir aportes de verdad use `app.py` en un servidor con Python (por ejemplo PythonAnywhere), con la variable `ADMIN_KEY`.

## Herramientas en Python (`herramientas/`)

| Script | Para qué |
|---|---|
| `preparar_medios.py` | Prepara videos, fotos, audio y música para la web |
| `verificar_paquete.py` | Comprueba que no falte nada antes de subir |
| `crear_altar.py` | Construye el altar 3D (colores, medidas, piezas) |
| `crear_iconos.py` | Crea los íconos de la aplicación |
| `generar_videos_demo.py` | Videos de ejemplo, solo para pruebas |
| `probar_servidor.py` | Prueba automática del servidor (27 comprobaciones) |

## Antes de mostrarlo

- Cada persona que aparece en un video o foto debe haber autorizado su uso (kit de validación, página 2).
- Lo litúrgico o sagrado solo con aval del mayor responsable.
- Música: use música propia o con licencia libre y escriba el crédito exacto en `contenido.json`.

## Qué se probó y qué no

Probado automáticamente: recorrido completo, video, diapositivas de fotos, visor de fotos ampliadas, música de fondo, formulario con envío y retiro, modo sin internet y seguridad del servidor. **No probado:** la realidad aumentada en un teléfono real, iPhone/Safari, poca luz y datos móviles.

## Declaración de uso de IA

El código, las herramientas y el modelo 3D se desarrollaron con ayuda de Claude (Anthropic), con revisión y decisiones del autor. Declárelo en el informe.
