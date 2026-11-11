// App do Repertório CCT: sempre busca a versão mais nova na internet; sem internet, mostra a última que foi aberta.
const CACHE = 'louvor-cct-v1';
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']).catch(() => {}))); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== self.location.origin) return;
  e.respondWith(fetch(r).then((resp) => { const cp = resp.clone(); caches.open(CACHE).then((c) => c.put(r, cp)); return resp; }).catch(() => caches.match(r).then((m) => m || caches.match('./'))));
});
