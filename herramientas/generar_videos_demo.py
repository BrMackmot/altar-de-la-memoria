"""
Crea tres videos de DEMOSTRACIÓN (video/rio.mp4, canto.mp4, persona.mp4) de 45 segundos cada uno.

Sirven para probar el recorrido completo de 3 minutos antes de tener las grabaciones reales.
Cada video lleva escrito en pantalla "VIDEO DE EJEMPLO", así no puede confundirse con un
testimonio. Reemplácelos por los videos autorizados de las personas con el mismo nombre de archivo.

Uso, desde la carpeta raíz del repositorio:
    python herramientas/generar_videos_demo.py

Requisito: tener ffmpeg instalado (https://ffmpeg.org).
"""
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AFICHE = RAIZ / "fuentes" / "referencia-afiche.png"
CARPETA = RAIZ / "video"
DURACION = 45  # segundos
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # cámbiela si usa Windows o Mac

# Recorte del afiche (x, y, ancho, alto) y sonido sintético de cada memoria.
MEMORIAS = {
    "rio": {
        "titulo": "EL RÍO",
        "recorte": (0, 1230, 560, 315),
        "audio": f"anoisesrc=d={DURACION}:color=pink:amplitude=0.25",
        "filtro_audio": "lowpass=f=900,afade=t=in:d=3,afade=t=out:st=42:d=3",
    },
    "canto": {
        "titulo": "EL CANTO",
        "recorte": (340, 1230, 560, 315),
        "audio": f"aevalsrc='0.55*sin(2*PI*90*t)*exp(-7*mod(t,0.75))':s=44100:d={DURACION}",
        "filtro_audio": "afade=t=in:d=2,afade=t=out:st=43:d=2",
    },
    "persona": {
        "titulo": "UNA PERSONA",
        "recorte": (680, 1230, 560, 315),
        "audio": f"aevalsrc='0.13*sin(2*PI*220*t)+0.09*sin(2*PI*277*t)':s=44100:d={DURACION}",
        "filtro_audio": "afade=t=in:d=3,afade=t=out:st=42:d=3",
    },
}


def generar(clave, datos):
    x, y, w, h = datos["recorte"]
    video = (
        f"crop={w}:{h}:{x}:{y},scale=1280:720,"
        "zoompan=z='min(1+0.0004*on,1.4)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720:fps=25,"
        f"drawtext=fontfile={FUENTE}:text='VIDEO DE EJEMPLO · {datos['titulo']}':fontcolor=white:fontsize=42:"
        "box=1:boxcolor=0x1b2523@0.8:boxborderw=14:x=(w-text_w)/2:y=h-170,"
        f"drawtext=fontfile={FUENTE}:text='Aquí irá la grabación autorizada':fontcolor=0xffd978:fontsize=30:"
        "box=1:boxcolor=0x1b2523@0.8:boxborderw=10:x=(w-text_w)/2:y=h-90,format=yuv420p"
    )
    salida = CARPETA / f"{clave}.mp4"
    orden = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "25", "-t", str(DURACION), "-i", str(AFICHE),
        "-f", "lavfi", "-i", datos["audio"],
        "-vf", video, "-af", datos["filtro_audio"],
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "32", "-c:a", "aac", "-b:a", "64k",
        "-shortest", "-movflags", "+faststart", str(salida),
    ]
    subprocess.run(orden, check=True)
    print(f"{salida.name}: {salida.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    CARPETA.mkdir(exist_ok=True)
    for clave, datos in MEMORIAS.items():
        generar(clave, datos)
    print("Listo. Recuerde reemplazarlos por los videos reales y autorizados.")
