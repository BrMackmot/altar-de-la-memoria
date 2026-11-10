/* Service worker: guarda el altar en el teléfono la primera vez que se abre,
   para que funcione después sin internet (útil donde la conexión es débil).
   Si cambia algún archivo del sitio, suba VERSION (v1 -> v2) para que se actualice. */
const VERSION = 'altar-v5';
const ARCHIVOS = [
  './',
  'index.html',
  'contenido.json',
  'manifest.webmanifest',
  'icono-192.png',
  'icono-512.png',
  'libs/model-viewer.min.js',
  'modelo/altar.glb',
  'video/rio.mp4',
  'video/rio-portada.jpg',
  'fotos/rio-1.jpg',
  'video/canto.mp4',
  'video/canto-portada.jpg',
  'fotos/canto-1.jpg',
  'fotos/canto-2.jpg',
  'fotos/canto-3.jpg',
  'fotos/canto-4.jpg',
  'fotos/canto-5.jpg',
  'fotos/canto-6.jpg',
  'fotos/persona-1.jpg',
  'fotos/persona-2.jpg',
  'fotos/persona-3.jpg',
  'fotos/persona-4.jpg',
  'fotos/persona-5.jpg',
  'fotos/persona-6.jpg',
  'fotos/persona-7.jpg',
  'musica/fondo.mp3'
];

// cache.add() rechaza respuestas parciales (206), que el navegador puede devolver si ya
// pidió el video por partes. Se pide con cache:'reload' para obtener el archivo completo.
async function guardar(cache, url) {
  try {
    const r = await fetch(new Request(url, { cache: 'reload' }));
    if (r.status === 200) await cache.put(url, r);
    else console.log('No se guardó', url, 'estado', r.status);
  } catch (err) {
    console.log('No se guardó', url, String(err));
  }
}

self.addEventListener('install', (e) => {
  // Los archivos opcionales que falten (por ejemplo un video aún no subido) no deben romper la instalación
  e.waitUntil(caches.open(VERSION).then((c) =>
    Promise.all(ARCHIVOS.map((a) => guardar(c, a)))
  ).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    // No se usa clients.claim(): tomar el control a mitad de una reproducción corta la descarga
    // del video. El service worker empieza a servir desde la siguiente visita.
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
  );
});

// Los navegadores piden los videos por rangos de bytes; hay que contestar igual desde la caché.
async function rango(req, resp) {
  const buf = await resp.arrayBuffer();
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.get('range'));
  const ini = m[1] ? parseInt(m[1], 10) : 0;
  const fin = m[2] ? Math.min(parseInt(m[2], 10), buf.byteLength - 1) : buf.byteLength - 1;
  return new Response(buf.slice(ini, fin + 1), {
    status: 206,
    headers: {
      'Content-Type': resp.headers.get('Content-Type') || 'video/mp4',
      'Content-Range': `bytes ${ini}-${fin}/${buf.byteLength}`,
      'Content-Length': String(fin - ini + 1)
    }
  });
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (new URL(req.url).pathname.includes('/api/')) return; // la API siempre va a la red
  e.respondWith((async () => {
    const guardado = await caches.match(req.url, { ignoreSearch: true });
    if (guardado) return req.headers.get('range') ? rango(req, guardado) : guardado;
    try {
      const r = await fetch(req);
      if (r.ok && r.status === 200) (await caches.open(VERSION)).put(req, r.clone());
      return r;
    } catch (err) {
      return new Response('Sin conexión y este archivo no se guardó todavía.', { status: 503 });
    }
  })());
});
